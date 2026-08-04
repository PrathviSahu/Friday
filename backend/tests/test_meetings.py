"""Tests for the Meeting Assistant (service + routes).

STT and LLM extraction are faked — no network, no API credits.
"""

import pytest


# ── Service ──────────────────────────────────────────────────────────────

def test_extract_meeting_structure(monkeypatch):
    """LLM JSON extraction is parsed into a clean structure."""
    from services import meeting_agent

    class FakeMsg:
        content = (
            '{"title": "Sprint planning", "summary": "We planned the sprint.", '
            '"key_points": ["Three stories"], "decisions": ["Use Postgres"], '
            '"action_items": [{"text": "Write tests", "owner": "Prem"}, '
            '{"text": "Deploy", "owner": ""}]}'
        )

    class FakeChoice:
        message = FakeMsg()

    class FakeCompletion:
        choices = [FakeChoice()]

    class FakeCompletions:
        def __init__(self): self.called = False
        def create(self, **kwargs):
            self.called = True
            return FakeCompletion()

    class FakeChat:
        def __init__(self): self.completions = FakeCompletions()

    class FakeClient:
        def __init__(self): self.chat = FakeChat()

    fake = FakeClient()
    monkeypatch.setattr(meeting_agent, "_get_groq_client", lambda: fake)
    result = meeting_agent.extract_meeting_structure("transcript...")
    assert fake.chat.completions.called
    assert result["title"] == "Sprint planning"
    assert len(result["action_items"]) == 2
    assert result["action_items"][0]["owner"] == "Prem"


def test_extract_meeting_structure_no_client(monkeypatch):
    from services import meeting_agent
    monkeypatch.setattr(meeting_agent, "_get_groq_client", lambda: None)
    with pytest.raises(meeting_agent.MeetingUnavailableError):
        meeting_agent.extract_meeting_structure("hi")


def test_save_meeting_mirrors_knowledge(monkeypatch):
    """Saved meetings land in the DB AND the Knowledge OS."""
    from services import meeting_agent
    mirrored = {}
    monkeypatch.setattr(meeting_agent, "kb_add_note",
                        lambda **kw: mirrored.update(kw))
    structure = {
        "title": "Standup", "summary": "Quick sync.",
        "key_points": [], "decisions": [], "action_items": [],
    }
    meeting = meeting_agent.save_meeting("transcript", structure, source="text")
    assert meeting["id"]
    assert mirrored["note_type"] == "meeting"
    assert meeting_agent.get_meeting(meeting["id"])["title"] == "Standup"


def test_process_meeting_full_pipeline(monkeypatch):
    from services import meeting_agent

    def fake_extract(transcript):
        return {"title": "Review", "summary": "Went well", "key_points": [],
                "decisions": [], "action_items": [{"text": "Fix bug", "owner": ""}]}

    monkeypatch.setattr(meeting_agent, "extract_meeting_structure", fake_extract)
    meeting = meeting_agent.process_meeting("long transcript", source="text")
    assert meeting["title"] == "Review"
    assert meeting_agent.list_meetings(limit=5)[0]["id"] == meeting["id"]


def test_push_action_items_to_todos(monkeypatch, tmp_path):
    from services import meeting_agent
    added = []
    monkeypatch.setattr("services.todos._save", lambda items: None)
    monkeypatch.setattr("services.todos.DATA_FILE", tmp_path / "todos.json")
    monkeypatch.setattr(meeting_agent, "get_meeting", lambda mid: {
        "id": mid, "title": "T", "date": "", "summary": "", "key_points": [],
        "decisions": [], "transcript": "", "source": "text",
        "action_items": [{"text": "Fix bug", "owner": "Prem"}],
    })

    # patch add_todo to capture
    def fake_add_todo(text, priority="normal"):
        added.append((text, priority))
        return {"id": "x", "text": text, "priority": priority}
    monkeypatch.setattr("services.todos.add_todo", fake_add_todo)

    result = meeting_agent.push_action_items_to_todos("m1")
    assert added == [("[Prem] Fix bug", "high")]
    assert result["added"] == ["[Prem] Fix bug"]


# ── Routes ───────────────────────────────────────────────────────────────

def test_meetings_list_requires_auth(remote_client):
    r = remote_client.get("/api/meetings")
    assert r.status_code == 401


def test_meetings_process_requires_auth(remote_client):
    r = remote_client.post("/api/meetings/process", json={"transcript": "hi"})
    assert r.status_code == 401


def test_meetings_process_ok(client, monkeypatch):
    from routes import meetings as meetings_routes
    meeting = {"id": "m1", "title": "Sync", "date": "", "duration_s": 0,
               "summary": "Went well", "key_points": [], "decisions": [],
               "action_items": [], "transcript": "hi", "source": "text"}
    monkeypatch.setattr(meetings_routes.meeting_agent, "process_meeting",
                        lambda transcript, source: meeting)
    r = client.post("/api/meetings/process", json={"transcript": "we discussed the roadmap"})
    assert r.status_code == 200
    assert r.json()["meeting"]["title"] == "Sync"


def test_meetings_process_empty_rejected(client):
    r = client.post("/api/meetings/process", json={"transcript": "   "})
    assert r.status_code == 400


def test_meetings_transcribe_oversized(client, monkeypatch):
    from routes import meetings as meetings_routes
    monkeypatch.setattr(meetings_routes.meeting_agent, "MAX_UPLOAD_BYTES", 100)
    blob = b"x" * 200
    r = client.post("/api/meetings/transcribe", files={"audio": ("m.ogg", blob, "audio/ogg")})
    assert r.status_code == 413


def test_meetings_transcribe_ok(client, monkeypatch):
    from routes import meetings as meetings_routes
    meeting = {"id": "m2", "title": "Call", "date": "", "duration_s": 0,
               "summary": "Called", "key_points": [], "decisions": [],
               "action_items": [], "transcript": "audio text", "source": "audio"}
    monkeypatch.setattr(meetings_routes.meeting_agent, "process_meeting_audio",
                        lambda data, fn, mt: meeting)
    r = client.post("/api/meetings/transcribe",
                    files={"audio": ("m.ogg", b"fake-audio", "audio/ogg")})
    assert r.status_code == 200
    assert r.json()["meeting"]["source"] == "audio"


def test_meetings_search_and_action_items(client, monkeypatch):
    from routes import meetings as meetings_routes
    monkeypatch.setattr(meetings_routes.meeting_agent, "search_meetings",
                        lambda q: [{"id": "m1", "title": "Sync", "date": "",
                                    "summary": "hi", "key_points": [], "decisions": [],
                                    "action_items": [], "transcript": "", "source": "text"}])
    r = client.get("/api/meetings/search?q=sync")
    assert r.status_code == 200
    assert len(r.json()["meetings"]) == 1

    monkeypatch.setattr(meetings_routes.meeting_agent, "get_action_items",
                        lambda: [{"meeting_id": "m1", "meeting_title": "Sync",
                                  "meeting_date": "", "text": "Fix bug", "owner": "Prem"}])
    r = client.get("/api/meetings/action-items")
    assert r.status_code == 200
    assert r.json()["action_items"][0]["text"] == "Fix bug"


def test_meetings_push_todos_route(client, monkeypatch):
    from routes import meetings as meetings_routes
    monkeypatch.setattr(meetings_routes.meeting_agent, "push_action_items_to_todos",
                        lambda mid: {"meeting_id": mid, "added": ["[Prem] Fix bug"]})
    r = client.post("/api/meetings/m1/todos")
    assert r.status_code == 200
    assert r.json()["added"] == ["[Prem] Fix bug"]
