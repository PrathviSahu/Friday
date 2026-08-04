"""Tests for the metrics, company intelligence and coding AI modules."""

import pytest


# ── Metrics ──────────────────────────────────────────────────────────────

def test_metrics_record_and_snapshot(monkeypatch, tmp_path):
    from services import metrics
    monkeypatch.setattr(metrics, "_samples", metrics.deque(maxlen=metrics.MAX_SAMPLES))
    metrics.record("llm", 123.4)
    metrics.record("llm", 200.0)
    metrics.record("stt", 50.0)
    snap = metrics.snapshot()
    assert snap["averages"]["llm"]["avg_ms"] == pytest.approx(161.7, abs=0.2)
    assert snap["averages"]["stt"]["count"] == 1


def test_metrics_timed_context():
    import time
    from services import metrics
    with metrics.timed("op"):
        time.sleep(0.01)
    snap = metrics.snapshot()
    assert "op" in snap["averages"]
    assert snap["averages"]["op"]["last_ms"] >= 5


def test_metrics_set_last():
    from services import metrics
    metrics.set_last(agent="career", tool="company_intel", action="none")
    assert metrics.snapshot()["last"]["agent"] == "career"
    assert metrics.snapshot()["last"]["tool"] == "company_intel"


def test_metrics_reset():
    from services import metrics
    metrics.record("x", 1.0)
    metrics.reset()
    assert metrics.snapshot()["averages"] == {}


# ── Company Intelligence ─────────────────────────────────────────────────

def test_company_intel_composes(monkeypatch):
    from services import company_intelligence
    monkeypatch.setattr(company_intelligence, "_search_company", lambda name: "Goldman Sachs is a global bank.")
    monkeypatch.setattr(company_intelligence, "_your_applications", lambda name: [
        {"title": "Software Engineer", "status": "interview", "applied_at": "2026-07-01", "salary_offered": 0, "notes": ""}])
    monkeypatch.setattr(company_intelligence, "_roles_at", lambda name: [
        {"title": "Software Engineer", "location": "Bengaluru"}])

    monkeypatch.setattr(company_intelligence, "_compose",
                        lambda name, web, apps, roles: f"BRIEF for {name} with {len(apps)} application(s).")
    intel = company_intelligence.get_company_intel("Goldman Sachs")
    assert intel["company"] == "Goldman Sachs"
    assert "1 application" in intel["report"]


def test_company_intel_requires_name():
    from services import company_intelligence
    with pytest.raises(company_intelligence.CompanyIntelUnavailableError):
        company_intelligence.get_company_intel("   ")


def test_company_intel_route_auth(remote_client):
    r = remote_client.get("/api/company/intel?name=Goldman")
    assert r.status_code == 401


def test_company_intel_route_ok(client, monkeypatch):
    from routes import company as company_routes
    monkeypatch.setattr(company_routes.company_intelligence, "get_company_intel",
                        lambda name: {"company": name, "report": "BRIEF", "web_found": True,
                                      "applications": 0, "roles_tracked": 0})
    r = client.get("/api/company/intel?name=Goldman%20Sachs")
    assert r.status_code == 200
    assert r.json()["report"] == "BRIEF"


# ── Coding AI ────────────────────────────────────────────────────────────

def test_coding_review_requires_code():
    from services import coding_agent
    with pytest.raises(coding_agent.CodingUnavailableError):
        coding_agent.review_code("   ")


def test_coding_review_uses_llm(monkeypatch):
    from services import coding_agent
    monkeypatch.setattr(coding_agent, "_llm", lambda s, c, e: "🔴 Critical: use parameterized queries")
    result = coding_agent.review_code("def q(x): return x", "python")
    assert "parameterized" in result


def test_coding_explain_and_tests(monkeypatch):
    from services import coding_agent
    monkeypatch.setattr(coding_agent, "_llm", lambda s, c, e: "explained")
    assert "explained" in coding_agent.explain_code("x = 1", "python")
    monkeypatch.setattr(coding_agent, "_llm", lambda s, c, e: "def test_x(): pass")
    assert "test_x" in coding_agent.generate_tests("x = 1", "python")


def test_coding_route_auth(remote_client):
    r = remote_client.post("/api/coding/review", json={"code": "x=1"})
    assert r.status_code == 401


def test_coding_route_ok(client, monkeypatch):
    from routes import coding as coding_routes
    monkeypatch.setattr(coding_routes.coding_agent, "review_code", lambda c, l: "looks fine")
    r = client.post("/api/coding/review", json={"code": "x = 1", "language": "python"})
    assert r.status_code == 200
    assert r.json()["result"] == "looks fine"
