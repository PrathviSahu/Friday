"""services/email_agent.py — Email Agent (Gmail / Outlook via IMAP + SMTP).

Read-only by default: nothing is ever sent without the two-step flow:

  1. POST /api/email/draft   → the message is stored SERVER-SIDE as a pending
     draft (with a TTL) and a preview is returned to the user.
  2. POST /api/email/send    → only accepts a draft_id that exists, is fresh,
     and for which the user granted a one-time `email.send` approval.

Sending an email that was never previewed server-side is therefore
impossible, even if a client is misbehaving.

Configuration (env): FRIDAY_EMAIL_HOST / FRIDAY_EMAIL_IMAP_PORT /
FRIDAY_EMAIL_USER / FRIDAY_EMAIL_PASS (+ optional FRIDAY_EMAIL_SMTP_HOST /
FRIDAY_EMAIL_SMTP_PORT). Gmail & Outlook both work with app passwords.
"""

import email
import imaplib
import json
import os
import re
import smtplib
import ssl
import time
import uuid
from datetime import datetime
from email.header import decode_header, make_header
from email.mime.text import MIMEText
from email.utils import formataddr, parsedate_to_datetime
from pathlib import Path

DRAFTS_FILE = Path(__file__).resolve().parent.parent / "data" / "email_drafts.json"
DRAFT_TTL_SECONDS = int(os.getenv("FRIDAY_EMAIL_DRAFT_TTL", "900"))  # 15 min

PRIORITY_KEYWORDS = re.compile(
    r"\b(urgent|asap|immediately|deadline|due today|interview|offer|invoice|"
    r"payment|overdue|final notice|action required|important)\b",
    re.IGNORECASE,
)

# Common senders / subjects that are never "urgent" — pure noise.
NOISE_KEYWORDS = re.compile(
    r"\b(unsubscribe|newsletter|no-reply|noreply|do not reply|promotions|spam)\b",
    re.IGNORECASE,
)


class EmailUnavailableError(RuntimeError):
    """Raised when email is not configured or the provider is unreachable."""


# ── Config ────────────────────────────────────────────────────────────────

def is_configured() -> bool:
    return bool(
        os.getenv("FRIDAY_EMAIL_HOST")
        and os.getenv("FRIDAY_EMAIL_USER")
        and os.getenv("FRIDAY_EMAIL_PASS")
    )


def _imap_host() -> str:
    return os.getenv("FRIDAY_EMAIL_HOST", "imap.gmail.com")


def _imap_port() -> int:
    return int(os.getenv("FRIDAY_EMAIL_IMAP_PORT", "993"))


def _smtp_host() -> str:
    return os.getenv("FRIDAY_EMAIL_SMTP_HOST") or _imap_host()


def _smtp_port() -> int:
    return int(os.getenv("FRIDAY_EMAIL_SMTP_PORT", "587"))


def _user() -> str:
    return os.getenv("FRIDAY_EMAIL_USER", "")


def _password() -> str:
    return os.getenv("FRIDAY_EMAIL_PASS", "")


def _ensure_configured() -> None:
    if not is_configured():
        raise EmailUnavailableError(
            "Email is not configured. Add FRIDAY_EMAIL_HOST, FRIDAY_EMAIL_USER "
            "and FRIDAY_EMAIL_PASS to backend/.env (Gmail/Outlook app password)."
        )


def _connect_imap(timeout: int = 10):
    """Open an IMAP4_SSL connection with explicit timeout."""
    _ensure_configured()
    conn = imaplib.IMAP4_SSL(_imap_host(), _imap_port(), timeout=timeout)
    conn.login(_user(), _password())
    return conn


def test_imap_connection(timeout: int = 10) -> tuple[bool, str]:
    """Test IMAP connection and authentication with an explicit timeout without fetching messages."""
    if not is_configured():
        return False, "Email credentials not configured."
    try:
        conn = imaplib.IMAP4_SSL(_imap_host(), _imap_port(), timeout=timeout)
        try:
            conn.login(_user(), _password())
            return True, "IMAP connection and authentication succeeded."
        except imaplib.IMAP4.error as auth_err:
            return False, f"IMAP authentication failed: {auth_err}"
        finally:
            try:
                conn.logout()
            except Exception:
                pass
    except Exception as net_err:
        return False, f"IMAP connection failed: {net_err}"


def test_smtp_connection(timeout: int = 10) -> tuple[bool, str]:
    """Test SMTP connection, STARTTLS, and authentication with an explicit timeout without sending."""
    if not is_configured():
        return False, "Email credentials not configured."
    try:
        server = smtplib.SMTP(_smtp_host(), _smtp_port(), timeout=timeout)
        try:
            server.starttls(context=ssl.create_default_context())
            server.login(_user(), _password())
            return True, "SMTP connection, STARTTLS, and authentication succeeded."
        except smtplib.SMTPAuthenticationError as auth_err:
            return False, f"SMTP authentication failed: {auth_err}"
        except Exception as smtp_err:
            return False, f"SMTP error: {smtp_err}"
        finally:
            try:
                server.quit()
            except Exception:
                pass
    except Exception as net_err:
        return False, f"SMTP connection failed: {net_err}"


def _decode_header_value(value) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return str(value)


def _body_snippet(msg, limit: int = 240) -> str:
    """Return a plain-text snippet from a parsed email message."""
    try:
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype == "text/plain" and not part.get_filename():
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        return payload.decode(charset, errors="replace").strip()[:limit]
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace").strip()[:limit]
    except Exception:
        pass
    return ""


def _parse_email(raw: bytes) -> dict:
    """Convert raw RFC822 bytes into a clean email dict."""
    msg = email.message_from_bytes(raw)
    sender = _decode_header_value(msg.get("From", ""))
    subject = _decode_header_value(msg.get("Subject", "")) or "(no subject)"
    date_raw = msg.get("Date", "")
    try:
        dt = parsedate_to_datetime(date_raw)
        ts = int(dt.timestamp())
    except Exception:
        ts = 0

    snippet = _body_snippet(msg)
    from_name = sender.split("<")[0].strip().strip('"') or sender
    priority = bool(PRIORITY_KEYWORDS.search(subject + " " + snippet)) and not NOISE_KEYWORDS.search(sender + " " + subject)

    return {
        "from": sender,
        "from_name": from_name[:60],
        "subject": subject[:120],
        "date": ts,
        "snippet": snippet,
        "priority": priority,
    }


def _fetch_recent_unseen(conn, limit: int = 15) -> list:
    """Fetch the most recent `limit` unread messages without marking them seen."""
    typ, data = conn.search(None, "UNSEEN")
    if typ != "OK":
        return []
    ids = (data[0] or b"").split()
    ids = ids[-limit:]
    results = []
    for num in ids:
        try:
            typ, msg_data = conn.fetch(num, "(BODY.PEEK[])")
            if typ != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
                continue
            raw = msg_data[0][1]
            results.append(_parse_email(raw))
        except Exception:
            continue
    return results


# ── Public read API ───────────────────────────────────────────────────────

def get_unread(limit: int = 15) -> list:
    """Return the most recent unread emails (does NOT mark them read)."""
    _ensure_configured()
    conn = _connect_imap()
    try:
        conn.select("INBOX")
        return _fetch_recent_unseen(conn, limit=limit)
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def search_emails(query: str, limit: int = 10) -> list:
    """Search subject/from for `query` across the inbox."""
    _ensure_configured()
    conn = _connect_imap()
    try:
        conn.select("INBOX")
        crit = f'(OR (SUBJECT "{query}") (FROM "{query}"))'
        typ, data = conn.search(None, crit)
        if typ != "OK":
            return []
        ids = (data[0] or b"").split()[-limit:]
        results = []
        for num in ids:
            try:
                typ, msg_data = conn.fetch(num, "(BODY.PEEK[])")
                if typ == "OK" and isinstance(msg_data[0], tuple):
                    results.append(_parse_email(msg_data[0][1]))
            except Exception:
                continue
        return results
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def summarize_inbox(limit: int = 20) -> dict:
    """Aggregate the inbox: unread count, top senders, priority items."""
    _ensure_configured()
    unread = get_unread(limit=limit)
    by_sender: dict = {}
    for item in unread:
        name = item["from_name"]
        by_sender[name] = by_sender.get(name, 0) + 1
    top_senders = sorted(by_sender.items(), key=lambda kv: -kv[1])[:5]
    priority = [m for m in unread if m["priority"]][:5]
    return {
        "unread_count": len(unread),
        "by_sender": [{"name": name, "count": count} for name, count in top_senders],
        "priority": priority,
    }


# ── Draft store (server-side, TTL'd) ─────────────────────────────────────

def _load_drafts() -> dict:
    if not DRAFTS_FILE.exists():
        return {}
    try:
        return json.loads(DRAFTS_FILE.read_text())
    except Exception:
        return {}


def _save_drafts(drafts: dict) -> None:
    DRAFTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    DRAFTS_FILE.write_text(json.dumps(drafts, indent=2))


def create_draft(to: str, subject: str, body: str) -> dict:
    """Persist a pending draft and return it (with id + expiry)."""
    to = (to or "").strip()
    if not to or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", to):
        raise ValueError("A valid recipient email address is required.")

    drafts = _load_drafts()
    now = time.time()
    # Purge expired drafts opportunistically
    drafts = {k: v for k, v in drafts.items() if v.get("expires_at", 0) > now}

    draft = {
        "id": uuid.uuid4().hex,
        "to": to,
        "subject": (subject or "").strip()[:150],
        "body": (body or "").strip(),
        "created_at": now,
        "expires_at": now + DRAFT_TTL_SECONDS,
        "status": "pending",
    }
    drafts[draft["id"]] = draft
    _save_drafts(drafts)
    return draft


def get_draft(draft_id: str) -> dict | None:
    draft = _load_drafts().get(draft_id)
    if not draft:
        return None
    if draft.get("expires_at", 0) < time.time() or draft.get("status") != "pending":
        return None
    return draft


def send_draft(draft_id: str) -> dict:
    """Send a previously created draft via SMTP and mark it sent."""
    draft = get_draft(draft_id)
    if not draft:
        raise EmailUnavailableError("Draft not found or expired — please preview the email again.")

    _ensure_configured()
    msg = MIMEText(draft["body"], "plain", "utf-8")
    msg["Subject"] = draft["subject"] or "(no subject)"
    msg["From"] = formataddr(("F.R.I.D.A.Y.", _user()))
    msg["To"] = draft["to"]

    server = smtplib.SMTP(_smtp_host(), _smtp_port(), timeout=25)
    try:
        server.starttls(context=ssl.create_default_context())
        server.login(_user(), _password())
        server.sendmail(_user(), [draft["to"]], msg.as_string())
    finally:
        try:
            server.quit()
        except Exception:
            pass

    drafts = _load_drafts()
    if draft_id in drafts:
        drafts[draft_id]["status"] = "sent"
        drafts[draft_id]["sent_at"] = time.time()
        _save_drafts(drafts)

    return {
        "draft_id": draft_id,
        "to": draft["to"],
        "subject": draft["subject"],
        "sent_at": int(time.time()),
    }


def cancel_draft(draft_id: str) -> bool:
    drafts = _load_drafts()
    if draft_id in drafts:
        drafts.pop(draft_id, None)
        _save_drafts(drafts)
        return True
    return False


# ── Friendly formatting for the AI brain ─────────────────────────────────

def format_email_preview(draft: dict) -> str:
    return (
        f"To: {draft['to']} | Subject: {draft['subject'] or '(none)'} | "
        f"Body: {draft['body'][:200]}"
    )
