"""Tests for the WhatsApp Agent (service + routes).

The Playwright driver is never launched — we test the surrounding
architecture (drafts, permission gates, approval flow) with a fake driver.
"""

import json
import time

import pytest


@pytest.fixture(autouse=True)
def _patch_env(monkeypatch):
    # Disable the real driver; simulate "enabled but not connected" paths
    # by patching whatsapp_agent.ENABLED where needed.
    monkeypatch.setenv("FRIDAY_WHATSAPP_ENABLED", "0")
    import services.whatsapp_agent as wa
    monkeypatch.setattr(wa, "ENABLED", False)


# ── Draft store ──────────────────────────────────────────────────────────

def test_create_draft_validates():
    from services import whatsapp_agent
    with pytest.raises(ValueError):
        whatsapp_agent.create_draft("", "hi")
    with pytest.raises(ValueError):
        whatsapp_agent.create_draft("123", "hi")  # too short


def test_draft_roundtrip_and_expiry(monkeypatch, tmp_path):
    from services import whatsapp_agent
    monkeypatch.setattr(whatsapp_agent, "DRAFTS_FILE", tmp_path / "wa.json")
    d = whatsapp_agent.create_draft("+91 98765 43210", "See you at 6")
    assert d["phone"] == "919876543210"
    assert whatsapp_agent.get_draft(d["id"]) is not None

    drafts = json.loads((tmp_path / "wa.json").read_text())
    drafts[d["id"]]["expires_at"] = time.time() - 1
    (tmp_path / "wa.json").write_text(json.dumps(drafts))
    assert whatsapp_agent.get_draft(d["id"]) is None


# ── Routes ───────────────────────────────────────────────────────────────

def test_whatsapp_status_requires_auth(remote_client):
    r = remote_client.get("/api/whatsapp/status")
    assert r.status_code == 401


def test_whatsapp_qr_when_disabled(client):
    """Driver disabled → QR returns a clean 503, not a crash."""
    r = client.get("/api/whatsapp/qr")
    assert r.status_code == 503


def test_whatsapp_chats_requires_permission(client):
    r = client.get("/api/whatsapp/chats")
    assert r.status_code == 403  # whatsapp.read = ask


def test_whatsapp_chats_when_disabled(client, monkeypatch):
    from services import permissions
    from routes import whatsapp as wa_routes
    permissions.set_mode("whatsapp.read", "enabled")

    def boom(*a, **k):
        raise wa_routes.whatsapp_agent.WhatsAppUnavailableError("WhatsApp is disabled.")
    monkeypatch.setattr(wa_routes.whatsapp_agent, "get_chats", boom)

    r = client.get("/api/whatsapp/chats")
    assert r.status_code == 503
    assert "disabled" in r.json()["detail"].lower()


def test_whatsapp_draft_requires_permission(client, monkeypatch, tmp_path):
    from services import permissions
    from routes import whatsapp as wa_routes
    permissions.set_mode("whatsapp.read", "enabled")
    monkeypatch.setattr(wa_routes.whatsapp_agent, "DRAFTS_FILE", tmp_path / "wa.json")

    r = client.post("/api/whatsapp/draft", json={"phone": "919876543210", "message": "hi"})
    assert r.status_code == 200
    assert r.json()["preview"]["phone"] == "919876543210"


def test_whatsapp_send_requires_permission(client, monkeypatch, tmp_path):
    """whatsapp.send stays 'ask' → send must 403 without a grant."""
    from services import permissions
    from routes import whatsapp as wa_routes
    permissions.set_mode("whatsapp.read", "enabled")
    permissions.set_mode("whatsapp.send", "ask")
    monkeypatch.setattr(wa_routes.whatsapp_agent, "DRAFTS_FILE", tmp_path / "wa.json")

    r = client.post("/api/whatsapp/draft", json={"phone": "919876543210", "message": "hi"})
    draft_id = r.json()["draft_id"]
    r = client.post("/api/whatsapp/send", json={"draft_id": draft_id})
    assert r.status_code == 403


def test_whatsapp_send_with_approval(client, monkeypatch, tmp_path):
    """One-time approval → send succeeds (driver send faked)."""
    from services import permissions
    from routes import whatsapp as wa_routes
    permissions.set_mode("whatsapp.read", "enabled")
    monkeypatch.setattr(wa_routes.whatsapp_agent, "DRAFTS_FILE", tmp_path / "wa.json")

    sent = {}
    monkeypatch.setattr(wa_routes.whatsapp_agent, "send_draft", lambda did: sent.update(draft_id=did) or {
        "draft_id": did, "phone": "919876543210", "sent_at": int(time.time())})

    r = client.post("/api/whatsapp/draft", json={"phone": "919876543210", "message": "hi"})
    draft_id = r.json()["draft_id"]
    r = client.post("/api/permissions/approve", json={"capability": "whatsapp.send", "seconds": 120})
    assert r.status_code == 200
    r = client.post("/api/whatsapp/send", json={"draft_id": draft_id})
    assert r.status_code == 200
    assert sent["draft_id"] == draft_id


def test_whatsapp_cancel_no_permission_needed(client, monkeypatch, tmp_path):
    from routes import whatsapp as wa_routes
    monkeypatch.setattr(wa_routes.whatsapp_agent, "DRAFTS_FILE", tmp_path / "wa.json")
    r = client.post("/api/whatsapp/cancel", json={"draft_id": "nope"})
    assert r.status_code == 200
    assert r.json()["status"] == "not_found"
