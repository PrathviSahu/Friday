"""services/calendar_agent.py — Calendar Agent (Google Calendar).

Reads today/upcoming events and creates events with an approval-first flow:

  1. POST /api/calendar/draft   → a pending event is stored server-side
     (with TTL) and a preview is returned.
  2. POST /api/calendar/create  → only accepts a fresh draft AND a valid
     `calendar.write` approval; the event is inserted via the Google
     Calendar API.

Auth mirrors GDrive: OAuth2 user token in `calendar_token.json` (own file,
own scopes — the GDrive token is scope-bound and can't be reused), created
from `credentials.json` via the installed-app flow, or a service account.
"""

import json
import os
import re
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Read + write scopes. `calendar.events` allows creating events without
# sharing the whole calendar (safer than full `calendar` scope).
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
SERVICE_ACCOUNT_FILE = BASE_DIR / "service_account.json"
TOKEN_FILE = BASE_DIR / "calendar_token.json"

DRAFTS_FILE = BASE_DIR / "data" / "calendar_drafts.json"
DRAFT_TTL_SECONDS = int(os.getenv("FRIDAY_CALENDAR_DRAFT_TTL", "900"))

_calendar_status = {
    "connected": False,
    "method": "none",
    "account": "",
    "status": "unauthenticated",
}


class CalendarUnavailableError(RuntimeError):
    """Raised when Google Calendar is not configured or unreachable."""


# ── Config / auth ─────────────────────────────────────────────────────────

def has_token_file() -> bool:
    """True when user OAuth token file exists."""
    return TOKEN_FILE.exists()


def has_credentials_file() -> bool:
    """True when client secrets file exists."""
    return CREDENTIALS_FILE.exists()


def has_service_account_file() -> bool:
    """True when service account file exists."""
    return SERVICE_ACCOUNT_FILE.exists()


def is_configured() -> bool:
    """True when a token, service account or client secrets file exists."""
    return has_token_file() or has_service_account_file() or has_credentials_file()



def _build_service():
    """Authenticate and return a Google Calendar API service (or raise)."""
    from google.oauth2.credentials import Credentials
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    global _calendar_status

    # Option 1: service account (needs domain-wide delegation for real calendars)
    if SERVICE_ACCOUNT_FILE.exists():
        try:
            creds = service_account.Credentials.from_service_account_file(
                str(SERVICE_ACCOUNT_FILE), scopes=SCOPES
            )
            service = build("calendar", "v3", credentials=creds)
            _calendar_status.update({"connected": True, "method": "ServiceAccount", "status": "authenticated"})
            return service
        except Exception as exc:
            print(f"[Calendar] Service account auth error: {exc}")

    # Option 2: OAuth2 user token (calendar_token.json)
    creds = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception as exc:
            print(f"[Calendar] Token load error: {exc}")

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json())
        except Exception as exc:
            print(f"[Calendar] Token refresh error: {exc}")

    if not creds or not creds.valid:
        if not CREDENTIALS_FILE.exists():
            raise CalendarUnavailableError(
                "Google Calendar is not connected. Create a Google Cloud OAuth "
                "client (enable the Calendar API), save it as backend/credentials.json, "
                "then call /api/calendar/status once to authenticate."
            )
        try:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
            TOKEN_FILE.write_text(creds.to_json())
            print("[Calendar] ✅ OAuth completed — token saved to calendar_token.json")
        except Exception as exc:
            raise CalendarUnavailableError(f"Google Calendar OAuth flow failed: {exc}") from exc

    # Guard: a token that was granted only Drive scopes can't read calendars
    granted = set(creds.scopes or [])
    if not granted.intersection(SCOPES):
        raise CalendarUnavailableError(
            "calendar_token.json was granted without Calendar scopes — delete it and "
            "re-authenticate via /api/calendar/status."
        )

    service = build("calendar", "v3", credentials=creds)
    _calendar_status.update({"connected": True, "method": "OAuth", "status": "authenticated"})
    return service


def get_status() -> dict:
    return dict(_calendar_status)


# ── Time helpers (local-tz aware, works in Docker with TZ set) ────────────

def _local_now():
    return datetime.now().astimezone()


def _rfc3339(dt: datetime) -> str:
    """Serialize a datetime to RFC3339 with offset (what the API expects)."""
    return dt.astimezone().isoformat()


def _parse_dt(value: str) -> datetime:
    """Parse 'YYYY-MM-DD HH:MM', 'YYYY-MM-DD', or ISO-8601 → local-aware dt."""
    value = (value or "").strip()
    if not value:
        raise ValueError("A start time is required (e.g. 2026-08-06 15:00).")
    m = re.match(r"^(\d{4}-\d{2}-\d{2})(?:[ T](\d{1,2}):(\d{2}))?$", value)
    if m:
        y, mo, d = map(int, m.group(1).split("-"))
        hh, mm = (int(m.group(2)), int(m.group(3))) if m.group(2) else (9, 0)
        return datetime(y, mo, d, hh, mm).astimezone()
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.astimezone()
        return parsed
    except ValueError as exc:
        raise ValueError(f"Unrecognized date/time '{value}' — use YYYY-MM-DD HH:MM or ISO-8601.") from exc


# ── Read API ──────────────────────────────────────────────────────────────

def _fetch_events(service, time_min: datetime, time_max: datetime, max_results: int = 25, q: str = "") -> list:
    request = service.events().list(
        calendarId="primary",
        timeMin=_rfc3339(time_min),
        timeMax=_rfc3339(time_max),
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime",
        q=q or None,
    )
    items = request.execute().get("items", [])
    out = []
    for it in items:
        start = it.get("start", {}).get("dateTime") or it.get("start", {}).get("date")
        end = it.get("end", {}).get("dateTime") or it.get("end", {}).get("date")
        out.append({
            "id": it.get("id", ""),
            "summary": it.get("summary", "(no title)")[:120],
            "start": start or "",
            "end": end or "",
            "location": (it.get("location") or "")[:120],
            "description": (it.get("description") or "")[:300],
        })
    return out


def _day_bounds(day_offset: int = 0):
    """(start, end) of a local day, `day_offset` days from today."""
    today = _local_now().replace(hour=0, minute=0, second=0, microsecond=0)
    return today + timedelta(days=day_offset), today + timedelta(days=day_offset + 1)


def get_today() -> list:
    service = _build_service()
    start, end = _day_bounds(0)
    return _fetch_events(service, start, end)


def get_day(day_offset: int = 1) -> list:
    service = _build_service()
    start, end = _day_bounds(day_offset)
    return _fetch_events(service, start, end)


def get_upcoming(days: int = 7, max_results: int = 20) -> list:
    service = _build_service()
    start = _local_now()
    end = start + timedelta(days=max(1, days))
    return _fetch_events(service, start, end, max_results=max_results)


def search_events(query: str, days: int = 30, max_results: int = 15) -> list:
    service = _build_service()
    start = _local_now()
    end = start + timedelta(days=max(1, days))
    return _fetch_events(service, start, end, max_results=max_results, q=query)


# ── Draft store (approval-first) ──────────────────────────────────────────

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


def create_draft(summary: str, start: str, end: str = "", description: str = "") -> dict:
    """Persist a pending event and return it (id + expiry + parsed times)."""
    summary = (summary or "").strip()
    if not summary:
        raise ValueError("A meeting title is required.")
    start_dt = _parse_dt(start)
    if end and end.strip():
        end_dt = _parse_dt(end)
        if end_dt <= start_dt:
            raise ValueError("End time must be after start time.")
    else:
        end_dt = start_dt + timedelta(hours=1)

    drafts = _load_drafts()
    now = time.time()
    drafts = {k: v for k, v in drafts.items() if v.get("expires_at", 0) > now}

    draft = {
        "id": uuid.uuid4().hex,
        "summary": summary[:150],
        "start": _rfc3339(start_dt),
        "end": _rfc3339(end_dt),
        "description": (description or "").strip()[:500],
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


def create_from_draft(draft_id: str) -> dict:
    """Insert a pending draft into Google Calendar and mark it created."""
    draft = get_draft(draft_id)
    if not draft:
        raise CalendarUnavailableError("Event draft not found or expired — please preview again.")

    service = _build_service()
    body = {
        "summary": draft["summary"],
        "description": draft["description"],
        "start": {"dateTime": draft["start"]},
        "end": {"dateTime": draft["end"]},
    }
    created = service.events().insert(calendarId="primary", body=body).execute()

    drafts = _load_drafts()
    if draft_id in drafts:
        drafts[draft_id]["status"] = "created"
        drafts[draft_id]["event_id"] = created.get("id", "")
        _save_drafts(drafts)

    return {
        "draft_id": draft_id,
        "event_id": created.get("id", ""),
        "summary": draft["summary"],
        "start": draft["start"],
        "end": draft["end"],
        "created_at": int(time.time()),
    }


def cancel_draft(draft_id: str) -> bool:
    drafts = _load_drafts()
    if draft_id in drafts:
        drafts.pop(draft_id, None)
        _save_drafts(drafts)
        return True
    return False


# ── Friendly formatting for the AI brain ─────────────────────────────────

def _pretty_time(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%a %d %b, %I:%M %p")
    except Exception:
        return iso


def format_event_preview(draft: dict) -> str:
    return (
        f"{draft['summary']} on {_pretty_time(draft['start'])} → {_pretty_time(draft['end'])}"
    )


def format_events_for_speech(events: list, day_label: str = "today") -> str:
    if not events:
        return f"Nothing scheduled {day_label}."
    lines = [f"{len(events)} event(s) {day_label}:"]
    for e in events[:5]:
        t = _pretty_time(e["start"])
        loc = f" at {e['location']}" if e.get("location") else ""
        lines.append(f"- {t}: {e['summary']}{loc}")
    return " ".join(lines)
