"""Tests for the Phase 2.3 Ambient Context Engine.

Acceptance per next_phase_2_architecture.md §7:
  * meeting shield suppresses suggestions during a calendar event
  * focus mode forces the 'confirm' tier (autonomy integration)

All signals are injected/monkeypatched — no real calendar, email, or network.
The module's 30s TTL cache is reset between tests (autouse fixture).
"""

from datetime import datetime, timedelta

import pytest

from services import context_engine as ce
from services import autonomy_engine as ae

SAT = datetime(2026, 8, 8, 12, 0, 0)      # Saturday
MON = datetime(2026, 8, 10, 12, 0, 0)     # Monday


@pytest.fixture(autouse=True)
def _reset_context_state():
    ce.invalidate_cache()
    ce.clear_focus()
    yield
    ce.invalidate_cache()
    ce.clear_focus()


def _events(monkeypatch, events):
    """Stub the calendar signal: today returns `events` (start/end ISO strings)."""
    import services.calendar_agent as cal
    monkeypatch.setattr(cal, "is_configured", lambda: True)
    monkeypatch.setattr(cal, "get_today", lambda: events)


def _no_calendar(monkeypatch):
    import services.calendar_agent as cal
    monkeypatch.setattr(cal, "is_configured", lambda: False)


def _no_email(monkeypatch):
    import services.email_agent as em
    monkeypatch.setattr(em, "is_configured", lambda: False)


def _no_practice(monkeypatch):
    monkeypatch.setattr(ce, "_practice_gap_days", lambda now: None)


# ── Time & market signals ─────────────────────────────────────────────────────

@pytest.mark.parametrize("hour,expected", [
    (5, "morning"), (11, "morning"), (12, "afternoon"), (16, "afternoon"),
    (17, "evening"), (20, "evening"), (21, "night"), (4, "night"),
])
def test_time_of_day(hour, expected, monkeypatch):
    _no_calendar(monkeypatch); _no_email(monkeypatch); _no_practice(monkeypatch)
    vec = ce.get_context(now=SAT.replace(hour=hour))
    assert vec["time_of_day"] == expected


def test_day_type_and_market_window(monkeypatch):
    _no_calendar(monkeypatch); _no_email(monkeypatch); _no_practice(monkeypatch)
    # Saturday noon IST → weekend, market closed
    vec = ce.get_context(now=SAT)
    assert vec["day_type"] == "weekend" and vec["market_open"] is False
    # Monday 10:00 IST → trading weekday, NSE open (9:15–15:30)
    vec = ce.get_context(now=MON.replace(hour=10))
    assert vec["day_type"] == "trading_weekday" and vec["market_open"] is True
    # Boundary minutes
    assert ce.get_context(now=MON.replace(hour=9, minute=14))["market_open"] is False
    assert ce.get_context(now=MON.replace(hour=9, minute=15))["market_open"] is True
    assert ce.get_context(now=MON.replace(hour=15, minute=30))["market_open"] is True
    assert ce.get_context(now=MON.replace(hour=15, minute=31))["market_open"] is False


def test_quiet_hours_flag(monkeypatch):
    _no_calendar(monkeypatch); _no_email(monkeypatch); _no_practice(monkeypatch)
    assert ce.get_context(now=SAT.replace(hour=23))["quiet_hours"] is True
    assert ce.get_context(now=SAT.replace(hour=12))["quiet_hours"] is False


# ── Calendar pressure & meeting detection ─────────────────────────────────────

def test_calendar_pressure_math(monkeypatch):
    _no_email(monkeypatch); _no_practice(monkeypatch)
    _events(monkeypatch, [
        {"summary": "Standup", "start": (SAT + timedelta(minutes=60)).isoformat(),
         "end": (SAT + timedelta(minutes=90)).isoformat()},
    ])
    vec = ce.get_context(now=SAT)
    assert vec["calendar_pressure"] == pytest.approx(0.5)      # 1/(60/30)
    assert vec["next_meeting_in_min"] == 60
    assert vec["meeting_now"] is False


def test_pressure_caps_at_one_for_imminent_meeting(monkeypatch):
    _no_email(monkeypatch); _no_practice(monkeypatch)
    _events(monkeypatch, [
        {"summary": "Now-ish", "start": (SAT + timedelta(minutes=5)).isoformat(),
         "end": (SAT + timedelta(minutes=35)).isoformat()},
    ])
    assert ce.get_context(now=SAT)["calendar_pressure"] == 1.0


def test_meeting_now_when_event_spans_current_time(monkeypatch):
    _no_email(monkeypatch); _no_practice(monkeypatch)
    _events(monkeypatch, [
        {"summary": "Live sync",
         "start": (SAT - timedelta(minutes=15)).isoformat(),
         "end": (SAT + timedelta(minutes=45)).isoformat()},
    ])
    vec = ce.get_context(now=SAT)
    assert vec["meeting_now"] is True and vec["next_meeting_in_min"] is None


def test_calendar_unconfigured_degrades_gracefully(monkeypatch):
    _no_calendar(monkeypatch); _no_email(monkeypatch); _no_practice(monkeypatch)
    vec = ce.get_context(now=SAT)
    assert vec["calendar_pressure"] == 0.0 and vec["next_meeting_in_min"] is None


# ── Email & practice signals ─────────────────────────────────────────────────

def test_unread_email_signal(monkeypatch):
    _no_calendar(monkeypatch); _no_practice(monkeypatch)
    import services.email_agent as em
    monkeypatch.setattr(em, "is_configured", lambda: True)
    monkeypatch.setattr(em, "get_unread", lambda limit=15: [{"id": i} for i in range(7)])
    assert ce.get_context(now=SAT)["unread_email"] == 7


def test_unconfigured_email_yields_none(monkeypatch):
    _no_calendar(monkeypatch); _no_email(monkeypatch); _no_practice(monkeypatch)
    assert ce.get_context(now=SAT)["unread_email"] is None


def test_practice_gap_days(monkeypatch):
    _no_calendar(monkeypatch); _no_email(monkeypatch)
    import services.learning as learn
    last = (SAT - timedelta(days=3)).date().isoformat()
    monkeypatch.setattr(learn, "_streak_data", lambda: (0, 5, last))
    assert ce.get_context(now=SAT)["practice_gap_days"] == 3


# ── Focus mode ────────────────────────────────────────────────────────────────

def test_focus_mode_set_and_expiry(monkeypatch):
    _no_calendar(monkeypatch); _no_email(monkeypatch); _no_practice(monkeypatch)
    res = ce.set_focus(90, now=SAT)
    assert res["status"] == "ok" and res["focus_until"]
    assert ce.get_context(now=SAT)["focus_mode"] is True
    assert ce.get_context(now=SAT)["focus_until"] is not None
    later = SAT + timedelta(minutes=91)
    assert ce.get_context(now=later)["focus_mode"] is False


def test_focus_mode_validation_and_clear(monkeypatch):
    assert ce.set_focus(3, now=SAT)["status"] == "error"      # below 5 min
    assert ce.set_focus(999, now=SAT)["status"] == "error"    # above 480
    ce.set_focus(60, now=SAT)
    assert ce.clear_focus()["focus_mode"] is False
    _no_calendar(monkeypatch); _no_email(monkeypatch); _no_practice(monkeypatch)
    assert ce.get_context(now=SAT)["focus_mode"] is False


# ── TTL cache ─────────────────────────────────────────────────────────────────

def test_context_cache_avoids_double_source_hits(monkeypatch):
    calls = []
    _no_email(monkeypatch); _no_practice(monkeypatch)
    monkeypatch.setattr(ce, "_calendar_signals",
                        lambda now: calls.append(now) or {
                            "next_meeting_in_min": None, "meeting_now": False,
                            "calendar_pressure": 0.0})
    ce.get_context()   # explicit now=None → uses real clock + cache
    ce.get_context()
    assert len(calls) == 1                                   # second call cached
    ce.get_context(now=SAT)                                  # explicit now → bypass
    assert len(calls) == 2


# ── Brain interactions ────────────────────────────────────────────────────────

def test_cap_brevity_table():
    high = {"meeting_now": False, "focus_mode": False, "calendar_pressure": 0.8}
    calm = {"meeting_now": False, "focus_mode": False, "calendar_pressure": 0.1}
    meeting = {"meeting_now": True, "focus_mode": False, "calendar_pressure": 0.0}
    focus = {"meeting_now": False, "focus_mode": True, "calendar_pressure": 0.0}

    assert ce.cap_brevity("detailed", high) == "balanced"     # pressure cap
    assert ce.cap_brevity("detailed", calm) == "detailed"     # explicit asks win
    assert ce.cap_brevity("balanced", meeting) == "ultra_concise"
    assert ce.cap_brevity("balanced", focus) == "ultra_concise"
    assert ce.cap_brevity("ultra_concise", meeting) == "ultra_concise"


def test_situation_line_and_describe(monkeypatch):
    _no_email(monkeypatch); _no_practice(monkeypatch)
    _events(monkeypatch, [
        {"summary": "Review", "start": (SAT + timedelta(minutes=42)).isoformat(),
         "end": (SAT + timedelta(minutes=72)).isoformat()},
    ])
    line = ce.situation_line(SAT)
    assert "CURRENT SITUATION" in line and "next meeting in 42 min" in line
    spoken = ce.describe(SAT)
    assert spoken.startswith("Prem,") and "markets are closed" in spoken


# ── Autonomy integration (the acceptance criteria) ───────────────────────────

def test_meeting_shield_forces_confirm_tier(monkeypatch):
    _no_email(monkeypatch); _no_practice(monkeypatch)
    monkeypatch.setattr(ce, "_now", lambda: SAT)  # decide→context uses real clock
    _events(monkeypatch, [
        {"summary": "Live sync",
         "start": (SAT - timedelta(minutes=10)).isoformat(),
         "end": (SAT + timedelta(minutes=50)).isoformat()},
    ])
    ce.invalidate_cache()
    # Seed a high-trust reversible action that would normally earn silent tier.
    with ae._lock, ae._db() as conn:
        conn.execute("INSERT OR REPLACE INTO action_trust"
                     " (action_type, accepts, rejects, tier, last_acted_at)"
                     " VALUES ('ctx_shield_trading', 12, 0, 'silent', ?)",
                     (SAT.isoformat(timespec="seconds"),))
        conn.commit()
    from services import learning_engine
    with learning_engine._db() as conn:
        conn.execute("INSERT OR REPLACE INTO user_action_habits"
                     " (action_type, hour_of_day, day_of_week, frequency)"
                     " VALUES ('ctx_shield_trading', 12, 5, 12)")
        conn.commit()
    d = ae.decide("ctx_shield_trading", "open_trading", now=SAT)
    assert d["tier"] == "confirm" and d["blocked_reason"] == "meeting_in_progress"


def test_focus_mode_forces_confirm_tier(monkeypatch):
    _no_calendar(monkeypatch); _no_email(monkeypatch); _no_practice(monkeypatch)
    monkeypatch.setattr(ce, "_now", lambda: SAT)
    ce.set_focus(60, now=SAT)
    ce.invalidate_cache()
    d = ae.decide("ctx_focus_anything", "open_trading", now=SAT)
    assert d["tier"] == "confirm" and d["blocked_reason"] == "focus_mode"


# ── API round-trip ────────────────────────────────────────────────────────────

def test_context_endpoint_shape(client, monkeypatch):
    _no_calendar(monkeypatch); _no_email(monkeypatch); _no_practice(monkeypatch)
    ce.invalidate_cache()
    r = client.get("/api/context")
    assert r.status_code == 200
    ctx = r.json()["context"]
    for key in ("time_of_day", "day_type", "market_open", "next_meeting_in_min",
                "meeting_now", "unread_email", "calendar_pressure",
                "practice_gap_days", "focus_mode", "quiet_hours"):
        assert key in ctx


def test_focus_endpoint_round_trip(client):
    r = client.post("/api/context/focus", json={"minutes": 90})
    assert r.status_code == 200 and r.json()["status"] == "ok"
    assert r.json()["focus_until"]
    assert client.post("/api/context/focus", json={"minutes": 3}).status_code == 400
    assert client.post("/api/context/clear").json()["focus_mode"] is False


def test_context_endpoints_remote_blocked(remote_client):
    assert remote_client.get("/api/context").status_code == 401
    assert remote_client.post("/api/context/focus", json={"minutes": 90}).status_code == 401
    assert remote_client.post("/api/context/clear").status_code == 401


# ── Tool Router registration (voice path) ────────────────────────────────────

def test_context_tools_registered_and_dispatchable():
    from services.function_engine import get_tools_schema, dispatch
    names = {t["function"]["name"] for t in get_tools_schema()}
    assert {"get_context", "set_focus_mode"} <= names
    reply = dispatch("set_focus_mode", {"minutes": 45})
    assert "Focus mode on for 45 minutes" in reply
    ce.clear_focus()
