"""Tests for the Phase 2.5 Cross-Device Presence engine.

Acceptance per next_phase_2_architecture.md §7:
  * an 'ask' capability (email send draft) can be approved from a device and
    its deferred action executes (Telegram inline buttons / PWA push)
  * presence devices can only RESOLVE approvals — never mint capabilities

No live Telegram bot, push service, or SMTP in tests: senders are stubbed,
the pending store and outbox are module state reset per test.
"""

import json
import time

import pytest

from services import presence
from services import permissions


@pytest.fixture(autouse=True)
def _reset_presence_state():
    presence._PENDING.clear()
    presence._OUTBOX.clear()
    presence.TELEGRAM_SENDER = None
    with presence._db() as conn:
        conn.execute("DELETE FROM presence_tokens")
        conn.commit()
    permissions.revoke_approval("email.send")
    permissions.revoke_approval("whatsapp.send")
    yield
    presence.TELEGRAM_SENDER = None


# ── Device registry ───────────────────────────────────────────────────────────

def test_register_validation():
    assert presence.register_device("carrier-pigeon", "abcd")["status"] == "error"
    assert presence.register_device("pwa", "x")["status"] == "error"
    ok = presence.register_device("pwa", '{"endpoint":"https://push.example/x"}', "Prem phone")
    assert ok["status"] == "ok" and ok["devices"] == 1


def test_register_dedupes_by_token():
    presence.register_device("telegram", "123456", "old label")
    presence.register_device("telegram", "123456", "Prem (Telegram)")
    devices = presence.list_devices()
    assert len(devices) == 1 and devices[0]["label"] == "Prem (Telegram)"


def test_remove_device_by_id_and_token():
    presence.register_device("pwa", '{"endpoint":"https://push.example/a"}', "")
    presence.register_device("telegram", "9988", "")
    devices = presence.list_devices()  # ordered by id DESC — most recent first
    pwa = next(d for d in devices if d["device_kind"] == "pwa")
    assert presence.remove_device(device_id=pwa["id"])["status"] == "ok"
    assert presence.remove_device(token="9988")["status"] == "ok"
    assert presence.remove_device(token="9988")["status"] == "error"
    assert presence.list_devices() == []


# ── Approval lifecycle ────────────────────────────────────────────────────────

def test_create_approval_unknown_capability_rejected():
    assert presence.create_approval("laser.control", "x")["status"] == "error"


def test_create_approval_lists_pending_and_expires():
    res = presence.create_approval("email.send", "Send email to rohan@x.com", push=False)
    assert res["status"] == "ok" and res["expires_in"] == presence.PENDING_TTL_SECONDS
    pending = presence.list_pending()
    assert pending[0]["capability"] == "email.send"
    assert pending[0]["description"] == "Send email to rohan@x.com"

    # Force expiry → pruned & unresolvable.
    presence._PENDING[res["approval_token"]]["expires_at"] = time.time() - 1
    assert presence.list_pending() == []
    assert presence.resolve_decision(res["approval_token"], "approve")["status"] == "error"


def test_approve_grants_only_its_capability():
    res = presence.create_approval("email.send", "send?", push=False)
    out = presence.resolve_decision(res["approval_token"], "approve")
    assert out["status"] == "ok" and out["capability"] == "email.send"
    assert permissions.has_valid_approval("email.send")          # THIS cap granted…
    assert not permissions.has_valid_approval("whatsapp.send")   # …and nothing else


def test_approve_executes_deferred_action(monkeypatch):
    sent = []
    import services.email_agent as em
    monkeypatch.setattr(em, "send_draft", lambda draft_id: sent.append(draft_id)
                        or {"message": "Sent to rohan@x.com"})
    res = presence.create_approval(
        "email.send", "Send email to rohan@x.com",
        action={"kind": "email_send_draft", "draft_id": "draft-123"}, push=False)
    out = presence.resolve_decision(res["approval_token"], "approve")
    assert out["executed"] is True and "Sent to rohan" in out["message"]
    assert sent == ["draft-123"]


def test_deny_consumes_without_granting():
    res = presence.create_approval("whatsapp.send", "send wa?", push=False)
    out = presence.resolve_decision(res["approval_token"], "deny")
    assert out["status"] == "ok" and out["decision"] == "deny"
    assert not permissions.has_valid_approval("whatsapp.send")
    # Consumed: a second decision on the same token fails.
    assert presence.resolve_decision(res["approval_token"], "approve")["status"] == "error"


def test_invalid_decision_does_not_consume():
    res = presence.create_approval("email.send", "send?", push=False)
    bad = presence.resolve_decision(res["approval_token"], "maybe")
    assert bad["status"] == "error" and "approve" in bad["message"]
    assert presence.resolve_decision(res["approval_token"], "approve")["status"] == "ok"


def test_unknown_token_rejected():
    assert presence.resolve_decision("nope-token", "approve")["status"] == "error"


# ── Push delivery ─────────────────────────────────────────────────────────────

def test_telegram_push_uses_live_sender():
    presence.register_device("telegram", "424242", "Prem")
    calls = []
    presence.TELEGRAM_SENDER = lambda chat_id, record: calls.append((chat_id, record))
    res = presence.create_approval("email.send", "Send email?", push=True)
    assert calls and calls[0][0] == "424242"
    assert calls[0][1]["approval_token"] == res["approval_token"]
    assert presence.get_outbox()[-1]["sent"] is True


def test_telegram_push_without_bot_is_graceful():
    presence.register_device("telegram", "424242", "Prem")
    presence.create_approval("email.send", "Send email?", push=True)
    row = presence.get_outbox()[-1]
    assert row["device_kind"] == "telegram" and row["sent"] is False
    assert "bot not running" in row["reason"]


def test_pwa_push_graceful_without_vapid_keys(monkeypatch):
    monkeypatch.delenv("VAPID_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("VAPID_PRIVATE_KEY", raising=False)
    presence.register_device("pwa", json.dumps({"endpoint": "https://push.example/1"}), "")
    presence.create_approval("email.send", "Send email?", push=True)
    row = presence.get_outbox()[-1]
    assert row["device_kind"] == "pwa" and row["sent"] is False
    assert "VAPID" in row["reason"]


def test_pwa_invalid_subscription_graceful():
    presence.register_device("pwa", "not-json", "")
    presence.create_approval("email.send", "Send email?", push=True)
    assert presence.get_outbox()[-1]["reason"] == "invalid subscription"


def test_vapid_jwt_builds_with_real_keys():
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    import base64, os
    key = ec.generate_private_key(ec.SECP256R1())
    priv = key.private_numbers().private_value.to_bytes(32, "big")
    pub_xy = key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    os.environ["VAPID_PRIVATE_KEY"] = base64.urlsafe_b64encode(priv).rstrip(b"=").decode()
    os.environ["VAPID_PUBLIC_KEY"] = base64.urlsafe_b64encode(pub_xy).rstrip(b"=").decode()
    try:
        pair = presence._vapid_jwt("https://push.example/sub/abc")
        assert pair is not None
        jwt, public = pair
        assert jwt.count(".") == 2 and public
    finally:
        del os.environ["VAPID_PRIVATE_KEY"], os.environ["VAPID_PUBLIC_KEY"]


# ── Telegram callback parsing (bot module) ────────────────────────────────────

@pytest.mark.skipif(__import__("services.telegram_bot", fromlist=["_PTB_AVAILABLE"])._PTB_AVAILABLE is False,
                    reason="python-telegram-bot not installed")
@pytest.mark.parametrize("data,expected", [
    ("pr:abc123:approve", ("abc123", "approve")),
    ("pr:xyz:deny", ("xyz", "deny")),
    ("pr:xyz:maybe", None),
    ("weather:refresh", None),
    ("", None), (None, None),
])
def test_telegram_callback_parsing(data, expected):
    from services.telegram_bot import parse_presence_callback
    assert parse_presence_callback(data) == expected


# ── API round-trip ────────────────────────────────────────────────────────────

def test_api_full_approval_journey(client, monkeypatch):
    sent = []
    import services.email_agent as em
    monkeypatch.setattr(em, "send_draft", lambda did: sent.append(did) or {"message": "Sent."})

    r = client.post("/api/presence/register", json={
        "device_kind": "telegram", "token": "7777", "label": "Prem phone"})
    assert r.status_code == 200
    assert client.get("/api/presence/devices").json()["devices"][0]["token"] == "7777"

    ask = client.post("/api/presence/ask", json={
        "capability": "email.send", "description": "Send email to rohan@x.com",
        "action": {"kind": "email_send_draft", "draft_id": "d-1"}})
    assert ask.status_code == 200
    token = ask.json()["approval_token"]

    pending = client.get("/api/presence/pending").json()["pending"]
    assert any(p["approval_token"] == token for p in pending)

    ok = client.post("/api/presence/decision",
                     json={"approval_token": token, "decision": "approve"})
    assert ok.status_code == 200
    body = ok.json()
    assert body["decision"] == "approve" and body["executed"] is True
    assert sent == ["d-1"] and permissions.has_valid_approval("email.send")

    # Unknown token → structured error, still 200 (device UX pattern).
    lost = client.post("/api/presence/decision",
                       json={"approval_token": token, "decision": "approve"})
    assert lost.status_code == 200 and lost.json()["status"] == "error"


def test_api_register_validation_and_device_delete(client):
    bad = client.post("/api/presence/register",
                      json={"device_kind": "fax", "token": "abcd"})
    assert bad.status_code == 400
    client.post("/api/presence/register", json={"device_kind": "pwa", "token": "tok-1234"})
    device_id = client.get("/api/presence/devices").json()["devices"][0]["id"]
    assert client.delete(f"/api/presence/devices/{device_id}").status_code == 200
    assert client.delete(f"/api/presence/devices/{device_id}").status_code == 404


def test_api_vapid_key_graceful(client, monkeypatch):
    monkeypatch.delenv("VAPID_PUBLIC_KEY", raising=False)
    assert client.get("/api/presence/vapid-key").json()["public_key"] == ""


def test_api_remote_blocked(remote_client):
    for method, path, body in [
        ("post", "/api/presence/register", {"device_kind": "pwa", "token": "abcd"}),
        ("get", "/api/presence/devices", None),
        ("get", "/api/presence/pending", None),
        ("post", "/api/presence/ask", {"capability": "email.send"}),
        ("post", "/api/presence/decision", {"approval_token": "x", "decision": "approve"}),
        ("get", "/api/presence/vapid-key", None),
    ]:
        resp = getattr(remote_client, method)(path, json=body) if body else \
               getattr(remote_client, method)(path)
        assert resp.status_code == 401, f"{method} {path}"
    assert remote_client.delete("/api/presence/devices/1").status_code == 401


# ── Email draft integration (the acceptance flow) ────────────────────────────

def test_email_draft_pushes_presence_prompt_in_ask_mode(client, monkeypatch):
    import services.email_agent as em
    monkeypatch.setattr(em, "create_draft", lambda to, subject, body: {
        "id": "draft-9", "to": to, "subject": subject, "body": body,
        "created_at": time.time(), "expires_at": time.time() + 900, "status": "pending"})
    # The draft endpoint itself requires email.read approval…
    permissions.grant_approval("email.read")
    # …and email.send must be in 'ask' mode for the presence prompt to fire.
    permissions.set_mode("email.send", "ask")
    r = client.post("/api/email/draft",
                    json={"to": "rohan@x.com", "subject": "Lunch?", "body": "12pm?"})
    assert r.status_code == 200 and r.json()["presence_prompt_sent"] is True
    pending = presence.list_pending()
    assert pending and pending[0]["capability"] == "email.send"
    assert "rohan@x.com" in pending[0]["description"]
