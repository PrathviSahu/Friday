"""FRIDAY Adaptive Self-Learning, Semantic Memory & Job Intelligence Engine.

Single unified database: backend/data/friday_brain.db

Tables:
  - memories          → Persistent personal facts & preferences (replaces friday_memory.db)
  - conversation_history → Short-term chat context (last 20 turns)
  - user_action_habits   → High-value habit tracking (trading, music, weather)
  - user_corrections     → Soft penalty corrections from voice phrases
  - job_profile          → Prem's career profile (role, skills, experience)
  - resume_data          → Extracted resume sections for job matching
  - job_applications     → Jobs FRIDAY found + application status
"""

import sqlite3
import json
import re
import threading
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "data" / "friday_brain.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Serializes writes so concurrent FastAPI threads can't interleave
# read-modify-write sequences on the same tables.
_db_lock = threading.RLock()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def init_brain_db():
    """Create all tables for FRIDAY's unified brain on first boot."""
    with _db() as conn:

        # 1. Persistent Facts & Preferences (replaces old memories table)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            category    TEXT    NOT NULL DEFAULT 'preference',
            key_fact    TEXT    UNIQUE NOT NULL,
            value_fact  TEXT    NOT NULL,
            confidence  REAL    DEFAULT 1.0,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

        # 2. Conversation History (short-term context, last 20 turns kept)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS conversation_history (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            role      TEXT NOT NULL,
            message   TEXT NOT NULL,
            tokens    TEXT,            -- JSON keyword array for RAG search
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

        # 3. High-Value Habit Tracking
        # Only tracks: trading, spotify_play, weather_check, web_search, engineering_mode
        conn.execute("""
        CREATE TABLE IF NOT EXISTS user_action_habits (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type   TEXT    NOT NULL,
            hour_of_day   INTEGER NOT NULL,  -- 0..23
            day_of_week   INTEGER NOT NULL,  -- 0=Mon, 6=Sun
            frequency     INTEGER DEFAULT 1,
            last_executed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(action_type, hour_of_day, day_of_week)
        )""")

        # 4. Soft Correction Penalty Table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS user_corrections (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            query_pattern   TEXT NOT NULL,
            rejected_target TEXT NOT NULL,
            preferred_target TEXT,
            penalty_weight  REAL DEFAULT -40.0,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(query_pattern, rejected_target)
        )""")

        # 5. Career & Job Profile
        conn.execute("""
        CREATE TABLE IF NOT EXISTS job_profile (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            field           TEXT UNIQUE NOT NULL,  -- e.g. 'primary_role', 'skills', 'experience_years'
            value           TEXT NOT NULL,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

        # 6. Resume Data Sections
        conn.execute("""
        CREATE TABLE IF NOT EXISTS resume_data (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            section     TEXT NOT NULL,  -- 'summary', 'skills', 'experience', 'education', 'projects'
            content     TEXT NOT NULL,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

        # 7. Job Applications Tracker
        conn.execute("""
        CREATE TABLE IF NOT EXISTS job_applications (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            portal          TEXT NOT NULL,    -- 'linkedin', 'naukri', 'indeed', 'wellfound'
            job_title       TEXT NOT NULL,
            company         TEXT NOT NULL,
            job_url         TEXT,
            match_score     REAL DEFAULT 0.0, -- 0-100, how well it matches resume
            status          TEXT DEFAULT 'pending_review',
            -- 'pending_review' | 'approved' | 'applied' | 'rejected' | 'interview'
            found_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            applied_at      TIMESTAMP,
            notes           TEXT
        )""")

        conn.commit()
    print("[FRIDAY Brain] ✅ Unified brain database initialized.")


# Run on import
init_brain_db()


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Personal Facts & Persistent Memory (replaces memory.py functions)
# ═══════════════════════════════════════════════════════════════════════════════

def save_fact(key: str, value: str, category: str = "preference"):
    """Save or update a persistent fact about Prem."""
    with _db_lock:
        with _db() as conn:
            conn.execute("""
            INSERT INTO memories (category, key_fact, value_fact, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key_fact) DO UPDATE SET
                value_fact = excluded.value_fact,
                updated_at = CURRENT_TIMESTAMP
            """, (category, key.strip().lower(), value.strip()))
            conn.commit()
    # Semantic index (guarded — never breaks the save)
    try:
        from services.embeddings import on_fact_saved
        on_fact_saved(key.strip().lower(), value.strip())
    except Exception:
        pass


def get_all_memories() -> list:
    with _db() as conn:
        rows = conn.execute("SELECT key_fact, value_fact, category FROM memories").fetchall()
        return [{"key": r["key_fact"], "value": r["value_fact"], "category": r["category"]} for r in rows]


def get_memory_context_string() -> str:
    memories = get_all_memories()
    if not memories:
        return "No prior user preferences saved yet."
    lines = ["Permanent facts about Prem:"]
    for m in memories:
        lines.append(f"- [{m['category']}] {m['key']}: {m['value']}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Conversation History & RAG Semantic Memory
# ═══════════════════════════════════════════════════════════════════════════════

_STOP_WORDS = {"the", "and", "for", "that", "this", "with", "you", "are", "what",
               "how", "can", "please", "friday", "prem", "okay", "ok", "karo"}

def _keywords(text: str) -> list:
    words = re.findall(r'\b[a-zA-Z0-9\u0900-\u097F]{3,}\b', text.lower())
    return [w for w in words if w not in _STOP_WORDS]


def log_conversation(role: str, message: str):
    """Log a conversation turn. Keeps only last 20 turns."""
    if not message.strip():
        return
    tokens = json.dumps(_keywords(message))
    with _db_lock:
        with _db() as conn:
            conn.execute(
                "INSERT INTO conversation_history (role, message, tokens) VALUES (?, ?, ?)",
                (role, message.strip(), tokens)
            )
            # Trim to last 20 turns
            conn.execute("""
            DELETE FROM conversation_history
            WHERE id NOT IN (SELECT id FROM conversation_history ORDER BY id DESC LIMIT 20)
            """)
            conn.commit()


def get_recent_conversation(limit: int = 6) -> list:
    with _db() as conn:
        rows = conn.execute(
            "SELECT role, message FROM conversation_history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [{"role": r["role"], "message": r["message"]} for r in reversed(rows)]


def search_semantic_memories(query: str, limit: int = 3) -> list:
    """Keyword-overlap RAG search across past conversation turns."""
    q_tokens = set(_keywords(query))
    if not q_tokens:
        return []
    results = []
    with _db() as conn:
        rows = conn.execute(
            "SELECT role, message, tokens, timestamp FROM conversation_history ORDER BY id DESC LIMIT 60"
        ).fetchall()
        for row in rows:
            stored = set(json.loads(row["tokens"] or "[]"))
            overlap = len(q_tokens & stored)
            if overlap > 0:
                score = (overlap / max(1, len(q_tokens))) * 100.0
                results.append({"role": row["role"], "message": row["message"],
                                 "timestamp": row["timestamp"], "score": score})
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — High-Value Habit Learning & Proactive Suggestions
# ═══════════════════════════════════════════════════════════════════════════════

# Only these actions are considered "high-value" for habit tracking
HIGH_VALUE_ACTIONS = {
    "trading", "trading_station",
    "open_spotify", "play_music", "play_hindi_playlist", "play_english_playlist",
    "weather",
    "web_search",
    "engineering", "vscode",
    "job_search",
}

def log_user_action(action_type: str):
    """Log a high-value action by current hour and day of week."""
    if action_type not in HIGH_VALUE_ACTIONS:
        return
    now = datetime.now()
    with _db_lock:
        with _db() as conn:
            conn.execute("""
            INSERT INTO user_action_habits (action_type, hour_of_day, day_of_week, frequency, last_executed)
            VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(action_type, hour_of_day, day_of_week) DO UPDATE SET
                frequency = frequency + 1,
                last_executed = CURRENT_TIMESTAMP
            """, (action_type, now.hour, now.weekday()))
            conn.commit()


def get_proactive_habit_suggestion() -> dict | None:
    """Return a proactive suggestion if a high-value habit S_habit >= 0.70 with freq >= 3."""
    now = datetime.now()
    with _db() as conn:
        row = conn.execute("""
        SELECT action_type, frequency FROM user_action_habits
        WHERE hour_of_day = ? AND day_of_week = ? AND frequency >= 3
        ORDER BY frequency DESC LIMIT 1
        """, (now.hour, now.weekday())).fetchone()
        if not row:
            return None

    action = row["action_type"]
    freq = row["frequency"]
    confidence = min(1.0, freq / 5.0)
    if confidence < 0.70:
        return None

    prompts = {
        "trading":             "Prem, Indian markets are active. Shall I open your Trading Workstation?",
        "trading_station":     "Prem, it's trading time. Shall I launch your Quantum Trading Workstation?",
        "open_spotify":        "Prem, would you like me to start your music?",
        "play_music":          "Prem, shall I resume your playlist?",
        "play_hindi_playlist": "Prem, apna Hindi playlist start karun?",
        "weather":             "Prem, shall I give you today's weather summary?",
        "web_search":          "Prem, anything you'd like me to look up?",
        "engineering":         "Prem, shall I open VS Code for your session?",
        "job_search":          "Prem, shall I run a fresh job search on your portals?",
    }
    prompt = prompts.get(action, f"Prem, shall I start {action.replace('_', ' ')}?")
    return {"action": action, "prompt": prompt, "confidence": confidence}


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Soft Correction Detection & Penalty
# ═══════════════════════════════════════════════════════════════════════════════

# Phrases that signal a correction from Prem
_CORRECTION_TRIGGERS = [
    r"no\s+(not|friday|that)",
    r"wrong\s+(song|track|version|video|result)",
    r"not\s+(the\s+)?(remix|sped|slowed|cover|version|that)",
    r"(galat|yeh\s+nahi|sahi\s+nahi)",  # Hinglish
    r"play\s+the\s+original",
    r"that('s|\s+is)\s+(wrong|bad|not\s+it)",
]

def detect_and_log_correction(user_text: str, last_action_context: dict) -> bool:
    """Auto-detect correction phrases and log soft penalty.

    Args:
        user_text: What Prem just said
        last_action_context: dict with 'query' and 'target' keys from the last FRIDAY action
    Returns:
        True if a correction was detected and logged
    """
    lower = user_text.lower().strip()
    is_correction = any(re.search(p, lower) for p in _CORRECTION_TRIGGERS)
    if not is_correction:
        return False

    query = last_action_context.get("query", "").strip().lower()
    target = last_action_context.get("target", "").strip().lower()

    if not query or not target:
        return False

    with _db() as conn:
        conn.execute("""
        INSERT INTO user_corrections (query_pattern, rejected_target, penalty_weight)
        VALUES (?, ?, -40.0)
        ON CONFLICT(query_pattern, rejected_target) DO UPDATE SET
            penalty_weight = MIN(penalty_weight - 10.0, -80.0)
        """, (query, target))
        conn.commit()

    print(f"[FRIDAY Brain] 📝 Correction logged: '{query}' → reject '{target}'")
    return True


def get_correction_penalty(query: str, candidate: str) -> float:
    """Return the soft penalty score for a candidate under a given query."""
    q = query.strip().lower()
    c = candidate.strip().lower()
    with _db() as conn:
        row = conn.execute("""
        SELECT penalty_weight FROM user_corrections
        WHERE query_pattern = ? AND (rejected_target = ? OR ? LIKE '%' || rejected_target || '%')
        LIMIT 1
        """, (q, c, c)).fetchone()
    return float(row["penalty_weight"]) if row else 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Dynamic Pace Matching (Brevity Controller)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_response_brevity(user_text: str) -> str:
    """Determine AI reply length style from input word count and intent signals.

    Returns: 'ultra_concise' | 'balanced' | 'detailed'
    """
    clean = user_text.strip().lower()
    if any(k in clean for k in ["explain", "why", "how does", "tell me about", "detailed", "what is", "summarize", "difference between"]):
        return "detailed"
    words = clean.split()
    if len(words) <= 8:
        return "ultra_concise"   # most voice commands (play X, volume up, pause etc.)
    elif len(words) <= 15:
        return "balanced"        # short questions
    return "detailed"            # long multi-part queries



BREVITY_INSTRUCTIONS = {
    "ultra_concise": "ONE punchy phrase only. No explanation. No filler. Example: 'Done.' or 'Playing now.'",
    "balanced":      "ONE clear sentence. No filler words. Be direct.",
    "detailed":      "Max 3 sentences. Be clear and helpful. No padding.",
}


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Job Intelligence Engine
# ═══════════════════════════════════════════════════════════════════════════════

def save_job_profile(field: str, value: str):
    """Save or update Prem's career profile field (e.g. primary_role, skills)."""
    with _db() as conn:
        conn.execute("""
        INSERT INTO job_profile (field, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(field) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
        """, (field.strip().lower(), value.strip()))
        conn.commit()
    print(f"[FRIDAY Brain] 💼 Job profile updated: {field} = {value}")


def get_job_profile() -> dict:
    """Return full career profile as a dict."""
    with _db() as conn:
        rows = conn.execute("SELECT field, value FROM job_profile").fetchall()
    return {r["field"]: r["value"] for r in rows}


def save_resume_section(section: str, content: str):
    """Save or update a resume section (summary, skills, experience, education, projects)."""
    with _db() as conn:
        existing = conn.execute(
            "SELECT id FROM resume_data WHERE section = ?", (section,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE resume_data SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE section = ?",
                (content, section)
            )
        else:
            conn.execute(
                "INSERT INTO resume_data (section, content) VALUES (?, ?)", (section, content)
            )
        conn.commit()
    print(f"[FRIDAY Brain] 📄 Resume section saved: {section}")


def get_resume_context() -> str:
    """Returns resume data as a formatted string for LLM job matching."""
    with _db() as conn:
        rows = conn.execute("SELECT section, content FROM resume_data ORDER BY id").fetchall()
    if not rows:
        return "No resume data uploaded yet."
    lines = ["Prem's Resume:"]
    for r in rows:
        lines.append(f"\n### {r['section'].upper()}\n{r['content']}")
    return "\n".join(lines)


def save_found_job(portal: str, title: str, company: str, url: str = "", match_score: float = 0.0):
    """Record a job FRIDAY found during a search."""
    with _db() as conn:
        conn.execute("""
        INSERT INTO job_applications (portal, job_title, company, job_url, match_score)
        VALUES (?, ?, ?, ?, ?)
        """, (portal, title, company, url, match_score))
        conn.commit()
    print(f"[FRIDAY Brain] 🔍 Job found: {title} @ {company} ({portal}) — Match: {match_score:.0f}%")


def get_pending_jobs() -> list:
    """Return jobs awaiting Prem's review."""
    with _db() as conn:
        rows = conn.execute("""
        SELECT id, portal, job_title, company, job_url, match_score, found_at
        FROM job_applications WHERE status = 'pending_review'
        ORDER BY match_score DESC
        """).fetchall()
    return [dict(r) for r in rows]


def update_job_status(job_id: int, status: str, notes: str = ""):
    """Update a job application status (approved, applied, rejected, interview)."""
    # Parameterized query — never interpolate SQL fragments (see changelog v3 §1.2).
    applied_at = datetime.now().isoformat() if status == "applied" else None
    with _db_lock:
        with _db() as conn:
            conn.execute("""
            UPDATE job_applications
            SET status = ?, notes = ?, applied_at = ?
            WHERE id = ?
            """, (status, notes, applied_at, job_id))
            conn.commit()


def extract_job_profile_from_text(text: str) -> dict:
    """Auto-extract career signals from free-text and save to job_profile.

    Detects patterns like:
    - 'I am a Java developer'
    - 'I have 3 years of experience'
    - 'I know React, Python, Spring Boot'
    """
    extracted = {}

    # Detect primary role
    role_match = re.search(
        r'\bi\s+am\s+a(?:n)?\s+([a-zA-Z ]+?(?:developer|engineer|designer|analyst|manager|lead|architect))',
        text, re.IGNORECASE
    )
    if role_match:
        role = role_match.group(1).strip().title()
        save_job_profile("primary_role", role)
        extracted["primary_role"] = role

    # Detect experience years
    exp_match = re.search(r'\b(\d+)\s+years?\s+(?:of\s+)?experience', text, re.IGNORECASE)
    if exp_match:
        yrs = exp_match.group(1)
        save_job_profile("experience_years", yrs)
        extracted["experience_years"] = yrs

    # Detect tech skills (common stack keywords)
    skill_keywords = re.findall(
        r'\b(java|python|react|spring\s*boot|nodejs|typescript|javascript|kotlin|aws|'
        r'docker|kubernetes|sql|mongodb|machine\s*learning|data\s*science|flutter|'
        r'android|ios|swift|go|rust|c\+\+|c#|\.net|angular|vue)\b',
        text, re.IGNORECASE
    )
    if skill_keywords:
        skills_str = ", ".join(sorted(set(s.title() for s in skill_keywords)))
        save_job_profile("skills", skills_str)
        extracted["skills"] = skills_str

    return extracted
