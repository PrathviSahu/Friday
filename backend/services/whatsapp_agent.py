"""services/whatsapp_agent.py — WhatsApp Agent (experimental).

IMPORTANT — honest engineering notes:
  * There is NO official free WhatsApp API. The well-known Python library
    (moyiz/whatsapp-web.py) is gone from GitHub, and the PyPI package that
    squats its name is a typosquat — we will NOT use it.
  * FRIDAY therefore ships its own thin Playwright driver for WhatsApp Web
    (the same technique whatsapp-web.js uses, but with Playwright which we
    already depend on and trust). It is EXPERIMENTAL: WhatsApp can change
    its DOM selectors at any time, so all scraping is defensive and
    best-effort.
  * The driver is OFF by default. Set FRIDAY_WHATSAPP_ENABLED=1 to opt in.
    Everything around it (permissions, drafts, approval-first send, voice)
    is fully tested with a fake driver.

Send flow (approval-first, identical to email):
  1. POST /api/whatsapp/draft   → message stored server-side (TTL) + preview
  2. POST /api/whatsapp/send    → requires a fresh draft + one-time
     `whatsapp.send` approval (permission mode 'ask' by default).
"""

import asyncio
import json
import os
import re
import threading
import time
import uuid
from pathlib import Path

DRAFTS_FILE = Path(__file__).resolve().parent.parent / "data" / "whatsapp_drafts.json"
DRAFT_TTL_SECONDS = int(os.getenv("FRIDAY_WHATSAPP_DRAFT_TTL", "900"))
SESSION_DIR = Path(__file__).resolve().parent.parent / "data" / "whatsapp_session"

ENABLED = os.getenv("FRIDAY_WHATSAPP_ENABLED", "0") == "1"

# Driver state machine (module-level, thread-safe)
_state = {
    "enabled": ENABLED,
    "connected": False,
    "pairing": False,
    "starting": False,
    "qr_data_url": "",      # base64 PNG of the pairing QR (canvas capture)
    "qr_ts": 0.0,
    "error": "",
    "last_check": 0.0,
}
_state_lock = threading.Lock()

_driver = None        # PlaywrightWhatsAppDriver singleton
_loop = None          # asyncio loop owned by the driver thread
_loop_lock = threading.Lock()


class WhatsAppUnavailableError(RuntimeError):
    """Raised when the driver is disabled or the connection is missing."""


# ── Draft store (approval-first) ─────────────────────────────────────────

def _load_drafts() -> dict:
    if not DRAFTS_FILE.exists():
        return {}
    try:
        return json.loads(DRAFTS_FILE.read_text())
    except Exception:
        return {}


def _save_drafts(drafts: dict) -> None:
    DRAFTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    DRAFTS_FILE.write_text(json.dumps(drafts, indent=2))


def _normalize_phone(phone: str) -> str:
    """'whatsapp' phone → digits with country code (best effort)."""
    digits = re.sub(r"\D", "", phone or "")
    if not digits:
        raise ValueError("A phone number is required (with country code, e.g. +91...).")
    if len(digits) < 10 or len(digits) > 15:
        raise ValueError("Phone number looks invalid — use country code + number, e.g. 919876543210.")
    return digits


def create_draft(phone: str, message: str) -> dict:
    phone = _normalize_phone(phone)
    message = (message or "").strip()
    if not message:
        raise ValueError("A message is required.")

    drafts = _load_drafts()
    now = time.time()
    drafts = {k: v for k, v in drafts.items() if v.get("expires_at", 0) > now}

    draft = {
        "id": uuid.uuid4().hex,
        "phone": phone,
        "message": message[:1000],
        "created_at": now,
        "expires_at": now + DRAFT_TTL_SECONDS,
        "status": "pending",
    }
    drafts[draft["id"]] = draft
    _save_drafts(drafts)
    return draft


def get_draft(draft_id: str) -> dict | None:
    draft = _load_drafts().get(draft_id)
    if not draft:
        return None
    if draft.get("expires_at", 0) < time.time() or draft.get("status") != "pending":
        return None
    return draft


def cancel_draft(draft_id: str) -> bool:
    drafts = _load_drafts()
    if draft_id in drafts:
        drafts.pop(draft_id, None)
        _save_drafts(drafts)
        return True
    return False


# ── Status / driver lifecycle ────────────────────────────────────────────

def get_status() -> dict:
    with _state_lock:
        return dict(_state)


def _update(**kw) -> None:
    with _state_lock:
        _state.update(kw)


def _require_enabled() -> None:
    if not ENABLED:
        raise WhatsAppUnavailableError(
            "WhatsApp is disabled. Set FRIDAY_WHATSAPP_ENABLED=1 in backend/.env "
            "(experimental — requires Playwright Chromium) to enable it."
        )


def _ensure_driver_started() -> None:
    """Lazily start the Playwright driver thread (once)."""
    global _driver, _loop
    _require_enabled()
    with _loop_lock:
        if _driver is not None:
            return
        if _state.get("starting"):
            return
        _update(starting=True, error="")
        try:
            _driver = PlaywrightWhatsAppDriver()
            t = threading.Thread(target=_driver.run, name="whatsapp-driver", daemon=True)
            t.start()
            # Wait until the thread publishes its loop (or 10s)
            deadline = time.time() + 10
            while _loop is None and time.time() < deadline:
                time.sleep(0.1)
        except Exception as exc:
            _update(starting=False, error=str(exc))
            _driver = None
            raise WhatsAppUnavailableError(f"Could not start WhatsApp driver: {exc}") from exc


def _run_on_loop(coro, timeout: float = 20.0):
    """Schedule an async coroutine on the driver's event loop."""
    global _loop
    with _loop_lock:
        if _loop is None or _loop.is_closed():
            raise WhatsAppUnavailableError("WhatsApp driver is not running.")
        fut = asyncio.run_coroutine_threadsafe(coro, _loop)
    return fut.result(timeout=timeout)


# ── Read / send API ──────────────────────────────────────────────────────

def get_qr() -> dict:
    """Current pairing QR (data URL) or a state description."""
    _ensure_driver_started()
    with _state_lock:
        st = dict(_state)
    if st.get("connected"):
        return {"status": "connected"}
    if st.get("qr_data_url") and time.time() - st.get("qr_ts", 0) < 60:
        return {"status": "pairing", "qr_data_url": st["qr_data_url"]}
    return {"status": "starting", "message": "Waiting for the pairing QR code…"}


def get_chats(limit: int = 20) -> list:
    """Recent chats with unread counts (best-effort; empty when driver can't)."""
    _require_enabled()
    _ensure_driver_started()
    if not _state.get("connected"):
        raise WhatsAppUnavailableError("WhatsApp is not connected yet — scan the QR code.")
    try:
        return _run_on_loop(_driver.read_chats(limit))
    except WhatsAppUnavailableError:
        raise
    except Exception as exc:
        raise WhatsAppUnavailableError(f"Could not read chats: {exc}") from exc


def search_messages(query: str, limit: int = 10) -> list:
    """Search recent chat messages for `query` (best-effort)."""
    _require_enabled()
    _ensure_driver_started()
    if not _state.get("connected"):
        raise WhatsAppUnavailableError("WhatsApp is not connected yet — scan the QR code.")
    try:
        return _run_on_loop(_driver.search_messages(query, limit))
    except Exception as exc:
        raise WhatsAppUnavailableError(f"Could not search WhatsApp: {exc}") from exc


def summarize() -> dict:
    """Unread summary for the brain (counts + top chats)."""
    chats = get_chats(limit=20)
    unread = [c for c in chats if (c.get("unread") or 0) > 0]
    return {
        "connected": True,
        "unread_count": sum(c.get("unread", 0) for c in unread),
        "chats": unread[:8],
    }


def send_draft(draft_id: str) -> dict:
    """Send a previously previewed draft (approval-first)."""
    draft = get_draft(draft_id)
    if not draft:
        raise WhatsAppUnavailableError("Draft not found or expired — please preview the message again.")
    _require_enabled()
    _ensure_driver_started()
    if not _state.get("connected"):
        raise WhatsAppUnavailableError("WhatsApp is not connected yet — scan the QR code.")
    try:
        chat_id = f"{draft['phone']}@c.us"
        _run_on_loop(_driver.send_message(chat_id, draft["message"]))
    except Exception as exc:
        raise WhatsAppUnavailableError(f"Could not send message: {exc}") from exc

    drafts = _load_drafts()
    if draft_id in drafts:
        drafts[draft_id]["status"] = "sent"
        drafts[draft_id]["sent_at"] = time.time()
        _save_drafts(drafts)
    return {"draft_id": draft_id, "phone": draft["phone"], "sent_at": int(time.time())}


# ── Playwright driver (EXPERIMENTAL — WhatsApp DOM may change) ───────────

class PlaywrightWhatsAppDriver:
    """Drives WhatsApp Web with Playwright.

    Runs in its own thread + event loop. Selectors are best-effort and
    wrapped in try/except — a DOM change degrades to empty results, never
    a crash. Session persists in backend/data/whatsapp_session.
    """

    SELECTORS = {
        "chat_list": '#pane-side div[role="row"]',
        "chat_name": 'span[dir="auto"]',
        "chat_unread": 'span[aria-label*="unread" i]',
        "message_box": 'div[contenteditable="true"][data-tab="10"], div[contenteditable="true"][spellcheck="true"]',
        "login_indicator": 'div[data-testid="chat-list"], #pane-side',
        "qr_canvas": "canvas",
    }

    def __init__(self):
        self._loop = None
        self._ctx = None

    def run(self):
        """Entry point for the driver thread."""
        global _loop
        try:
            asyncio.run(self._main())
        except Exception as exc:
            _update(error=str(exc), starting=False, connected=False)
            with _loop_lock:
                _loop = None

    async def _main(self):
        from playwright.async_api import async_playwright

        self._loop = asyncio.get_running_loop()
        global _loop
        with _loop_lock:
            _loop = self._loop

        async with async_playwright() as p:
            SESSION_DIR.mkdir(parents=True, exist_ok=True)
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(SESSION_DIR),
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            self._ctx = context
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")
            _update(starting=False)

            # Poll: connected? else capture QR.
            while True:
                try:
                    if await page.query_selector(self.SELECTORS["login_indicator"]):
                        _update(connected=True, pairing=False, qr_data_url="", qr_ts=0.0)
                    else:
                        _update(connected=False, pairing=True)
                        data_url = await self._capture_qr(page)
                        if data_url:
                            _update(qr_data_url=data_url, qr_ts=time.time())
                except Exception:
                    pass
                await asyncio.sleep(3)

    async def _capture_qr(self, page) -> str:
        """Capture the pairing QR as a PNG data URL (canvas → fallback screenshot)."""
        try:
            data_url = await page.evaluate(
                """() => {
                    const cv = document.querySelector('canvas');
                    if (!cv) return '';
                    try { return cv.toDataURL('image/png'); } catch (e) { return ''; }
                }"""
            )
            if data_url:
                return data_url
        except Exception:
            pass
        try:
            shot = await page.screenshot(type="png")
            import base64
            return "data:image/png;base64," + base64.b64encode(shot).decode()
        except Exception:
            return ""

    async def read_chats(self, limit: int = 20) -> list:
        page = await self._page()
        items = await page.query_selector_all(self.SELECTORS["chat_list"])
        out = []
        for item in items[:limit]:
            try:
                name_el = await item.query_selector(self.SELECTORS["chat_name"])
                name = (await name_el.inner_text()).strip() if name_el else ""
                if not name:
                    continue
                unread_el = await item.query_selector(self.SELECTORS["chat_unread"])
                unread_text = (await unread_el.inner_text()).strip() if unread_el else ""
                unread = int(re.sub(r"\D", "", unread_text)) if unread_text else 0
                out.append({"name": name[:60], "unread": unread})
            except Exception:
                continue
        return out

    async def search_messages(self, query: str, limit: int = 10) -> list:
        chats = await self.read_chats(limit=10)
        # Best-effort: match chat names; message-body search requires opening
        # each chat, which is slow and fragile — name match is the stable part.
        q = query.lower()
        return [c for c in chats if q in c["name"].lower()][:limit]

    async def send_message(self, chat_id: str, text: str) -> None:
        page = await self._page()
        # Open the chat by URL first (robust), then type + Enter.
        await page.goto(f"https://web.whatsapp.com/send?phone={chat_id.replace('@c.us', '')}")
        await page.wait_for_timeout(2500)
        box = await page.wait_for_selector(
            self.SELECTORS["message_box"], timeout=15000
        )
        await box.click()
        await box.fill(text)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(800)

    async def _page(self):
        if self._ctx is None:
            raise WhatsAppUnavailableError("Driver context not ready.")
        return self._ctx.pages[0] if self._ctx.pages else await self._ctx.new_page()
