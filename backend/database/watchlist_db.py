import sqlite3
import json
import time
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "friday_trading_db.sqlite"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def init_watchlist_table():
    """Create watchlist table in SQLite if it doesn't exist."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watchlist (
                symbol      TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                full_name   TEXT,
                logo_img    TEXT,
                logo_img2   TEXT,
                logo_bg     TEXT,
                logo_text   TEXT,
                type        TEXT,
                exchange    TEXT,
                is_positive INTEGER DEFAULT 1,
                flagged     INTEGER DEFAULT 0,
                price       TEXT DEFAULT '—',
                change      TEXT DEFAULT '—',
                change_pct  TEXT DEFAULT '—',
                sort_order  INTEGER DEFAULT 0,
                added_at    REAL NOT NULL
            )
        ''')
        conn.commit()
    print("[Watchlist DB] ✅ Watchlist table ready.")


init_watchlist_table()


def get_watchlist() -> list:
    """Fetch all watchlist items sorted by sort_order."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM watchlist ORDER BY sort_order ASC, added_at ASC")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"[Watchlist DB] Error fetching watchlist: {e}")
        return []


def add_watchlist_item(item: dict) -> bool:
    """Add or update a watchlist item. Returns True on success."""
    try:
        symbol = item.get("symbol", "").strip().upper()
        if not symbol:
            return False

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Count existing rows to set sort_order
            cursor.execute("SELECT COUNT(*) FROM watchlist")
            count = cursor.fetchone()[0]

            cursor.execute('''
                INSERT INTO watchlist
                    (symbol, name, full_name, logo_img, logo_img2, logo_bg, logo_text,
                     type, exchange, is_positive, flagged, price, change, change_pct,
                     sort_order, added_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    name        = excluded.name,
                    full_name   = excluded.full_name,
                    logo_img    = excluded.logo_img,
                    logo_img2   = excluded.logo_img2,
                    logo_bg     = excluded.logo_bg,
                    logo_text   = excluded.logo_text,
                    type        = excluded.type,
                    exchange    = excluded.exchange,
                    is_positive = excluded.is_positive,
                    flagged     = excluded.flagged
            ''', (
                symbol,
                item.get("name", symbol),
                item.get("full", item.get("full_name", "")),
                item.get("logoImg", item.get("logo_img", "")),
                item.get("logoImg2", item.get("logo_img2", "")),
                item.get("logoBg", item.get("logo_bg", "#2962ff")),
                item.get("logoText", item.get("logo_text", "")),
                item.get("type", ""),
                item.get("exchange", ""),
                1 if item.get("isPositive", item.get("is_positive", True)) else 0,
                1 if item.get("flagged", False) else 0,
                item.get("price", "—"),
                item.get("change", "—"),
                item.get("changePct", item.get("change_pct", "—")),
                count,
                time.time()
            ))
            conn.commit()
        print(f"[Watchlist DB] ✅ Saved {symbol} to watchlist.")
        return True
    except Exception as e:
        print(f"[Watchlist DB] Error adding item: {e}")
        return False


def remove_watchlist_item(symbol: str) -> bool:
    """Remove a symbol from the watchlist. Returns True if a row was deleted."""
    try:
        symbol = symbol.strip().upper()
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))
            deleted = cursor.rowcount
            conn.commit()
        print(f"[Watchlist DB] {'✅ Removed' if deleted else '⚠️ Not found'}: {symbol}")
        return deleted > 0
    except Exception as e:
        print(f"[Watchlist DB] Error removing item: {e}")
        return False


def seed_default_watchlist(default_items: list) -> None:
    """Seed the watchlist with default items only if the table is empty."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM watchlist")
            if cursor.fetchone()[0] == 0:
                for item in default_items:
                    add_watchlist_item(item)
                print(f"[Watchlist DB] ✅ Seeded {len(default_items)} default items.")
    except Exception as e:
        print(f"[Watchlist DB] Error seeding defaults: {e}")
