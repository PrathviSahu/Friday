"""services/meeting_agent.py — Meeting Assistant.

Pipeline:
  1. Audio (or pasted transcript) → Groq Whisper transcription (reuses the
     existing STT engine, free tier).
  2. Transcript → Groq LLM extraction of: title, summary, key points,
     decisions, and ACTION ITEMS (with optional owner).
  3. Persisted to SQLite (`meetings.db`) AND mirrored into the Knowledge OS
     (`kb_notes` type=meeting) so past meetings are searchable everywhere.
  4. Action items can be pushed into Todos with one call.

Uses the same friday_brain.db as knowledge.py so the knowledge-mirror
write is atomic with the meeting record.
"""

import json
import os
import sqlite3
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from services.knowledge import add_note as kb_add_note
from services.brain import _get_groq_client

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "meetings.db"
_lock = threading.Lock()

MAX_UPLOAD_BYTES = int(os.getenv("FRIDAY_MEETING_MAX_UPLOAD", str(25 * 1024 * 1024)))  # 25 MB (Groq cap)

_EXTRACT_SYSTEM_PROMPT = (
    "You are F.R.I.D.A.Y.'s meeting intelligence engine. Extract structure from "
    "the meeting transcript below.\n"
    "Reply with ONLY a single JSON object:\n"
    '{"title": "<short title>", "summary": "<2-3 sentence summary>", '
    '"key_points": ["<bullet>", ...], "decisions": ["<decision>", ...], '
    '"action_items": [{"text": "<action>", "owner": "<name or empty>"}, ...]}\n'
    "If an action item has no clear owner, use an empty string. "
    "Keep every field concise. No commentary outside the JSON."
)


class MeetingUnavailableError(RuntimeError):
    """Raised when transcription/extraction fails."""


def init_meetings_db():
    with _lock, _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                id          TEXT PRIMARY KEY,
                title       TEXT NOT NULL,
                date        TEXT NOT NULL,
                duration_s  INTEGER DEFAULT 0,
                summary     TEXT NOT NULL,
                key_points  TEXT DEFAULT '[]',
                decisions   TEXT DEFAULT '[]',
                action_items TEXT DEFAULT '[]',
                transcript  TEXT DEFAULT '',
                source      TEXT DEFAULT 'audio',
                created_at  REAL NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_meetings_date ON meetings(date)")
        conn.commit()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


# ── Transcription (reuses services/stt.py — Groq Whisper free tier) ──────

def transcribe_audio(audio_bytes: bytes, filename: str, mime_type: str) -> str:
    """Transcribe meeting audio via the shared STT engine."""
    from services.stt import transcribe_audio as stt_transcribe

    if not audio_bytes:
        raise MeetingUnavailableError("No audio received.")
    try:
        result = stt_transcribe(audio_bytes, filename, mime_type)
    except Exception as exc:
        raise MeetingUnavailableError(f"Transcription failed: {exc}") from exc
    transcript = (result.get("transcript") or "").strip()
    if not transcript:
        raise MeetingUnavailableError("Transcription returned no text — is the audio speech?")
    return transcript


# ── LLM extraction (Groq, with Gemini failover via the shared brain path) ─

def _extract_json(text: str) -> dict:
    if not text:
        return {}
    import re
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        candidate = brace.group(0) if brace else None
    if not candidate:
        return {}
    try:
        return json.loads(candidate)
    except Exception:
        return {}


def extract_meeting_structure(transcript: str) -> dict:
    """Run the transcript through the LLM and return structured JSON."""
    client = _get_groq_client()
    if client is None:
        raise MeetingUnavailableError("GROQ_API_KEY is not configured — can't extract structure.")

    try:
        completion = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=[
                {"role": "system", "content": _EXTRACT_SYSTEM_PROMPT},
                {"role": "user", "content": f"Meeting transcript:\n\n{transcript[:12000]}"},
            ],
            temperature=0.2,
        )
        raw = (getattr(completion.choices[0].message, "content", "") or "").strip()
    except Exception as exc:
        raise MeetingUnavailableError(f"LLM extraction failed: {exc}") from exc

    data = _extract_json(raw)
    if not data:
        raise MeetingUnavailableError("LLM returned no structured data.")

    return {
        "title": str(data.get("title") or "Untitled meeting")[:150],
        "summary": str(data.get("summary") or "")[:1000],
        "key_points": [str(k)[:300] for k in (data.get("key_points") or [])][:15],
        "decisions": [str(d)[:300] for d in (data.get("decisions") or [])][:15],
        "action_items": [
            {
                "text": str(a.get("text") or "")[:300],
                "owner": str(a.get("owner") or "")[:80],
            }
            for a in (data.get("action_items") or []) if (a.get("text") or "").strip()
        ][:20],
    }


# ── Persistence ──────────────────────────────────────────────────────────

def save_meeting(transcript: str, structure: dict, source: str = "text",
                 duration_s: int = 0) -> dict:
    """Persist a processed meeting + mirror it into the Knowledge OS."""
    meeting = {
        "id": uuid.uuid4().hex,
        "title": structure["title"],
        "date": datetime.now().astimezone().isoformat(),
        "duration_s": int(duration_s or 0),
        "summary": structure["summary"],
        "key_points": structure["key_points"],
        "decisions": structure["decisions"],
        "action_items": structure["action_items"],
        "transcript": transcript,
        "source": source,
        "created_at": time.time(),
    }
    with _lock, _connect() as conn:
        conn.execute(
            """INSERT INTO meetings (id, title, date, duration_s, summary,
               key_points, decisions, action_items, transcript, source, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                meeting["id"], meeting["title"], meeting["date"], meeting["duration_s"],
                meeting["summary"], json.dumps(meeting["key_points"]),
                json.dumps(meeting["decisions"]), json.dumps(meeting["action_items"]),
                meeting["transcript"], meeting["source"], meeting["created_at"],
            ),
        )
        conn.commit()

    # Mirror into Knowledge OS (searchable via "second brain")
    try:
        kb_add_note(
            title=meeting["title"],
            content=meeting["summary"],
            note_type="meeting",
            tags=["meeting"],
        )
    except Exception:
        pass  # the mirror must never break the meeting save

    return meeting


def process_meeting(transcript: str, source: str = "text", duration_s: int = 0) -> dict:
    """Full pipeline: extract structure → persist → return the meeting."""
    structure = extract_meeting_structure(transcript)
    return save_meeting(transcript, structure, source=source, duration_s=duration_s)


def process_meeting_audio(audio_bytes: bytes, filename: str, mime_type: str) -> dict:
    """Full pipeline for an audio upload: transcribe → extract → persist."""
    transcript = transcribe_audio(audio_bytes, filename, mime_type)
    return process_meeting(transcript, source="audio")


# ── Queries ──────────────────────────────────────────────────────────────

def _row_to_meeting(row: sqlite3.Row) -> dict:
    def _loads(v, default):
        try:
            return json.loads(v) if v else default
        except Exception:
            return default

    return {
        "id": row["id"],
        "title": row["title"],
        "date": row["date"],
        "duration_s": row["duration_s"],
        "summary": row["summary"],
        "key_points": _loads(row["key_points"], []),
        "decisions": _loads(row["decisions"], []),
        "action_items": _loads(row["action_items"], []),
        "transcript": row["transcript"],
        "source": row["source"],
    }


def list_meetings(limit: int = 20) -> list:
    with _lock, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM meetings ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_meeting(r) for r in rows]


def get_meeting(meeting_id: str) -> dict | None:
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)).fetchone()
    return _row_to_meeting(row) if row else None


def search_meetings(query: str, limit: int = 10) -> list:
    with _lock, _connect() as conn:
        like = f"%{query}%"
        rows = conn.execute(
            """SELECT * FROM meetings
               WHERE title LIKE ? OR summary LIKE ? OR transcript LIKE ?
               ORDER BY created_at DESC LIMIT ?""",
            (like, like, like, limit),
        ).fetchall()
    return [_row_to_meeting(r) for r in rows]


def get_action_items(include_done: bool = False) -> list:
    """All action items across meetings (most recent meetings first)."""
    out = []
    for m in list_meetings(limit=50):
        for item in m["action_items"]:
            out.append({
                "meeting_id": m["id"],
                "meeting_title": m["title"],
                "meeting_date": m["date"],
                "text": item.get("text", ""),
                "owner": item.get("owner", ""),
            })
    return out


def push_action_items_to_todos(meeting_id: str) -> dict:
    """Add a meeting's action items to the todo list (tasks.write)."""
    from services.todos import add_todo

    meeting = get_meeting(meeting_id)
    if not meeting:
        raise MeetingUnavailableError("Meeting not found.")
    added = []
    for item in meeting["action_items"]:
        text = item.get("text", "").strip()
        if not text:
            continue
        owner = item.get("owner", "").strip()
        todo_text = f"[{owner}] {text}" if owner else text
        add_todo(todo_text, priority="high")
        added.append(todo_text)
    return {"meeting_id": meeting_id, "added": added}


# ── Friendly formatting for the AI brain ─────────────────────────────────

def format_meeting_for_speech(meeting: dict, with_action_items: bool = True) -> str:
    if not meeting:
        return "I don't have any meetings recorded yet."
    parts = [f"Meeting: {meeting['title']}. {meeting['summary']}"]
    if with_action_items and meeting["action_items"]:
        items = "; ".join(f"{a.get('text', '')}" for a in meeting["action_items"][:4])
        parts.append(f"Action items: {items}.")
    return " ".join(parts)


# Ensure the table exists on first import (matches knowledge.py's pattern).
init_meetings_db()
