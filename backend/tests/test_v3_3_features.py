"""Tests for v3.3: Second Brain, Memory Timeline, Goal Manager, explainable recs."""

from datetime import date, timedelta


# ═══ Second Brain ═══════════════════════════════════════════════════════════

def test_note_add_and_auto_categorize(client):
    # Idea capture: no type → auto-categorized as 'idea'
    r = client.post("/api/knowledge", json={
        "title": "Kafka architecture idea",
        "content": "maybe we should use a Kafka stream for the attendance pipeline",
    })
    assert r.status_code == 200
    assert r.json()["type"] == "idea" or r.json()["type"] == "code_snippet"

    # Explicit meeting note
    r = client.post("/api/knowledge", json={
        "title": "Sprint sync", "content": "Decided to use Playwright", "note_type": "meeting"})
    assert r.status_code == 200

    r = client.get("/api/knowledge")
    assert len(r.json()["notes"]) >= 2


def test_note_search_and_recall(client):
    client.post("/api/knowledge", json={
        "title": "AirChord project",
        "content": "chose Playwright instead of Selenium for browser automation",
        "note_type": "decision",
    })
    r = client.get("/api/knowledge/search", params={"q": "why playwright selenium"})
    assert r.status_code == 200
    assert r.json()["matches"]
    assert "Playwright" in r.json()["answer"] or "Playwright" in str(r.json()["matches"])


def test_project_memory(client):
    r = client.put("/api/knowledge/projects/Friday/architecture", json={
        "project": "Friday", "section": "architecture",
        "content": "FastAPI + React 19 + SQLite WAL"})
    assert r.status_code == 200
    r = client.get("/api/knowledge/projects/Friday")
    assert r.json()["sections"]["architecture"] == "FastAPI + React 19 + SQLite WAL"
    r = client.get("/api/knowledge/projects")
    assert any(p["project"] == "Friday" for p in r.json()["projects"])


def test_note_delete(client):
    r = client.post("/api/knowledge", json={"title": "temp", "content": "x"})
    nid = r.json()["note_id"]
    r = client.delete(f"/api/knowledge/{nid}")
    assert r.status_code == 200


# ═══ AI Memory Timeline ══════════════════════════════════════════════════════

def test_timeline_add_list_delete(client):
    r = client.post("/api/timeline", json={
        "event": "Finished AI Attendance System", "category": "project"})
    assert r.status_code == 200
    eid = r.json()["event_id"]

    r = client.get("/api/timeline", params={"category": "project"})
    assert any(e["id"] == eid for e in r.json()["events"])

    r = client.delete(f"/api/timeline/{eid}")
    assert r.status_code == 200


def test_timeline_summary_last_month(client):
    # backdate an event to ~10 days ago
    client.post("/api/timeline", json={
        "event": "Got internship", "category": "career",
        "event_date": (date.today() - timedelta(days=10)).isoformat()})
    r = client.get("/api/timeline/summary", params={"query": "last month"})
    assert r.status_code == 200
    body = r.json()
    assert "events" in body and "summary" in body
    assert any("internship" in e["event"].lower() for e in body["events"])


def test_timeline_period_for_query():
    from services.timeline import period_for_query
    since, until = period_for_query("this year")
    assert since.endswith("-01-01")
    since2, _ = period_for_query("last 30 days")
    assert since2 <= date.today().isoformat()


# ═══ Goal Manager ════════════════════════════════════════════════════════════

def test_goal_crud_and_progress(client):
    r = client.post("/api/goals", json={
        "title": "Get 8 LPA job", "target_value": 100, "unit": "%"})
    assert r.status_code == 200
    gid = r.json()["goal_id"]

    r = client.post(f"/api/goals/{gid}/progress", params={"amount": 25})
    assert r.status_code == 200
    assert r.json()["goal"]["current_value"] == 25

    r = client.get("/api/goals")
    g = next(x for x in r.json()["goals"] if x["id"] == gid)
    assert g["progress_pct"] == 25

    # hit 100% → auto-done
    for _ in range(3):
        client.post(f"/api/goals/{gid}/progress", params={"amount": 25})
    r = client.get("/api/goals")
    g = next(x for x in r.json()["goals"] if x["id"] == gid)
    assert g["status"] == "done" and g["progress_pct"] == 100

    r = client.delete(f"/api/goals/{gid}")
    assert r.status_code == 200


def test_goal_validation(client):
    r = client.post("/api/goals", json={"title": "", "target_value": 10})
    assert r.status_code == 400


# ═══ Function tools ══════════════════════════════════════════════════════════

def test_remember_idea_tool():
    from services.function_engine import dispatch
    reply = dispatch("remember_idea", {"title": "New idea", "content": "what if we build a plugin system"})
    assert "Captured" in reply


def test_log_milestone_tool():
    from services.function_engine import dispatch
    from services.timeline import list_events
    reply = dispatch("log_milestone", {"event": "AWS Certified", "category": "skill"})
    assert "timeline" in reply
    assert any(e["event"] == "AWS Certified" for e in list_events())


def test_update_goal_tool():
    from services.function_engine import dispatch
    reply = dispatch("update_goal", {"title": "Solve 100 DSA problems", "target": 100, "amount": 10})
    lowered = reply.lower()
    assert "updated" in lowered or "created" in lowered or "goal" in lowered


def test_search_notes_tool():
    from services.function_engine import dispatch
    reply = dispatch("search_notes", {"query": "zzz nonexistent note query"})
    assert "couldn't find" in reply


# ═══ Explainable career recommendations ══════════════════════════════════════

def test_recommendations_have_reasons():
    from services.career_intelligence import get_career_recommendations
    recs = get_career_recommendations(
        {"upcoming_deadlines": [{"title": "Google SWE", "company": "Google",
                                 "deadline": "2026-09-01"}],
         "high_priority": 3, "total_applications": 0},
        {}, [])
    assert recs
    for r in recs:
        assert "reasons" in r and isinstance(r["reasons"], list)
        assert r["reasons"]
