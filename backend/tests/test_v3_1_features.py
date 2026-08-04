"""Tests for v3.1: Permission Center, Automation Engine, Briefing, Multi-Agent."""

import json

import pytest


# ═══ Permission Center ═══════════════════════════════════════════════════════

def test_permissions_list_has_all_capabilities(client):
    r = client.get("/api/permissions")
    assert r.status_code == 200
    caps = {p["capability"]: p["mode"] for p in r.json()["permissions"]}
    # High-stakes capabilities default to ask/disabled
    assert caps["trades.execute"] == "ask"
    assert caps["files.delete"] == "disabled"
    assert caps["system.control"] == "enabled"  # current UI keeps working


def test_permission_mode_change_and_enforcement(client):
    # Set screen.capture -> disabled, then check enforcement is real
    r = client.put("/api/permissions", json={"capability": "screen.capture", "mode": "disabled"})
    assert r.status_code == 200
    from services.permissions import check_permission
    assert check_permission("screen.capture") == "denied"
    # restore
    client.put("/api/permissions", json={"capability": "screen.capture", "mode": "ask"})


def test_approval_flow(client):
    from services.permissions import check_permission, grant_approval, revoke_approval
    revoke_approval("trades.execute")
    assert check_permission("trades.execute") == "approval_required"
    r = client.post("/api/permissions/approve",
                    json={"capability": "trades.execute", "seconds": 60})
    assert r.status_code == 200
    assert check_permission("trades.execute") == "allowed"
    revoke_approval("trades.execute")
    assert check_permission("trades.execute") == "approval_required"


def test_paper_order_gated_by_permission(client):
    # trades.execute defaults to ask -> 403 approval_required without approval
    from services.permissions import revoke_approval
    revoke_approval("trades.execute")
    r = client.post("/api/trading/order", json={
        "symbol": "FX:EURUSD", "side": "buy", "quantity": 1})
    assert r.status_code == 403
    assert r.json()["detail"]["permission"] == "trades.execute"
    assert r.json()["detail"]["decision"] == "approval_required"

    # Grant one-time approval -> accepted (paper only)
    client.post("/api/permissions/approve",
                json={"capability": "trades.execute", "seconds": 60})
    r = client.post("/api/trading/order", json={
        "symbol": "FX:EURUSD", "side": "buy", "quantity": 1})
    assert r.status_code == 200
    assert r.json()["status"] == "paper_order_accepted"
    from services.permissions import revoke_approval
    revoke_approval("trades.execute")


def test_system_control_obeys_permission_mode(client):
    from services.permissions import set_mode, check_permission
    set_mode("system.control", "disabled")
    assert check_permission("system.control") == "denied"
    r = client.post("/api/system/display/lock")
    assert r.status_code == 403
    # restore so the app keeps working
    set_mode("system.control", "enabled")
    assert check_permission("system.control") == "allowed"


# ═══ Automation Engine ═══════════════════════════════════════════════════════

def test_automation_crud(client):
    r = client.post("/api/automations", json={
        "name": "Morning Briefing",
        "trigger_type": "daily",
        "daily_time": "09:00",
        "action": "briefing",
    })
    assert r.status_code == 200
    aid = r.json()["automation_id"]

    r = client.get("/api/automations")
    assert any(a["id"] == aid and a["action"] == "briefing"
               for a in r.json()["automations"])

    r = client.put(f"/api/automations/{aid}", json={"enabled": False})
    assert r.status_code == 200

    r = client.delete(f"/api/automations/{aid}")
    assert r.status_code == 200


def test_automation_validation(client):
    r = client.post("/api/automations", json={
        "name": "Bad", "trigger_type": "interval", "interval_seconds": 5,
        "action": "briefing"})
    assert r.status_code == 400  # interval must be >= 60


def test_automation_run_now_pushes_notification(client):
    r = client.post("/api/automations", json={
        "name": "Test Briefing", "trigger_type": "interval", "interval_seconds": 3600,
        "action": "briefing"})
    aid = r.json()["automation_id"]
    r = client.post(f"/api/automations/{aid}/run")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    r = client.get("/api/notifications")
    assert r.status_code == 200
    assert any(n["category"] == "briefing" for n in r.json()["notifications"])
    client.delete(f"/api/automations/{aid}")


def test_notification_mark_read(client):
    from services.notifications import push_notification
    nid = push_notification("Test", "hello", "general")
    r = client.post(f"/api/notifications/{nid}/read")
    assert r.status_code == 200
    r = client.get("/api/notifications", params={"unread_only": True})
    assert all(n["id"] != nid for n in r.json()["notifications"])


# ═══ Daily Briefing ══════════════════════════════════════════════════════════

def test_briefing_structure(client):
    r = client.get("/api/briefing")
    assert r.status_code == 200
    body = r.json()
    assert body["generated_at"]
    assert len(body["sections"]) >= 4
    titles = {s["title"] for s in body["sections"]}
    assert {"Weather", "Tasks", "Career"} <= titles
    assert body["spoken_summary"]


# ═══ Multi-Agent framework ═══════════════════════════════════════════════════

def test_agents_list(client):
    r = client.get("/api/agents")
    assert r.status_code == 200
    keys = {a["key"] for a in r.json()["agents"]}
    assert {"career", "coding", "research", "finance", "communication", "automation"} <= keys


def test_agent_routing():
    from services.agents import route_to_agent
    assert route_to_agent("apply for java jobs in bangalore") == "career"
    assert route_to_agent("what's the trend on gold") == "finance"
    assert route_to_agent("debug this react error") == "coding"
    assert route_to_agent("research vector databases") == "research"
    assert route_to_agent("summarize my emails") == "communication"
    assert route_to_agent("run the briefing every morning") == "automation"


def test_agent_tools_are_filtered():
    from services.agents import tools_for_agent
    finance_tools = {t["function"]["name"] for t in tools_for_agent("finance")}
    assert "technical_analysis" in finance_tools
    assert "remember_fact" not in finance_tools  # scoped, not the full registry


def test_agent_chat_falls_back_without_keys(client, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    r = client.post("/api/agent/chat", json={"text": "check my trading charts"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("agent") == "finance"
    assert body.get("reply")
