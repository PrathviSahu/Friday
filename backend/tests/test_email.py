"""Tests for the Email Agent (service + routes).

IMAP/SMTP are faked — no real network, no credentials needed.
"""

import email
import email.utils
import json
import time

import pytest


# ── Fixtures / fakes ─────────────────────────────────────────────────────

def sample_raw(from_, subject, body, sender="Rahul <rahul@example.com>"):
    msg = email.message.EmailMessage()
    msg["From"] = sender
    msg["To"] = "prem@example.com"
    msg["Subject"] = subject
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg.set_content(body)
    return msg.as_bytes()


class FakeIMAP:
    """Minimal imaplib-compatible fake: search + BODY.PEEK fetch."""

    def __init__(self, messages):
        self.messages = messages
        self.select_called = False
        self.logged_out = False

    def select(self, mailbox="INBOX", readonly=False, *args, **kwargs):
        self.select_called = True
        self.readonly = readonly
        return ("OK", [b"1"])

    def search(self, *args):
        n = len(self.messages)
        if n == 0:
            return ("OK", [b""])
        return ("OK", [b" ".join(str(i + 1).encode() for i in range(n))])

    def fetch(self, num, *args):
        idx = int(num) - 1
        return ("OK", [(num, self.messages[idx])])

    def logout(self):
        self.logged_out = True
        return ("BYE", [])


@pytest.fixture(autouse=True)
def _configure_email(monkeypatch):
    monkeypatch.setenv("FRIDAY_EMAIL_HOST", "imap.test")
    monkeypatch.setenv("FRIDAY_EMAIL_USER", "prem@test.com")
    monkeypatch.setenv("FRIDAY_EMAIL_PASS", "app-password")


# ── Service: reading ─────────────────────────────────────────────────────

def test_get_unread_parses_messages(monkeypatch):
    from services import email_agent
    raw = sample_raw("rahul@example.com", "Running late?", "Hey, still on for 6?")
    monkeypatch.setattr(email_agent, "_connect_imap", lambda: FakeIMAP([raw]))

    items = email_agent.get_unread(limit=5)
    assert len(items) == 1
    m = items[0]
    assert "rahul@example.com" in m["from"]
    assert m["subject"] == "Running late?"
    assert "still on for 6" in m["snippet"]
    assert m["priority"] is False


def test_get_unread_marks_priority(monkeypatch):
    from services import email_agent
    raw = sample_raw("rahul@example.com", "URGENT: interview tomorrow", "Please confirm by EOD.")
    monkeypatch.setattr(email_agent, "_connect_imap", lambda: FakeIMAP([raw]))
    items = email_agent.get_unread(limit=5)
    assert items[0]["priority"] is True


def test_get_unread_empty_inbox(monkeypatch):
    from services import email_agent
    monkeypatch.setattr(email_agent, "_connect_imap", lambda: FakeIMAP([]))
    assert email_agent.get_unread(limit=5) == []


def test_summarize_inbox_aggregates(monkeypatch):
    from services import email_agent
    msgs = [
        sample_raw("a@x.com", "Hello", "one", sender="Alice <a@x.com>"),
        sample_raw("a@x.com", "Hello again", "two", sender="Alice <a@x.com>"),
        sample_raw("b@x.com", "URGENT deadline", "three", sender="Bob <b@x.com>"),
    ]
    monkeypatch.setattr(email_agent, "_connect_imap", lambda: FakeIMAP(msgs))
    s = email_agent.summarize_inbox(limit=10)
    assert s["unread_count"] == 3
    assert s["by_sender"][0]["name"] == "Alice"
    assert s["by_sender"][0]["count"] == 2
    assert s["priority"][0]["subject"] == "URGENT deadline"


# ── Service: draft → send (approval-first) ───────────────────────────────

def test_draft_requires_valid_email():
    from services import email_agent
    with pytest.raises(ValueError):
        email_agent.create_draft("not-an-email", "hi", "body")


def test_draft_expires(monkeypatch, tmp_path):
    from services import email_agent
    monkeypatch.setattr(email_agent, "DRAFTS_FILE", tmp_path / "drafts.json")
    d = email_agent.create_draft("a@b.com", "s", "b")
    assert email_agent.get_draft(d["id"]) is not None
    # Expire it manually
    drafts = json.loads((tmp_path / "drafts.json").read_text())
    drafts[d["id"]]["expires_at"] = time.time() - 1
    (tmp_path / "drafts.json").write_text(json.dumps(drafts))
    assert email_agent.get_draft(d["id"]) is None
    with pytest.raises(email_agent.EmailUnavailableError):
        email_agent.send_draft(d["id"])


def test_send_draft_uses_smtp(monkeypatch, tmp_path):
    from services import email_agent
    monkeypatch.setattr(email_agent, "DRAFTS_FILE", tmp_path / "drafts.json")
    sent = {}

    class FakeSMTP:
        def __init__(self, *a, **k): self.quit_called = False
        def starttls(self, context=None): pass
        def login(self, user, pw): pass
        def sendmail(self, from_, to, body):
            sent["to"] = to
            sent["body"] = body
        def quit(self): self.quit_called = True

    monkeypatch.setattr(email_agent.smtplib, "SMTP", FakeSMTP)

    d = email_agent.create_draft("rahul@example.com", "Quick note", "I'll reach in 20.")
    result = email_agent.send_draft(d["id"])
    assert result["to"] == "rahul@example.com"
    assert sent["to"] == ["rahul@example.com"]
    # Body is base64-encoded inside the MIME message — decode it
    decoded = email.message_from_string(sent["body"]).get_payload(decode=True).decode("utf-8", errors="replace")
    assert "I'll reach in 20" in decoded
    assert email_agent.get_draft(d["id"]) is None  # marked sent


# ── Routes ───────────────────────────────────────────────────────────────

def test_email_unread_requires_auth(remote_client):
    r = remote_client.get("/api/email/unread")
    assert r.status_code == 401


def test_email_read_permission_gate(client):
    """email.read defaults to 'ask' → 403 without approval/mode change."""
    r = client.get("/api/email/unread")
    assert r.status_code == 403


def test_email_unread_ok_when_permitted(client, monkeypatch):
    from services import permissions
    from routes import email as email_routes
    permissions.set_mode("email.read", "enabled")
    monkeypatch.setattr(email_routes.email_agent, "get_unread",
                        lambda limit=15: [{"from": "A <a@x.com>", "subject": "Hi", "priority": False}])
    r = client.get("/api/email/unread")
    assert r.status_code == 200
    assert len(r.json()["unread"]) == 1


def test_email_unconfigured_returns_503(client, monkeypatch):
    from services import permissions
    from routes import email as email_routes
    permissions.set_mode("email.read", "enabled")
    monkeypatch.setattr(email_routes.email_agent, "is_configured", lambda: False)
    monkeypatch.setattr(email_routes.email_agent, "get_unread",
                        lambda limit=15: (_ for _ in ()).throw(
                            email_routes.email_agent.EmailUnavailableError("not configured")))
    r = client.get("/api/email/unread")
    assert r.status_code == 503


def test_email_draft_and_send_flow(client, monkeypatch, tmp_path):
    """Full approval-first flow: draft (with email.read) → approve → send."""
    from services import permissions
    from routes import email as email_routes
    permissions.set_mode("email.read", "enabled")
    permissions.set_mode("email.send", "enabled")
    monkeypatch.setattr(email_routes.email_agent, "DRAFTS_FILE", tmp_path / "drafts.json")

    class FakeSMTP:
        def __init__(self, *a, **k): pass
        def starttls(self, context=None): pass
        def login(self, user, pw): pass
        def sendmail(self, from_, to, body): pass
        def quit(self): pass

    monkeypatch.setattr(email_routes.email_agent.smtplib, "SMTP", FakeSMTP)

    # Draft
    r = client.post("/api/email/draft", json={"to": "rahul@example.com", "subject": "Hi", "body": "See you soon"})
    assert r.status_code == 200
    draft_id = r.json()["draft_id"]
    assert r.json()["preview"]["to"] == "rahul@example.com"

    # Sending an unknown draft → 400
    r = client.post("/api/email/send", json={"draft_id": "nope"})
    assert r.status_code == 400

    # Sending the real draft (permission enabled for test)
    r = client.post("/api/email/send", json={"draft_id": draft_id})
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_email_send_requires_permission(client, monkeypatch, tmp_path):
    """email.send stays 'ask' → send must 403 without a grant."""
    from services import permissions
    from routes import email as email_routes
    permissions.set_mode("email.read", "enabled")
    permissions.set_mode("email.send", "ask")  # reset in case a prior test enabled it
    monkeypatch.setattr(email_routes.email_agent, "DRAFTS_FILE", tmp_path / "drafts.json")

    r = client.post("/api/email/draft", json={"to": "rahul@example.com", "subject": "Hi", "body": "x"})
    assert r.status_code == 200
    draft_id = r.json()["draft_id"]

    r = client.post("/api/email/send", json={"draft_id": draft_id})
    assert r.status_code == 403


def test_email_send_with_approval(client, monkeypatch, tmp_path):
    """Grant a one-time approval → send succeeds."""
    from services import permissions
    from routes import email as email_routes
    permissions.set_mode("email.read", "enabled")
    monkeypatch.setattr(email_routes.email_agent, "DRAFTS_FILE", tmp_path / "drafts.json")
    sent = {}

    class FakeSMTP:
        def __init__(self, *a, **k): pass
        def starttls(self, context=None): pass
        def login(self, user, pw): pass
        def sendmail(self, from_, to, body): sent["to"] = to
        def quit(self): pass

    monkeypatch.setattr(email_routes.email_agent.smtplib, "SMTP", FakeSMTP)

    r = client.post("/api/email/draft", json={"to": "rahul@example.com", "subject": "Hi", "body": "x"})
    draft_id = r.json()["draft_id"]

    # Approve once via the permission API
    r = client.post("/api/permissions/approve", json={"capability": "email.send", "seconds": 120})
    assert r.status_code == 200

    r = client.post("/api/email/send", json={"draft_id": draft_id})
    assert r.status_code == 200
    assert sent["to"] == ["rahul@example.com"]
