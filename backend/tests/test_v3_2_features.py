"""Tests for v3.2: Learning Coach, Life Memory (graph-lite), Developer Mode."""

from datetime import date, timedelta


# ═══ Learning Coach ═════════════════════════════════════════════════════════

def test_learning_log_and_dashboard(client):
    r = client.post("/api/learning/log", json={
        "title": "Two Sum", "category": "dsa", "minutes": 45, "solved": 2})
    assert r.status_code == 200
    d = r.json()["dashboard"]
    assert d["today_sessions"] >= 1
    assert d["today_minutes"] >= 45
    assert d["weekly_goals"]  # seeded goals exist


def test_learning_streak_computes_consecutive_days(client):
    from services.learning import log_session
    today = date.today()
    # backfill the previous two days
    for offset in (2, 1):
        log_session("Backfill", "dsa", 20, 1,
                    log_date=(today - timedelta(days=offset)).isoformat())
    r = client.get("/api/learning/streak")
    assert r.status_code == 200
    assert r.json()["current_streak"] >= 2


def test_learning_streak_check_notifies_after_3_days(client):
    from services.learning import log_session, check_streak
    from services.notifications import get_notifications
    # Isolate from other tests' sessions: wipe the log, then backdate one entry
    from services.learning import _connect
    with _connect() as conn:
        conn.execute("DELETE FROM learning_log")
        conn.commit()
    log_session("Old session", "java", 30, 1,
                log_date=(date.today() - timedelta(days=4)).isoformat())
    before = len(get_notifications(limit=1000))
    msg = check_streak()
    assert "haven't practiced" in msg
    after = len(get_notifications(limit=1000))
    assert after > before  # pushed a Learning Coach notification


def test_learning_log_requires_owner(client, remote_client):
    r = remote_client.post("/api/learning/log", json={"title": "x"})
    assert r.status_code == 401


# ═══ Life Memory ════════════════════════════════════════════════════════════

def test_life_memory_save_and_search(client):
    r = client.post("/api/life-memory", json={
        "subject": "Boss", "relation": "loves", "target": "cold brew",
        "category": "food"})
    assert r.status_code == 200
    mid = r.json()["memory_id"]

    r = client.get("/api/life-memory/search", params={"q": "what do I love"})
    assert r.status_code == 200
    assert any(m["target"] == "cold brew" for m in r.json()["matches"])
    assert "cold brew" in r.json()["answer"]

    r = client.delete(f"/api/life-memory/{mid}")
    assert r.status_code == 200


def test_life_memory_search_empty():
    from services.life_memory import answer_memory_query
    ans = answer_memory_query("zyxwv nonsense query 12345")
    assert "don't remember" in ans


def test_remember_fact_also_writes_life_memory():
    from services.function_engine import dispatch
    from services.life_memory import search_memories
    dispatch("remember_fact", {"key": "minimum_salary", "value": "7 LPA"})
    hits = search_memories("minimum salary", limit=5)
    assert any(h["target"] == "7 LPA" for h in hits)


# ═══ Function engine additions ══════════════════════════════════════════════

def test_log_learning_tool_dispatches():
    from services.function_engine import dispatch
    reply = dispatch("log_learning", {"title": "Binary Search", "category": "dsa",
                                      "minutes": 30, "solved": 1})
    assert "Logged" in reply


def test_search_memories_tool_dispatches():
    from services.function_engine import dispatch
    reply = dispatch("search_memories", {"query": "zyxwv nonexistent memory 999"})
    assert "don't remember" in reply


# ═══ Developer Mode ═════════════════════════════════════════════════════════

def test_dev_overview(client):
    r = client.get("/api/dev/overview")
    assert r.status_code == 200
    body = r.json()
    assert "facts" in body and "life_memories" in body
    assert body["uptime_seconds"] >= 0


def test_dev_logs(client):
    r = client.get("/api/dev/logs", params={"lines": 50})
    assert r.status_code == 200
    assert isinstance(r.json()["logs"], list)


def test_dev_config_never_leaks_secrets(client):
    r = client.get("/api/dev/config")
    assert r.status_code == 200
    body = r.json()
    assert body["version"]
    # env values are booleans only — the actual keys must not appear
    assert all(isinstance(v, bool) for v in body["env"].values())
    import json
    assert "your_key_here" not in json.dumps(body)


def test_dev_api_tester(client):
    r = client.post("/api/dev/test", json={
        "method": "GET", "path": "/api/system/stats"})
    assert r.status_code == 200
    assert r.json()["status"] == 200
    assert "cpu_percent" in r.json()["data"]


def test_dev_requires_owner(client, remote_client):
    r = remote_client.get("/api/dev/logs")
    assert r.status_code == 401
