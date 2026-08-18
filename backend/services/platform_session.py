import os
import sys
import json
import sqlite3
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

# Sessions live in the unified friday_brain.db like the rest of Career OS
# (previously a separate career.db — migrated once below).
DB_FILE = Path(__file__).parent.parent / "data" / "friday_brain.db"


def _connect():
    """Thread-safe SQLite connection (WAL) for the unified brain DB."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_session_db():
    conn = _connect()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS platform_sessions (
            platform_key TEXT PRIMARY KEY,
            account_name TEXT,
            headline TEXT,
            connections_count INTEGER DEFAULT 0,
            open_to_work INTEGER DEFAULT 0,
            cookies_json TEXT,
            verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def _migrate_legacy_career_db():
    """One-time copy of platform_sessions from the old data/career.db (if any)."""
    legacy = Path(__file__).parent.parent / "data" / "career.db"
    if not legacy.exists():
        return
    try:
        import sqlite3 as _sq
        src = _sq.connect(legacy)
        src.row_factory = _sq.Row
        rows = src.execute(
            "SELECT platform_key, account_name, headline, connections_count, "
            "open_to_work, cookies_json, verified_at FROM platform_sessions"
        ).fetchall()
        src.close()
        if not rows:
            return
        with _connect() as conn:
            for r in rows:
                conn.execute(
                    "INSERT OR IGNORE INTO platform_sessions "
                    "(platform_key, account_name, headline, connections_count, "
                    "open_to_work, cookies_json, verified_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (r["platform_key"], r["account_name"], r["headline"],
                     r["connections_count"], r["open_to_work"],
                     r["cookies_json"], r["verified_at"]))
            conn.commit()
        print(f"[Platform Session] Migrated {len(rows)} session(s) from legacy career.db")
    except Exception as err:
        print(f"[Platform Session] Legacy migration skipped: {err}")


init_session_db()
_migrate_legacy_career_db()

async def launch_real_browser_login(platform_key: str):
    """
    Launches a real Chromium browser window (headless=False) for the user to log in ONCE.
    Captures authenticated session cookies (li_at, etc.) and saves them to DB.

    Returns an honest error dict (never raises / never 500s) when the browser
    cannot be launched — e.g. Playwright Chromium not installed (Docker default
    INSTALL_BROWSERS=0) or no display available on a headless server.
    """
    urls = {
        "linkedin": "https://www.linkedin.com/login",
        "naukri": "https://www.naukri.com/nlogin/login",
        "internshala": "https://internshala.com/login/user",
        "wellfound": "https://wellfound.com/login",
        "foundit": "https://www.foundit.in/login"
    }

    target_url = urls.get(platform_key, "https://www.linkedin.com/login")
    browser = None
    try:
        from playwright.async_api import async_playwright

        # headless=False needs a desktop session. On a headless Linux server
        # (Render, most Docker hosts) there is no display — tell the user this
        # feature must run on their own desktop machine instead of crashing.
        if os.name == "posix" and not sys.platform.startswith("darwin") and not os.environ.get("DISPLAY"):
            return {
                "status": "error",
                "verified": False,
                "message": (
                    "Account connect launches a visible browser window, which "
                    "needs a desktop display. Run FRIDAY on your own machine "
                    "(or via start.sh) to connect career accounts."
                ),
            }

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(target_url, timeout=30000)

                # Wait up to 120s for user to complete login
                for _ in range(120):
                    await asyncio.sleep(1)
                    curr_url = page.url.lower()
                    cookies = await context.cookies()

                    has_li_cookie = any(c['name'] == 'li_at' for c in cookies)
                    if 'feed' in curr_url or 'in/' in curr_url or 'mynetwork' in curr_url or has_li_cookie or ('naukri.com' in curr_url and 'mnjuser' in curr_url):
                        cookies_json = json.dumps(cookies)

                        account_name = ""
                        headline = ""
                        connections = 0
                        open_to_work = 0

                        try:
                            if 'linkedin.com' in curr_url:
                                name_el = await page.query_selector(".profile-rail-card__actor-link, .identity-headline")
                                if name_el:
                                    account_name = (await name_el.inner_text()).strip()
                        except Exception:
                            pass

                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute('''
                            INSERT OR REPLACE INTO platform_sessions 
                            (platform_key, account_name, headline, connections_count, open_to_work, cookies_json, verified_at)
                            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        ''', (platform_key, account_name, headline, connections, open_to_work, cookies_json))
                        conn.commit()
                        conn.close()

                        if browser:
                            await browser.close()
                        return {
                            "status": "connected",
                            "verified": True,
                            "platform": platform_key.capitalize(),
                            "account_user": account_name,
                            "headline": headline,
                            "connections": connections,
                            "open_to_work": bool(open_to_work),
                            "cookie_expires_days": 14,
                            "last_verified": "Just now",
                            "permissions": ["Read profile", "Search jobs", "Fill applications safely"]
                        }

                if browser:
                    await browser.close()
                return {"status": "timeout", "verified": False, "message": "Login window timed out."}
            except Exception as e:
                if browser:
                    await browser.close()
                return {"status": "error", "verified": False, "message": str(e)}
    except Exception as e:
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
        return {
            "status": "error",
            "verified": False,
            "message": (
                f"Could not launch browser for {platform_key}: {e}. "
                "Install Playwright Chromium (INSTALL_BROWSERS=1 in Docker) or "
                "run FRIDAY on a desktop machine to connect accounts."
            ),
        }

def get_platform_session_status(platform_key: str):
    """Retrieves verified session metadata for platform.

    Returns an honest `needs_login` status when no session has been captured
    yet — never a fabricated "connected" response.
    """
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT account_name, headline, connections_count, open_to_work, cookies_json, verified_at FROM platform_sessions WHERE platform_key = ?", (platform_key,))
    row = c.fetchone()
    conn.close()

    if row:
        account_name, headline, connections, open_to_work, cookies_json, verified_at = row
        return {
            "status": "connected",
            "healthy": True,
            "verified": True,
            "platform": platform_key.capitalize(),
            "account_user": account_name or "Unknown account",
            "headline": headline or "",
            "connections": int(connections or 0),
            "open_to_work": bool(open_to_work),
            "last_verified": verified_at or "Recently",
            "cookie_expires_days": 14,
            "permissions": ["Read profile", "Search jobs", "Fill applications safely"]
        }

    return {
        "status": "needs_login",
        "healthy": False,
        "verified": False,
        "platform": platform_key.capitalize(),
        "account_user": None,
        "headline": None,
        "connections": 0,
        "open_to_work": False,
        "last_verified": None,
        "cookie_expires_days": 0,
        "permissions": [],
        "message": (
            f"No stored session for {platform_key}. "
            "Use 'Connect' to log in once in a real browser and capture a session."
        )
    }
