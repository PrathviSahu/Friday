"""Tests for the Calendar Agent (service + routes).

The Google API client is never invoked — `_build_service` is faked with an
in-memory event list so tests stay offline.
"""

import json
import time

import pytest


# ── Fake Google Calendar service ─────────────────────────────────────────

class FakeCalendarService:
    """Minimal in-memory calendar service with list() + insert()."""

    def __init__(self, events=None):
        self.events_list = events or []
        self.inserted = []

    def events(self):
        return self

    def list(self, calendarId=None, timeMin=None, timeMax=None, maxResults=25,
             singleEvents=True, orderBy="startTime", q=None):
        self._q = q
        return self

    def execute(self):
        # list() → return stored events (q filter naive match)
        items = self.events_list
        if getattr(self, "_q", None):
            items = [e for e in items if self._q.lower() in e["summary"].lower()]
        return {"items": items}

    def insert(self, calendarId=None, body=None):
        self.inserted.append(body)
        return type("Resp", (), {"execute": lambda self: {"id": "evt-123", **body}})()


@pytest.fixture(autouse=True)
def _patch_build(monkeypatch):
    from services import calendar_agent
    fake = FakeCalendarService()
    monkeypatch.setattr(calendar_agent, "_build_service", lambda: fake)
    return fake


# ── Service: reading ─────────────────────────────────────────────────────

def _evt(summary, start, end, loc=""):
    # Mirrors the real Google Calendar API item shape
    return {"id": "x", "summary": summary,
            "start": {"dateTime": start}, "end": {"dateTime": end},
            "location": loc, "description": ""}


def test_get_today_returns_events(_patch_build):
    from services import calendar_agent
    _patch_build.events_list = [
        _evt("Standup", "2026-08-05T09:30:00+05:30", "2026-08-05T09:45:00+05:30", "Zoom"),
        _evt("Interview prep", "2026-08-05T18:00:00+05:30", "2026-08-05T19:00:00+05:30"),
    ]
    events = calendar_agent.get_today()
    assert len(events) == 2
    assert events[0]["summary"] == "Standup"
    assert events[0]["location"] == "Zoom"


def test_search_events_filters(_patch_build):
    from services import calendar_agent
    _patch_build.events_list = [
        _evt("DSA practice", "2026-08-05T10:00:00+05:30", "2026-08-05T11:00:00+05:30"),
        _evt("Gym", "2026-08-05T18:00:00+05:30", "2026-08-05T19:00:00+05:30"),
    ]
    results = calendar_agent.search_events("dsa")
    assert len(results) == 1
    assert results[0]["summary"] == "DSA practice"


def test_format_events_for_speech_empty():
    from services import calendar_agent
    assert "Nothing scheduled" in calendar_agent.format_events_for_speech([], "today")


# ── Service: draft → create (approval-first) ─────────────────────────────

def test_create_draft_validates():
    from services import calendar_agent
    with pytest.raises(ValueError):
        calendar_agent.create_draft("", "2026-08-06 15:00")
    with pytest.raises(ValueError):
        calendar_agent.create_draft("Hi", "2026-08-06 15:00", "2026-08-06 14:00")  # end < start


def test_create_draft_defaults_end_plus_one_hour(monkeypatch, tmp_path):
    from services import calendar_agent
    monkeypatch.setattr(calendar_agent, "DRAFTS_FILE", tmp_path / "drafts.json")
    d = calendar_agent.create_draft("Standup", "2026-08-06 10:00")
    assert d["end"].startswith("2026-08-06T11:00")


def test_draft_expires(monkeypatch, tmp_path):
    from services import calendar_agent
    monkeypatch.setattr(calendar_agent, "DRAFTS_FILE", tmp_path / "drafts.json")
    d = calendar_agent.create_draft("Standup", "2026-08-06 10:00")
    assert calendar_agent.get_draft(d["id"]) is not None
    drafts = json.loads((tmp_path / "drafts.json").read_text())
    drafts[d["id"]]["expires_at"] = time.time() - 1
    (tmp_path / "drafts.json").write_text(json.dumps(drafts))
    assert calendar_agent.get_draft(d["id"]) is None
    with pytest.raises(calendar_agent.CalendarUnavailableError):
        calendar_agent.create_from_draft(d["id"])


def test_create_from_draft_inserts(_patch_build, monkeypatch, tmp_path):
    from services import calendar_agent
    monkeypatch.setattr(calendar_agent, "DRAFTS_FILE", tmp_path / "drafts.json")
    d = calendar_agent.create_draft("Client call", "2026-08-07 15:00", "", "Discuss offer")
    result = calendar_agent.create_from_draft(d["id"])
    assert result["event_id"] == "evt-123"
    assert len(_patch_build.inserted) == 1
    body = _patch_build.inserted[0]
    assert body["summary"] == "Client call"
    assert body["description"] == "Discuss offer"
    assert body["start"]["dateTime"].startswith("2026-08-07T15:00")
    assert calendar_agent.get_draft(d["id"]) is None  # marked created


# ── Routes ───────────────────────────────────────────────────────────────

def test_calendar_status_requires_auth(remote_client):
    r = remote_client.get("/api/calendar/status")
    assert r.status_code == 401


def test_calendar_today_requires_permission(client):
    """calendar.read defaults to 'ask' → 403 without approval."""
    r = client.get("/api/calendar/today")
    assert r.status_code == 403


def test_calendar_today_ok_when_permitted(client, _patch_build, monkeypatch):
    from services import permissions
    permissions.set_mode("calendar.read", "enabled")
    _patch_build.events_list = [_evt("Standup", "2026-08-05T09:30:00+05:30", "2026-08-05T09:45:00+05:30")]
    r = client.get("/api/calendar/today")
    assert r.status_code == 200
    assert len(r.json()["events"]) == 1


def test_calendar_draft_and_create_flow(client, _patch_build, monkeypatch, tmp_path):
    """Draft (calendar.read) → create (calendar.write) with both enabled."""
    from services import permissions
    from routes import calendar as calendar_routes
    permissions.set_mode("calendar.read", "enabled")
    permissions.set_mode("calendar.write", "enabled")
    monkeypatch.setattr(calendar_routes.calendar_agent, "DRAFTS_FILE", tmp_path / "drafts.json")

    r = client.post("/api/calendar/draft", json={"summary": "Standup", "start": "2026-08-06 10:00"})
    assert r.status_code == 200
    draft_id = r.json()["draft_id"]

    r = client.post("/api/calendar/create", json={"draft_id": draft_id})
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert len(_patch_build.inserted) == 1


def test_calendar_create_requires_permission(client, monkeypatch, tmp_path):
    """calendar.write stays 'ask' → create must 403 without a grant."""
    from services import permissions
    from routes import calendar as calendar_routes
    permissions.set_mode("calendar.read", "enabled")
    permissions.set_mode("calendar.write", "ask")
    monkeypatch.setattr(calendar_routes.calendar_agent, "DRAFTS_FILE", tmp_path / "drafts.json")

    r = client.post("/api/calendar/draft", json={"summary": "Standup", "start": "2026-08-06 10:00"})
    draft_id = r.json()["draft_id"]
    r = client.post("/api/calendar/create", json={"draft_id": draft_id})
    assert r.status_code == 403


def test_calendar_create_with_approval(client, _patch_build, monkeypatch, tmp_path):
    """One-time approval via /api/permissions/approve → create succeeds."""
    from services import permissions
    from routes import calendar as calendar_routes
    permissions.set_mode("calendar.read", "enabled")
    monkeypatch.setattr(calendar_routes.calendar_agent, "DRAFTS_FILE", tmp_path / "drafts.json")

    r = client.post("/api/calendar/draft", json={"summary": "Standup", "start": "2026-08-06 10:00"})
    draft_id = r.json()["draft_id"]
    r = client.post("/api/permissions/approve", json={"capability": "calendar.write", "seconds": 120})
    assert r.status_code == 200
    r = client.post("/api/calendar/create", json={"draft_id": draft_id})
    assert r.status_code == 200
    assert len(_patch_build.inserted) == 1
