"""context_engine.py — Ambient Context Engine (Phase 2.3).

Fuses live situational signals into a single **Context Vector** consumed by
the brain, the briefing, and the Autonomy & Trust Engine, per
next_phase_2_architecture.md §4-C:

    time_of_day, day_type, market_open, next_meeting_in_min, meeting_now,
    unread_email, calendar_pressure, practice_gap_days, focus_mode, quiet_hours

Design rules:
  * NO background polling — the vector is computed on demand from each
    source's own fresh accessor, with a 30s in-process TTL cache so one chat
    turn (brain inject + autonomy decide) doesn't double-hit network sources.
  * Every source is graceful: calendar/email unconfigured or offline → that
    field degrades to None/0, never an exception. A broken signal must never
    break a chat turn or an autonomy decision.
  * `now` is injectable everywhere for deterministic tests.

Consumers already wired:
  * autonomy_engine._blocked_by_context() — meeting shield + focus mode force
    the 'confirm' tier (import guard added in Phase 2.1).
  * brain.py — brevity cap: pressure/focus/meeting shortens replies.
  * brain_v2 — the vector is injected into the system prompt as a
    "CURRENT SITUATION" line so the LLM adapts tone/pace and prioritization.

Focus mode is in-memory (same lifetime doctrine as permissions one-time
approvals): quiet hours unchanged, restart clears it.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# ── Constants (next_phase_2_architecture.md §4-C) ─────────────────────────────

CACHE_TTL_SECONDS = 30
PRESSURE_EVENT_HORIZON_MIN = 360       # only events within 6h pressurize
PRESSURE_HIGH = 0.70                   # ≥ → brevity cap applies
QUIET_HOUR_START = 22                  # same doctrine as autonomy_engine
QUIET_HOUR_END = 7
FOCUS_MIN_MINUTES = 5
FOCUS_MAX_MINUTES = 480                # 8h cap
IST = ZoneInfo("Asia/Kolkata")


def _now() -> datetime:
    """Single clock — monkeypatched by tests."""
    return datetime.now()


# ── Focus mode (in-memory, like permissions._APPROVALS) ───────────────────────

_focus_until: datetime | None = None


def set_focus(minutes: int, now: datetime | None = None) -> dict:
    """Focus mode ON for `minutes` — autonomy forced confirm, proactive muted."""
    global _focus_until
    now = now or _now()
    minutes = int(minutes)
    if not (FOCUS_MIN_MINUTES <= minutes <= FOCUS_MAX_MINUTES):
        return {"status": "error",
                "message": f"focus minutes must be {FOCUS_MIN_MINUTES}–{FOCUS_MAX_MINUTES}"}
    _focus_until = now + timedelta(minutes=minutes)
    invalidate_cache()
    return {"status": "ok", "focus_until": _focus_until.isoformat(timespec="seconds"),
            "minutes": minutes}


def clear_focus() -> dict:
    """Focus mode OFF (voice: 'focus off' / dashboard toggle)."""
    global _focus_until
    _focus_until = None
    invalidate_cache()
    return {"status": "ok", "focus_mode": False}


def _focus_active(now: datetime) -> bool:
    return bool(_focus_until and now < _focus_until)


# ── Signal sources (each graceful) ────────────────────────────────────────────

def _time_of_day(now: datetime) -> str:
    h = now.hour
    if 5 <= h < 12:
        return "morning"
    if 12 <= h < 17:
        return "afternoon"
    if 17 <= h < 21:
        return "evening"
    return "night"


def _market_open(now: datetime) -> bool:
    """NSE window: Mon–Fri 09:15–15:30 IST (mirrors indian_market_data, now-driven)."""
    now_ist = now.astimezone(IST) if now.tzinfo else now.replace(tzinfo=IST)
    if now_ist.weekday() >= 5:
        return False
    open_t = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
    close_t = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
    return open_t <= now_ist <= close_t


def _calendar_signals(now: datetime) -> dict:
    """next_meeting_in_min / meeting_now / calendar_pressure from today's events."""
    out = {"next_meeting_in_min": None, "meeting_now": False, "calendar_pressure": 0.0}
    try:
        from services import calendar_agent
        if not calendar_agent.is_configured():
            return out
        events = calendar_agent.get_today() or []
    except Exception:
        return out

    horizon = now + timedelta(minutes=PRESSURE_EVENT_HORIZON_MIN)
    pressure = 0.0
    next_min = None
    for ev in events:
        start = _parse_iso(ev.get("start"))
        end = _parse_iso(ev.get("end"))
        if start is None:
            continue
        start = _align_tz(start, now)
        end = _align_tz(end, now) if end else start + timedelta(hours=1)
        if start <= now <= end and (end - now).total_seconds() > 0:
            out["meeting_now"] = True
        elif now < start <= horizon:
            mins = (start - now).total_seconds() / 60.0
            if next_min is None or mins < next_min:
                next_min = mins
            pressure += 1.0 / max(mins / 30.0, 0.25)   # near events dominate
    out["next_meeting_in_min"] = int(round(next_min)) if next_min is not None else None
    out["calendar_pressure"] = round(min(1.0, pressure), 4)
    return out


def _unread_email() -> int | None:
    """Unread inbox count, or None when email isn't configured/reachable."""
    try:
        from services import email_agent
        if not email_agent.is_configured():
            return None
        return len(email_agent.get_unread(limit=15) or [])
    except Exception:
        return None


def _practice_gap_days(now: datetime) -> int | None:
    """Days since the last learning-coach session (None = never practiced)."""
    try:
        from services import learning
        _, _, last_date = learning._streak_data()
        if not last_date:
            return None
        last = datetime.fromisoformat(str(last_date))
        return max(0, (now.date() - last.date()).days)
    except Exception:
        return None


def _parse_iso(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _align_tz(dt: datetime, ref: datetime) -> datetime:
    """Make dt comparable to ref (mixing naive local & aware RFC3339 times)."""
    if dt.tzinfo and not ref.tzinfo:
        return dt.astimezone().replace(tzinfo=None)
    if ref.tzinfo and not dt.tzinfo:
        return dt.replace(tzinfo=ref.tzinfo)
    return dt


# ── Context Vector ────────────────────────────────────────────────────────────

_cache: dict = {"at": None, "vec": None}


def invalidate_cache() -> None:
    _cache["at"] = None
    _cache["vec"] = None


def get_context(now: datetime | None = None, use_cache: bool = True) -> dict:
    """The Ambient Context Vector. Explicit `now` bypasses the TTL cache."""
    real_now = now or _now()
    if now is None and use_cache and _cache["vec"] is not None \
            and _cache["at"] and (real_now - _cache["at"]).total_seconds() < CACHE_TTL_SECONDS:
        return dict(_cache["vec"])

    cal = _calendar_signals(real_now)
    vec = {
        "time_of_day": _time_of_day(real_now),
        "day_type": "trading_weekday" if real_now.weekday() < 5 else "weekend",
        "market_open": _market_open(real_now),
        "next_meeting_in_min": cal["next_meeting_in_min"],
        "meeting_now": cal["meeting_now"],
        "unread_email": _unread_email(),
        "calendar_pressure": cal["calendar_pressure"],
        "practice_gap_days": _practice_gap_days(real_now),
        "focus_mode": _focus_active(real_now),
        "focus_until": _focus_until.isoformat(timespec="seconds")
                       if _focus_active(real_now) else None,
        "quiet_hours": real_now.hour >= QUIET_HOUR_START or real_now.hour < QUIET_HOUR_END,
    }
    if now is None and use_cache:
        _cache["at"], _cache["vec"] = real_now, dict(vec)
    return vec


# ── Brain interactions ────────────────────────────────────────────────────────

def cap_brevity(style: str, vec: dict | None = None) -> str:
    """Context-aware brevity cap (Phase 2.3 brain interaction).

    Under situational pressure (meeting in progress, focus mode, or high
    calendar pressure) FRIDAY shortens replies: 'detailed' → 'balanced';
    during an active meeting or focus mode, 'balanced' → 'ultra_concise'.
    'ultra_concise' is never widened — explicit detail requests still win
    over pressure (the user's ask outranks ambient state).
    """
    vec = vec or get_context()
    urgent = vec.get("meeting_now") or vec.get("focus_mode")
    pressured = urgent or (vec.get("calendar_pressure") or 0.0) >= PRESSURE_HIGH
    if style == "detailed" and pressured:
        return "balanced"
    if style == "balanced" and urgent:
        return "ultra_concise"
    return style


def situation_line(now: datetime | None = None) -> str:
    """One-line '🧭 CURRENT SITUATION' string for the brain's system prompt."""
    v = get_context(now)
    parts = [f"{v['time_of_day']} ({v['day_type']})"]
    parts.append("market OPEN" if v["market_open"] else "market closed")
    if v["meeting_now"]:
        parts.append("IN A MEETING NOW — keep it brief")
    elif v["next_meeting_in_min"] is not None:
        parts.append(f"next meeting in {v['next_meeting_in_min']} min")
    if v["unread_email"] is not None:
        parts.append(f"{v['unread_email']} unread emails")
    if v["practice_gap_days"] is not None and v["practice_gap_days"] >= 2:
        parts.append(f"no practice for {v['practice_gap_days']} days")
    if v["focus_mode"]:
        parts.append("FOCUS MODE on — no interruptions")
    if v["quiet_hours"]:
        parts.append("quiet hours")
    return "🧭 CURRENT SITUATION: " + "; ".join(parts) + "."


def describe(now: datetime | None = None) -> str:
    """Voice-friendly spoken summary (READ_CONTEXT intent: 'situation batao')."""
    v = get_context(now)
    spoken = [f"It's {v['time_of_day']}, {v['day_type'].replace('_', ' ')}"]
    spoken.append("markets are open" if v["market_open"] else "markets are closed")
    if v["meeting_now"]:
        spoken.append("you're in a meeting right now")
    elif v["next_meeting_in_min"] is not None:
        spoken.append(f"next meeting in {v['next_meeting_in_min']} minutes")
    if v["unread_email"]:
        spoken.append(f"{v['unread_email']} unread emails waiting")
    if v["focus_mode"]:
        spoken.append("focus mode is on")
    return "Prem, " + "; ".join(spoken) + "."
