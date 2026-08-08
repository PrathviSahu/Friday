"""memory_consolidator.py — Memory Consolidation & Forgetting (Phase 2.2).

Nightly distillation of raw experience into durable knowledge, per
next_phase_2_architecture.md §4-B:

  1. EXTRACT  — LLM pass over the last ~24h of conversation turns (+ notes,
                when accessible) → candidate facts/patterns. Graceful: no LLM
                key or parse failure → zero candidates, the rest of the
                pipeline still runs.
  2. MERGE    — cosine ≥ 0.92 against indexed digest items via the existing
                embeddings store → merge (confidence +0.05, capped 1.0);
                keyword-Jaccard ≥ 0.75 fallback when embeddings are offline.
                Candidates matching an EXISTING permanent memory boost that
                memory instead of duplicating it.
  3. DECAY    — Ebbinghaus: after a 30-day grace period without access,
                confidence ×= e^(−k·days), k = ln2/60 (half-life 60 days).
                `last_decayed_at` makes the sweep idempotent per day.
  4. PRUNE    — confidence < 0.20 → archived: kept in DB, excluded from the
                brain context (get_memory_context_string).
  5. REPORT   — summary lands in the Notification Center.

Data ownership (same rule as autonomy_engine): `memories` belongs to
learning_engine — every read/write goes through learning_engine's OWN
connection, so the module works both in production (one shared
friday_brain.db) and under test isolation (per-module temp DBs). This
module's own DB file holds ONLY memory_digest.

Spec refinements documented in the status note:
  * `memories` gains THREE columns: access_count, last_accessed (spec) plus
    last_decayed_at + archived (needed for idempotent decay & pruning).
  * Decay accrues per day past the grace period at run cadence, anchored by
    last_decayed_at — re-running twice in one day never double-decays.
"""

import json
import math
import re
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "friday_brain.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_lock = threading.RLock()

# ── Model constants (next_phase_2_architecture.md §4-B) ───────────────────────

DECAY_K = math.log(2) / 60.0        # half-life: 60 days
GRACE_DAYS = 30                     # untouched for this long before decay starts
PRUNE_THRESHOLD = 0.20              # below → archived out of brain context
MERGE_BOOST = 0.05                  # confidence bump on merge (+cap 1.0)
MERGE_SIMILARITY_SEMANTIC = 0.92    # cosine threshold via embeddings store
MERGE_SIMILARITY_KEYWORD = 0.75     # Jaccard fallback when embeddings offline
DIGEST_BRAIN_FLOOR = 0.50           # digest facts below this skip brain prompts
SOURCE_WINDOW_HOURS = 36            # last-N-hours of conversation to distill
MAX_CANDIDATES = 12                 # per run — keep the night job cheap


def _now() -> datetime:
    """Single clock — monkeypatched by tests."""
    return datetime.now()


# ── Database: own store (memory_digest only) ─────────────────────────────────

def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def init_consolidator_db() -> None:
    """Create memory_digest + migrate learning_engine.memories (additive)."""
    with _db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS memory_digest (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            kind            TEXT NOT NULL,          -- 'fact' | 'pattern' | 'summary'
            content         TEXT NOT NULL UNIQUE,
            source_ids      TEXT,                   -- JSON array of source row ids
            confidence      REAL DEFAULT 1.0,
            archived        INTEGER DEFAULT 0,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_decayed_at TIMESTAMP
        )""")
        conn.commit()
    _migrate_memories()


def _le_db() -> sqlite3.Connection:
    """learning_engine's own connection — owner of `memories` (see module doc)."""
    from services import learning_engine
    return learning_engine._db()


def _migrate_memories() -> None:
    """Add consolidation columns to learning_engine.memories, guarded + additive.

    Skipped silently when that table isn't reachable on this boot (e.g. a
    bare consolidator DB in isolation) — production always has it.
    """
    try:
        with _le_db() as conn:
            cols = {r["name"] for r in conn.execute("PRAGMA table_info(memories)")}
            if not cols:
                return
            for col, ddl in (
                ("access_count",    "ALTER TABLE memories ADD COLUMN access_count INTEGER DEFAULT 0"),
                ("last_accessed",   "ALTER TABLE memories ADD COLUMN last_accessed TIMESTAMP"),
                ("last_decayed_at", "ALTER TABLE memories ADD COLUMN last_decayed_at TIMESTAMP"),
                ("archived",        "ALTER TABLE memories ADD COLUMN archived INTEGER DEFAULT 0"),
            ):
                if col not in cols:
                    conn.execute(ddl)
            conn.commit()
    except sqlite3.OperationalError:
        pass


init_consolidator_db()


# ── Step 1: EXTRACT (graceful LLM pass) ───────────────────────────────────────

def _source_conversations(now: datetime) -> list:
    """Recent conversation turns through learning_engine's store."""
    since = (now - timedelta(hours=SOURCE_WINDOW_HOURS)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        with _le_db() as conn:
            rows = conn.execute(
                "SELECT id, role, message FROM conversation_history "
                "WHERE timestamp >= ? ORDER BY id DESC LIMIT 60", (since,)).fetchall()
        return [{"id": r["id"], "role": r["role"], "message": r["message"]} for r in rows]
    except sqlite3.OperationalError:
        return []


def _extract_candidates(turns: list) -> list:
    """LLM distillation → [{'kind': 'fact|pattern|summary', 'content': str}, ...].

    Never raises: any failure (no key, bad JSON, offline) → empty list.
    Tests monkeypatch this function to control candidates deterministically.
    """
    if not turns:
        return []
    import os
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return []
    transcript = "\n".join(f"{t['role']}: {t['message']}" for t in turns[:40])[:6000]
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=[
                {"role": "system", "content": (
                    "You distill a personal AI assistant's recent conversations into "
                    "durable long-term knowledge. Reply with a JSON array ONLY, e.g. "
                    '[{"kind": "fact", "content": "Prem prefers cold brew coffee"}]. '
                    "kind ∈ fact (stable preference/fact), pattern (recurring habit), "
                    "summary (worth-remembering event). Skip small talk and one-off "
                    "requests. Max 12 items, each < 120 chars.")},
                {"role": "user", "content": transcript},
            ],
            temperature=0.2, max_tokens=800,
        )
        text = (resp.choices[0].message.content or "").strip()
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            return []
        raw = json.loads(match.group(0))
        out = []
        for item in raw[:MAX_CANDIDATES]:
            content = str(item.get("content", "")).strip()
            if len(content) < 8:
                continue
            kind = item.get("kind") if item.get("kind") in {"fact", "pattern", "summary"} else "fact"
            out.append({"kind": kind, "content": content[:200]})
        return out
    except Exception:
        return []


# ── Step 2: MERGE (semantic ≥ 0.92, keyword fallback ≥ 0.75) ─────────────────

def _keywords(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9'\u0900-\u097F]{3,}", text.lower())}


def _jaccard(a: str, b: str) -> float:
    ta, tb = _keywords(a), _keywords(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _semantic_match(content: str) -> str | None:
    """Best-matching indexed digest text via the embeddings store, or None.

    Honors the spec's cosine ≥ 0.92 merge threshold when the semantic store
    is live; silently None when embeddings are offline/unavailable.
    """
    try:
        from services import embeddings
        if not embeddings.available():
            return None
        hits = embeddings.retrieve(content, k=1)
        if hits and hits[0]["source"] == "digest" and hits[0]["score"] >= MERGE_SIMILARITY_SEMANTIC:
            return hits[0]["text"]
    except Exception:
        pass
    return None


def _index_digest(content: str, digest_id: int) -> None:
    try:
        from services import embeddings
        embeddings.index_text("digest", str(digest_id), content)
    except Exception:
        pass


def _merge_candidate(candidate: dict, source_ids: list, now: datetime) -> str:
    """Merge one candidate into digest/memories. Returns 'new' | 'merged' | 'merged_memory'."""
    content = candidate["content"]
    norm = content.strip().lower()

    with _lock, _db() as conn:
        digest_rows = conn.execute(
            "SELECT id, content, confidence, source_ids FROM memory_digest WHERE archived = 0"
        ).fetchall()

    # 1. Exact/semantic match against the digest itself.
    target = None
    for row in digest_rows:
        if row["content"].strip().lower() == norm:
            target = row
            break
    if target is None:
        sem = _semantic_match(content)
        if sem:
            target = next((r for r in digest_rows if r["content"] == sem), None)

    # 2. Keyword fallback vs digest.
    if target is None:
        best, best_score = None, 0.0
        for row in digest_rows:
            score = _jaccard(content, row["content"])
            if score > best_score:
                best, best_score = row, score
        if best_score >= MERGE_SIMILARITY_KEYWORD:
            target = best

    if target is not None:
        merged_sources = sorted(set(json.loads(target["source_ids"] or "[]")) | set(source_ids))
        with _lock, _db() as conn:
            conn.execute(
                "UPDATE memory_digest SET confidence = MIN(1.0, confidence + ?), source_ids = ? "
                "WHERE id = ?", (MERGE_BOOST, json.dumps(merged_sources), target["id"]))
            conn.commit()
        return "merged"

    # 3. Existing permanent memory? Boost it — never duplicate knowledge.
    mem_text = None
    try:
        with _le_db() as conn:
            rows = conn.execute(
                "SELECT key_fact, value_fact FROM memories WHERE archived = 0").fetchall()
        for r in rows:
            text = f"{r['key_fact']}: {r['value_fact']}"
            if _jaccard(content, text) >= MERGE_SIMILARITY_KEYWORD:
                mem_text = r["key_fact"]
                break
    except sqlite3.OperationalError:
        pass
    if mem_text:
        with _lock, _le_db() as conn:
            conn.execute(
                "UPDATE memories SET confidence = MIN(1.0, confidence + ?), "
                "updated_at = CURRENT_TIMESTAMP WHERE key_fact = ?",
                (MERGE_BOOST, mem_text))
            conn.commit()
        return "merged_memory"

    # 4. Novel knowledge → new digest row + semantic index.
    with _lock, _db() as conn:
        cur = conn.execute(
            "INSERT INTO memory_digest (kind, content, source_ids, confidence) VALUES (?, ?, ?, 1.0)",
            (candidate["kind"], content, json.dumps(source_ids)))
        conn.commit()
        digest_id = cur.lastrowid
    _index_digest(content, digest_id)
    return "new"


# ── Steps 3–4: DECAY & PRUNE (Ebbinghaus, idempotent) ────────────────────────

def _parse_ts(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", ""))
    except ValueError:
        return None


def _decay_table(conn, table: str, now: datetime) -> tuple[int, int]:
    """Decay one table (must have confidence/archived/last_decayed_at).
    Returns (decayed_count, pruned_count)."""
    touch_col = "last_accessed" if table == "memories" else None
    cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
    if "confidence" not in cols or "archived" not in cols:
        return 0, 0
    select_touch = f", {touch_col}" if touch_col and touch_col in cols else ""
    rows = conn.execute(
        f"SELECT id, confidence, created_at, last_decayed_at{select_touch}"
        f" FROM {table} WHERE archived = 0").fetchall()

    decayed = pruned = 0
    for row in rows:
        created = _parse_ts(row["created_at"]) or now
        last_touch = (_parse_ts(row[touch_col]) if touch_col and touch_col in cols
                      else None) or created
        if (now - last_touch) < timedelta(days=GRACE_DAYS):
            continue                                    # still inside the grace period
        ref = _parse_ts(row["last_decayed_at"]) or last_touch
        days = (now - ref).days
        if days <= 0:
            continue                                    # idempotent: already decayed today
        new_conf = row["confidence"] * math.exp(-DECAY_K * days)
        archive = 1 if new_conf < PRUNE_THRESHOLD else 0
        conn.execute(
            f"UPDATE {table} SET confidence = ?, last_decayed_at = ?, archived = ? WHERE id = ?",
            (new_conf, now.isoformat(timespec="seconds"), archive, row["id"]))
        decayed += 1
        pruned += archive
    return decayed, pruned


def _apply_decay_and_prune(now: datetime) -> tuple[int, int]:
    decayed = pruned = 0
    with _lock, _db() as conn:
        d, p = _decay_table(conn, "memory_digest", now)
        decayed += d
        pruned += p
        conn.commit()
    try:
        with _lock, _le_db() as conn:
            d, p = _decay_table(conn, "memories", now)
            decayed += d
            pruned += p
            conn.commit()
    except sqlite3.OperationalError:
        pass  # memories columns not migrated on this DB layout
    return decayed, pruned


# ── Public: nightly run ───────────────────────────────────────────────────────

def run(now: datetime | None = None) -> dict:
    """One full consolidation pass. Returns counts + human-readable report.

    Registered as the `consolidate_memory` automation action (nightly 03:30)
    and manually triggerable via POST /api/memory/consolidate.
    """
    now = now or _now()
    turns = _source_conversations(now)
    source_ids = [t["id"] for t in turns]

    new_facts = merged = merged_memory = 0
    for candidate in _extract_candidates(turns):
        outcome = _merge_candidate(candidate, source_ids[:20], now)
        if outcome == "new":
            new_facts += 1
        elif outcome == "merged":
            merged += 1
        else:
            merged_memory += 1

    decayed, pruned = _apply_decay_and_prune(now)

    report = (f"Memory consolidation: {new_facts} new, {merged + merged_memory} merged, "
              f"{decayed} decayed, {pruned} pruned.")
    result = {"status": "ok", "new_facts": new_facts, "merged": merged + merged_memory,
              "decayed": decayed, "pruned": pruned, "report": report,
              "ran_at": now.isoformat(timespec="seconds")}

    # Step 5 — the summary lands in the Notification Center instead of interrupting.
    try:
        from services.notifications import push_notification
        push_notification("Memory Consolidation", report, "general")
    except Exception:
        pass
    return result


# ── Brain-facing accessors ────────────────────────────────────────────────────

def get_brain_facts(limit: int = 12) -> list:
    """High-confidence digest items for get_memory_context_string() injection."""
    with _db() as conn:
        rows = conn.execute(
            "SELECT kind, content, confidence FROM memory_digest "
            "WHERE archived = 0 AND confidence >= ? ORDER BY confidence DESC, id DESC LIMIT ?",
            (DIGEST_BRAIN_FLOOR, limit)).fetchall()
    return [{"kind": r["kind"], "content": r["content"], "confidence": r["confidence"]}
            for r in rows]


def get_digest(limit: int = 100) -> dict:
    """HUD/API view: live digest items + total pruned count (both tables)."""
    with _db() as conn:
        rows = conn.execute(
            "SELECT id, kind, content, confidence, created_at FROM memory_digest "
            "WHERE archived = 0 ORDER BY confidence DESC, id DESC LIMIT ?", (limit,)).fetchall()
        digest_pruned = conn.execute(
            "SELECT COUNT(*) AS n FROM memory_digest WHERE archived = 1").fetchone()["n"]
    mem_pruned = 0
    try:
        with _le_db() as conn:
            mem_pruned = conn.execute(
                "SELECT COUNT(*) AS n FROM memories WHERE archived = 1").fetchone()["n"]
    except sqlite3.OperationalError:
        pass
    return {"facts": [dict(r) for r in rows], "pruned_count": int(digest_pruned) + int(mem_pruned)}
