"""
career_db.py — Career Intelligence Center: SQLite data layer.

All career tables live inside the existing friday_brain.db.
Zero interference with existing tables.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

DB_PATH = Path(__file__).parent.parent / "data" / "friday_brain.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_career_db():
    """Create all Career OS tables if they don't exist."""
    with _db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS career_preferences (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            source     TEXT DEFAULT 'user',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS career_profile (
            field        TEXT PRIMARY KEY,
            value        TEXT NOT NULL,
            is_sensitive INTEGER DEFAULT 0,
            updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS career_resumes (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            title            TEXT NOT NULL,
            content_json     TEXT NOT NULL DEFAULT '{}',
            version          INTEGER DEFAULT 1,
            is_archived      INTEGER DEFAULT 0,
            is_recommended   INTEGER DEFAULT 0,
            ats_score        REAL DEFAULT 0,
            performance_json TEXT DEFAULT '{"applied":0,"interviews":0,"offers":0}',
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS career_jobs (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            title               TEXT NOT NULL,
            company             TEXT NOT NULL,
            description         TEXT DEFAULT '',
            source              TEXT DEFAULT 'manual',
            url                 TEXT DEFAULT '',
            location            TEXT DEFAULT '',
            remote_type         TEXT DEFAULT 'unknown',
            salary_raw          TEXT DEFAULT '',
            salary_min          REAL DEFAULT 0,
            salary_max          REAL DEFAULT 0,
            experience_required TEXT DEFAULT '',
            visa_sponsorship    INTEGER DEFAULT 0,
            match_json          TEXT DEFAULT '{}',
            match_score         REAL DEFAULT 0,
            status              TEXT DEFAULT 'new',
            deadline            TEXT DEFAULT '',
            found_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            analyzed_at         TIMESTAMP
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS career_applications (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id          INTEGER REFERENCES career_jobs(id),
            resume_id       INTEGER REFERENCES career_resumes(id),
            cover_letter_id INTEGER,
            status          TEXT DEFAULT 'saved',
            applied_at      TIMESTAMP,
            deadline        TEXT DEFAULT '',
            recruiter_id    INTEGER,
            salary_offered  REAL DEFAULT 0,
            offer_details   TEXT DEFAULT '',
            notes           TEXT DEFAULT '',
            follow_up_date  TEXT DEFAULT '',
            timeline_json   TEXT DEFAULT '[]',
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS career_cover_letters (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id     INTEGER,
            resume_id  INTEGER,
            content    TEXT NOT NULL,
            tone       TEXT DEFAULT 'professional',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS career_recruiters (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            company      TEXT DEFAULT '',
            email        TEXT DEFAULT '',
            linkedin     TEXT DEFAULT '',
            phone        TEXT DEFAULT '',
            notes        TEXT DEFAULT '',
            last_contact TIMESTAMP,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS career_interviews (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id   INTEGER REFERENCES career_applications(id),
            stage            TEXT DEFAULT 'phone',
            scheduled_at     TEXT DEFAULT '',
            meeting_link     TEXT DEFAULT '',
            interviewer_name TEXT DEFAULT '',
            notes            TEXT DEFAULT '',
            prep_questions   TEXT DEFAULT '[]',
            outcome          TEXT DEFAULT 'pending',
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS career_companies (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT UNIQUE NOT NULL,
            domain           TEXT DEFAULT '',
            industry         TEXT DEFAULT '',
            size             TEXT DEFAULT '',
            reputation_score REAL DEFAULT 0,
            is_blacklisted   INTEGER DEFAULT 0,
            blacklist_reason TEXT DEFAULT '',
            notes            TEXT DEFAULT '',
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS career_activity_log (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type    TEXT NOT NULL,
            title         TEXT NOT NULL,
            description   TEXT DEFAULT '',
            metadata_json TEXT DEFAULT '{}',
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.commit()
    print("[Career OS] ✅ Career database initialized.")


init_career_db()


# ── Preferences ────────────────────────────────────────────────────────────────

PREFERENCE_DEFAULTS = {
    "min_salary": 0,
    "preferred_remote": "any",
    "preferred_countries": [],
    "preferred_cities": [],
    "preferred_tech_stack": [],
    "avoided_tech_stack": [],
    "preferred_industries": [],
    "avoided_industries": [],
    "preferred_roles": [],
    "avoided_roles": [],
    "blacklisted_companies": [],
    "favorite_companies": [],
    "job_types": ["full-time"],
    "experience_level": "any",
    "visa_required": False,
    "notice_period_days": 0,
}


def get_all_preferences() -> dict:
    with _db() as conn:
        rows = conn.execute("SELECT key, value FROM career_preferences").fetchall()
    result = dict(PREFERENCE_DEFAULTS)
    for r in rows:
        try:
            result[r["key"]] = json.loads(r["value"])
        except Exception:
            result[r["key"]] = r["value"]
    return result


def upsert_preference(key: str, value, source: str = "user"):
    with _db() as conn:
        conn.execute("""
        INSERT INTO career_preferences (key, value, source, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value, source = excluded.source,
            updated_at = CURRENT_TIMESTAMP
        """, (key, json.dumps(value), source))
        conn.commit()


def update_preferences_bulk(updates: dict, source: str = "user"):
    for key, value in updates.items():
        upsert_preference(key, value, source)


# ── Profile ────────────────────────────────────────────────────────────────────

SENSITIVE_FIELDS = {"email", "phone", "address", "salary", "password"}


def get_profile() -> dict:
    with _db() as conn:
        rows = conn.execute("SELECT field, value, is_sensitive FROM career_profile").fetchall()
    return {r["field"]: {"value": r["value"], "sensitive": bool(r["is_sensitive"])} for r in rows}


def upsert_profile_field(field: str, value: str, is_sensitive: bool = False):
    with _db() as conn:
        conn.execute("""
        INSERT INTO career_profile (field, value, is_sensitive, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(field) DO UPDATE SET
            value = excluded.value, is_sensitive = excluded.is_sensitive,
            updated_at = CURRENT_TIMESTAMP
        """, (field.strip().lower(), value.strip(), int(is_sensitive)))
        conn.commit()


def update_profile_bulk(fields: dict):
    for field, value in fields.items():
        upsert_profile_field(field, str(value), field.lower() in SENSITIVE_FIELDS)


# ── Resumes ────────────────────────────────────────────────────────────────────

def get_all_resumes(include_archived: bool = False) -> list:
    with _db() as conn:
        if include_archived:
            rows = conn.execute("SELECT * FROM career_resumes ORDER BY updated_at DESC").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM career_resumes WHERE is_archived = 0 ORDER BY updated_at DESC"
            ).fetchall()
    return [dict(r) for r in rows]


def get_resume(resume_id: int) -> Optional[dict]:
    with _db() as conn:
        row = conn.execute("SELECT * FROM career_resumes WHERE id = ?", (resume_id,)).fetchone()
    return dict(row) if row else None


def create_resume(title: str, content: dict) -> int:
    with _db() as conn:
        cur = conn.execute(
            "INSERT INTO career_resumes (title, content_json) VALUES (?, ?)",
            (title, json.dumps(content))
        )
        conn.commit()
        resume_id = cur.lastrowid
    log_activity("resume_created", f"Resume created: {title}")
    return resume_id


def update_resume(resume_id: int, updates: dict) -> bool:
    allowed = {"title", "content_json", "version", "is_archived", "is_recommended",
               "ats_score", "performance_json"}
    fields = {k: v for k, v in updates.items() if k in allowed}
    if not fields:
        return False
    if "content_json" in fields and isinstance(fields["content_json"], dict):
        fields["content_json"] = json.dumps(fields["content_json"])
    if "performance_json" in fields and isinstance(fields["performance_json"], dict):
        fields["performance_json"] = json.dumps(fields["performance_json"])
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with _db() as conn:
        conn.execute(
            f"UPDATE career_resumes SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            list(fields.values()) + [resume_id]
        )
        conn.commit()
    return True


def duplicate_resume(resume_id: int) -> Optional[int]:
    original = get_resume(resume_id)
    if not original:
        return None
    content = json.loads(original.get("content_json") or "{}")
    return create_resume(f"{original['title']} (Copy)", content)


def set_recommended_resume(resume_id: int):
    with _db() as conn:
        conn.execute("UPDATE career_resumes SET is_recommended = 0")
        conn.execute("UPDATE career_resumes SET is_recommended = 1 WHERE id = ?", (resume_id,))
        conn.commit()


def delete_resume(resume_id) -> bool:
    with _db() as conn:
        try:
            r_id = int(resume_id)
            conn.execute("UPDATE career_applications SET resume_id = NULL WHERE resume_id = ?", (r_id,))
            conn.execute("DELETE FROM career_resumes WHERE id = ?", (r_id,))
        except (ValueError, TypeError):
            conn.execute("UPDATE career_applications SET resume_id = NULL WHERE resume_id = ?", (str(resume_id),))
            conn.execute("DELETE FROM career_resumes WHERE id = ?", (str(resume_id),))
        conn.commit()
    log_activity("resume_deleted", f"Resume ID {resume_id} deleted")
    return True


# ── Jobs ───────────────────────────────────────────────────────────────────────

def get_jobs(status: Optional[str] = None, min_score: float = 0, source: Optional[str] = None) -> list:
    with _db() as conn:
        conditions = ["match_score >= ?"]
        params: list = [min_score]
        if status:
            conditions.append("status = ?")
            params.append(status)
        if source and source != "all":
            conditions.append("source = ?")
            params.append(source)
        where = " AND ".join(conditions)
        rows = conn.execute(
            f"SELECT * FROM career_jobs WHERE {where} ORDER BY match_score DESC, found_at DESC",
            params
        ).fetchall()
    return [dict(r) for r in rows]


def get_job(job_id: int) -> Optional[dict]:
    with _db() as conn:
        row = conn.execute("SELECT * FROM career_jobs WHERE id = ?", (job_id,)).fetchone()
    return dict(row) if row else None


def create_job(data: dict) -> int:
    fields = ["title", "company", "description", "source", "url", "location",
              "remote_type", "salary_raw", "salary_min", "salary_max",
              "experience_required", "visa_sponsorship", "deadline"]
    present = [f for f in fields if f in data]
    cols = ", ".join(present)
    placeholders = ", ".join("?" for _ in present)
    values = [data[f] for f in present]
    with _db() as conn:
        cur = conn.execute(f"INSERT INTO career_jobs ({cols}) VALUES ({placeholders})", values)
        conn.commit()
        job_id = cur.lastrowid
    log_activity("job_found", f"New opportunity: {data.get('title')} at {data.get('company')}")
    return job_id


def update_job(job_id: int, updates: dict) -> bool:
    allowed = {"status", "match_json", "match_score", "analyzed_at",
               "salary_min", "salary_max", "visa_sponsorship", "deadline"}
    fields = {k: v for k, v in updates.items() if k in allowed}
    if not fields:
        return False
    if "match_json" in fields and isinstance(fields["match_json"], dict):
        fields["match_json"] = json.dumps(fields["match_json"])
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with _db() as conn:
        conn.execute(
            f"UPDATE career_jobs SET {set_clause} WHERE id = ?",
            list(fields.values()) + [job_id]
        )
        conn.commit()
    return True


# ── Applications ───────────────────────────────────────────────────────────────

def get_applications(status: Optional[str] = None) -> list:
    with _db() as conn:
        if status:
            rows = conn.execute("""
                SELECT a.*, j.title as job_title, j.company, j.match_score, j.location
                FROM career_applications a LEFT JOIN career_jobs j ON a.job_id = j.id
                WHERE a.status = ? ORDER BY a.updated_at DESC
            """, (status,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT a.*, j.title as job_title, j.company, j.match_score, j.location
                FROM career_applications a LEFT JOIN career_jobs j ON a.job_id = j.id
                ORDER BY a.updated_at DESC
            """).fetchall()
    return [dict(r) for r in rows]


def create_application(job_id: int, resume_id: Optional[int] = None) -> int:
    with _db() as conn:
        cur = conn.execute(
            "INSERT INTO career_applications (job_id, resume_id) VALUES (?, ?)",
            (job_id, resume_id)
        )
        conn.commit()
        app_id = cur.lastrowid
    job = get_job(job_id)
    if job:
        log_activity("application_created",
                     f"Application tracked: {job['title']} at {job['company']}")
    update_job(job_id, {"status": "approved"})
    return app_id


def update_application(app_id: int, updates: dict) -> bool:
    allowed = {"status", "resume_id", "cover_letter_id", "recruiter_id",
               "notes", "follow_up_date", "deadline", "salary_offered",
               "offer_details", "applied_at", "timeline_json"}
    fields = {k: v for k, v in updates.items() if k in allowed}
    if not fields:
        return False
    if "status" in fields:
        conn2 = _db()
        row = conn2.execute(
            "SELECT timeline_json FROM career_applications WHERE id = ?", (app_id,)
        ).fetchone()
        if row:
            try:
                timeline = json.loads(row["timeline_json"] or "[]")
            except Exception:
                timeline = []
            timeline.append({"date": datetime.utcnow().isoformat(),
                              "event": f"Status → {fields['status']}"})
            fields["timeline_json"] = json.dumps(timeline)
        conn2.close()
        log_activity("status_changed", f"Application status: {fields['status']}")
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with _db() as conn:
        conn.execute(
            f"UPDATE career_applications SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            list(fields.values()) + [app_id]
        )
        conn.commit()
    return True


# ── Cover Letters ──────────────────────────────────────────────────────────────

def save_cover_letter(job_id: int, resume_id: Optional[int], content: str, tone: str = "professional") -> int:
    with _db() as conn:
        cur = conn.execute(
            "INSERT INTO career_cover_letters (job_id, resume_id, content, tone) VALUES (?, ?, ?, ?)",
            (job_id, resume_id, content, tone)
        )
        conn.commit()
        return cur.lastrowid


def get_cover_letters(job_id: Optional[int] = None) -> list:
    with _db() as conn:
        if job_id:
            rows = conn.execute(
                "SELECT * FROM career_cover_letters WHERE job_id = ? ORDER BY created_at DESC",
                (job_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM career_cover_letters ORDER BY created_at DESC"
            ).fetchall()
    return [dict(r) for r in rows]


# ── Recruiters ─────────────────────────────────────────────────────────────────

def get_recruiters() -> list:
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM career_recruiters ORDER BY last_contact DESC, created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def create_recruiter(data: dict) -> int:
    with _db() as conn:
        cur = conn.execute(
            "INSERT INTO career_recruiters (name, company, email, linkedin, phone, notes) VALUES (?,?,?,?,?,?)",
            (data.get("name", ""), data.get("company", ""), data.get("email", ""),
             data.get("linkedin", ""), data.get("phone", ""), data.get("notes", ""))
        )
        conn.commit()
        return cur.lastrowid


def update_recruiter(recruiter_id: int, updates: dict) -> bool:
    allowed = {"name", "company", "email", "linkedin", "phone", "notes", "last_contact"}
    fields = {k: v for k, v in updates.items() if k in allowed}
    if not fields:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with _db() as conn:
        conn.execute(
            f"UPDATE career_recruiters SET {set_clause} WHERE id = ?",
            list(fields.values()) + [recruiter_id]
        )
        conn.commit()
    return True


# ── Interviews ─────────────────────────────────────────────────────────────────

def get_interviews(upcoming_only: bool = False) -> list:
    with _db() as conn:
        if upcoming_only:
            rows = conn.execute("""
                SELECT i.*, j.title as job_title, j.company
                FROM career_interviews i
                LEFT JOIN career_applications a ON i.application_id = a.id
                LEFT JOIN career_jobs j ON a.job_id = j.id
                WHERE i.outcome = 'pending' ORDER BY i.scheduled_at ASC
            """).fetchall()
        else:
            rows = conn.execute("""
                SELECT i.*, j.title as job_title, j.company
                FROM career_interviews i
                LEFT JOIN career_applications a ON i.application_id = a.id
                LEFT JOIN career_jobs j ON a.job_id = j.id
                ORDER BY i.scheduled_at DESC
            """).fetchall()
    return [dict(r) for r in rows]


def create_interview(data: dict) -> int:
    with _db() as conn:
        cur = conn.execute(
            """INSERT INTO career_interviews
               (application_id, stage, scheduled_at, meeting_link, interviewer_name, notes)
               VALUES (?,?,?,?,?,?)""",
            (data.get("application_id"), data.get("stage", "phone"),
             data.get("scheduled_at", ""), data.get("meeting_link", ""),
             data.get("interviewer_name", ""), data.get("notes", ""))
        )
        conn.commit()
        interview_id = cur.lastrowid
    log_activity("interview_scheduled",
                 f"Interview scheduled: {data.get('stage', 'phone')} round")
    return interview_id


def update_interview(interview_id: int, updates: dict) -> bool:
    allowed = {"stage", "scheduled_at", "meeting_link", "interviewer_name",
               "notes", "prep_questions", "outcome"}
    fields = {k: v for k, v in updates.items() if k in allowed}
    if not fields:
        return False
    if "prep_questions" in fields and isinstance(fields["prep_questions"], list):
        fields["prep_questions"] = json.dumps(fields["prep_questions"])
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with _db() as conn:
        conn.execute(
            f"UPDATE career_interviews SET {set_clause} WHERE id = ?",
            list(fields.values()) + [interview_id]
        )
        conn.commit()
    return True


# ── Companies ──────────────────────────────────────────────────────────────────

def get_companies(blacklisted_only: bool = False) -> list:
    with _db() as conn:
        if blacklisted_only:
            rows = conn.execute(
                "SELECT * FROM career_companies WHERE is_blacklisted = 1 ORDER BY name"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM career_companies ORDER BY is_blacklisted ASC, name"
            ).fetchall()
    return [dict(r) for r in rows]


def upsert_company(name: str, data: dict = None) -> int:
    data = data or {}
    with _db() as conn:
        existing = conn.execute(
            "SELECT id FROM career_companies WHERE name = ?", (name,)
        ).fetchone()
        if existing:
            allowed = {"domain", "industry", "size", "reputation_score",
                       "is_blacklisted", "blacklist_reason", "notes"}
            fields = {k: v for k, v in data.items() if k in allowed}
            if fields:
                set_clause = ", ".join(f"{k} = ?" for k in fields)
                conn.execute(
                    f"UPDATE career_companies SET {set_clause} WHERE name = ?",
                    list(fields.values()) + [name]
                )
            conn.commit()
            return existing["id"]
        else:
            cur = conn.execute(
                """INSERT INTO career_companies
                   (name, domain, industry, size, reputation_score, is_blacklisted, blacklist_reason, notes)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (name, data.get("domain", ""), data.get("industry", ""),
                 data.get("size", ""), data.get("reputation_score", 0),
                 int(data.get("is_blacklisted", 0)), data.get("blacklist_reason", ""),
                 data.get("notes", ""))
            )
            conn.commit()
            return cur.lastrowid


def blacklist_company(name: str, reason: str = "User preference") -> bool:
    upsert_company(name, {"is_blacklisted": 1, "blacklist_reason": reason})
    prefs = get_all_preferences()
    blacklist = prefs.get("blacklisted_companies", [])
    if name not in blacklist:
        blacklist.append(name)
        upsert_preference("blacklisted_companies", blacklist, source="ai_inferred")
    log_activity("company_blacklisted", f"Company hidden: {name}", reason)
    return True


def is_company_blacklisted(name: str) -> bool:
    prefs = get_all_preferences()
    blacklist = [c.lower() for c in prefs.get("blacklisted_companies", [])]
    return name.lower() in blacklist


# ── Activity Log ───────────────────────────────────────────────────────────────

def log_activity(event_type: str, title: str, description: str = "", metadata: dict = None):
    with _db() as conn:
        conn.execute(
            "INSERT INTO career_activity_log (event_type, title, description, metadata_json) VALUES (?,?,?,?)",
            (event_type, title, description, json.dumps(metadata or {}))
        )
        conn.commit()


def get_activity_log(limit: int = 20) -> list:
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM career_activity_log ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# ── Dashboard Stats ────────────────────────────────────────────────────────────

def get_dashboard_stats() -> dict:
    with _db() as conn:
        new_jobs = conn.execute(
            "SELECT COUNT(*) FROM career_jobs WHERE status = 'new'"
        ).fetchone()[0]
        high_priority = conn.execute(
            "SELECT COUNT(*) FROM career_jobs WHERE match_score >= 80 AND status = 'new'"
        ).fetchone()[0]
        pending_approval = conn.execute(
            "SELECT COUNT(*) FROM career_jobs WHERE status IN ('bookmarked','new') AND match_score >= 70"
        ).fetchone()[0]
        submitted = conn.execute(
            "SELECT COUNT(*) FROM career_applications WHERE status IN ('submitted','viewed')"
        ).fetchone()[0]
        interviews = conn.execute(
            "SELECT COUNT(*) FROM career_interviews WHERE outcome = 'pending'"
        ).fetchone()[0]
        offers = conn.execute(
            "SELECT COUNT(*) FROM career_applications WHERE status = 'offer'"
        ).fetchone()[0]
        total_apps = conn.execute(
            "SELECT COUNT(*) FROM career_applications"
        ).fetchone()[0]
        deadlines = conn.execute("""
            SELECT title, company, deadline FROM career_jobs
            WHERE deadline != '' AND status NOT IN ('applied','ignored')
            ORDER BY deadline ASC LIMIT 5
        """).fetchall()
    return {
        "new_jobs": new_jobs,
        "high_priority": high_priority,
        "pending_approval": pending_approval,
        "submitted": submitted,
        "interviews": interviews,
        "offers": offers,
        "total_applications": total_apps,
        "upcoming_deadlines": [dict(d) for d in deadlines],
    }


# ── Analytics ──────────────────────────────────────────────────────────────────

def get_analytics() -> dict:
    with _db() as conn:
        monthly = conn.execute("""
            SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count
            FROM career_applications GROUP BY month ORDER BY month DESC LIMIT 6
        """).fetchall()
        funnel = conn.execute("""
            SELECT status, COUNT(*) as count FROM career_applications GROUP BY status
        """).fetchall()
        resume_perf = conn.execute("""
            SELECT r.title, r.ats_score,
                   COUNT(a.id) as applications,
                   SUM(CASE WHEN a.status IN ('interview','offer') THEN 1 ELSE 0 END) as successes
            FROM career_resumes r LEFT JOIN career_applications a ON r.id = a.resume_id
            WHERE r.is_archived = 0 GROUP BY r.id
        """).fetchall()
        avg_score = conn.execute(
            "SELECT AVG(match_score) FROM career_jobs WHERE match_score > 0"
        ).fetchone()[0] or 0
        top_companies = conn.execute("""
            SELECT j.company, COUNT(*) as apps
            FROM career_applications a JOIN career_jobs j ON a.job_id = j.id
            GROUP BY j.company ORDER BY apps DESC LIMIT 8
        """).fetchall()
    return {
        "monthly_applications": [dict(r) for r in monthly],
        "status_funnel": {r["status"]: r["count"] for r in funnel},
        "resume_performance": [dict(r) for r in resume_perf],
        "avg_match_score": round(avg_score, 1),
        "top_companies": [dict(r) for r in top_companies],
    }
