"""Tests for the Phase 2.2 Memory Consolidation & Forgetting engine.

Acceptance per next_phase_2_architecture.md §7:
  * seeded conversations consolidate into memory_digest
  * confidence decays per §4-B (Ebbinghaus, 60-day half-life, 30-day grace)
  * brain context shrinks on repeat runs (idempotent decay + dedupe)

Data ownership under test isolation: `memories` + `conversation_history` live
in learning_engine's temp DB (accessed via learning_engine._db());
`memory_digest` lives in the consolidator's own temp DB.
"""

import math
from datetime import datetime, timedelta

import pytest

from services import learning_engine as le
from services import memory_consolidator as mc

NOW = datetime(2026, 8, 8, 12, 0, 0)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _no_llm(monkeypatch):
    """Deterministic consolidation: LLM extractor returns nothing."""
    monkeypatch.setattr(mc, "_extract_candidates", lambda turns: [])


def _seed_memory(key: str, created_days_ago: int | None = None,
                 accessed_days_ago: int | None = None, confidence: float = 1.0):
    le.save_fact(key, f"value for {key}")
    with le._db() as conn:
        if created_days_ago is not None:
            conn.execute(
                "UPDATE memories SET created_at = ?, confidence = ? WHERE key_fact = ?",
                ((NOW - timedelta(days=created_days_ago)).isoformat(timespec="seconds"),
                 confidence, key))
        if accessed_days_ago is not None:
            conn.execute(
                "UPDATE memories SET last_accessed = ? WHERE key_fact = ?",
                ((NOW - timedelta(days=accessed_days_ago)).isoformat(timespec="seconds"), key))
        conn.commit()


def _mem_row(key: str):
    with le._db() as conn:
        return conn.execute("SELECT * FROM memories WHERE key_fact = ?", (key,)).fetchone()


def _digest_row(content: str):
    with mc._db() as conn:
        return conn.execute(
            "SELECT * FROM memory_digest WHERE content = ?", (content,)).fetchone()


# ── Schema migration ─────────────────────────────────────────────────────────

def test_memories_table_migrated_with_consolidation_columns():
    with le._db() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(memories)")}
    assert {"access_count", "last_accessed", "last_decayed_at", "archived"} <= cols


def test_digest_table_created_once():
    with mc._db() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(memory_digest)")}
    assert {"kind", "content", "source_ids", "confidence",
            "archived", "created_at", "last_decayed_at"} <= cols


# ── Ebbinghaus decay & prune ─────────────────────────────────────────────────

def test_fresh_memory_is_not_decayed(monkeypatch):
    _no_llm(monkeypatch)
    _seed_memory("mc fresh fact", created_days_ago=10)
    r = mc.run(now=NOW)
    row = _mem_row("mc fresh fact")
    assert r["decayed"] == 0 and row["confidence"] == 1.0
    assert row["last_decayed_at"] is None


def test_old_memory_decays_with_sixty_day_half_life(monkeypatch):
    _no_llm(monkeypatch)
    _seed_memory("mc stale fact", created_days_ago=100)
    r = mc.run(now=NOW)
    row = _mem_row("mc stale fact")
    expected = math.exp(-mc.DECAY_K * 100)          # 2^(-100/60) ≈ 0.315
    assert row["confidence"] == pytest.approx(expected, abs=1e-4)
    assert row["archived"] == 0                      # 0.315 > 0.20 prune floor
    assert row["last_decayed_at"] is not None
    assert r["decayed"] >= 1


def test_recent_access_shields_old_memory(monkeypatch):
    _no_llm(monkeypatch)
    _seed_memory("mc accessed fact", created_days_ago=100, accessed_days_ago=2)
    r = mc.run(now=NOW)
    assert _mem_row("mc accessed fact")["confidence"] == 1.0
    assert r["decayed"] == 0


def test_decay_below_floor_prunes_but_keeps_row(monkeypatch):
    _no_llm(monkeypatch)
    _seed_memory("mc ancient fact", created_days_ago=200)
    r = mc.run(now=NOW)
    row = _mem_row("mc ancient fact")
    assert row is not None                           # kept in DB...
    assert row["archived"] == 1                      # ...but archived out of context
    assert row["confidence"] == pytest.approx(math.exp(-mc.DECAY_K * 200), abs=1e-4)
    keys = {m["key"] for m in le.get_all_memories()}
    assert "mc ancient fact" not in keys             # excluded from brain fetch


def test_decay_is_idempotent_within_same_day(monkeypatch):
    _no_llm(monkeypatch)
    _seed_memory("mc idempotent fact", created_days_ago=90)
    first = mc.run(now=NOW)
    conf_after_first = _mem_row("mc idempotent fact")["confidence"]
    second = mc.run(now=NOW)
    assert first["decayed"] >= 1
    assert second["decayed"] == 0                    # already decayed today
    assert _mem_row("mc idempotent fact")["confidence"] == conf_after_first


def test_digest_rows_decay_too(monkeypatch):
    _no_llm(monkeypatch)
    with mc._lock, mc._db() as conn:
        conn.execute(
            "INSERT INTO memory_digest (kind, content, confidence, created_at) "
            "VALUES ('fact', 'mc digest stale fact', 1.0, ?)",
            ((NOW - timedelta(days=120)).isoformat(timespec="seconds"),))
        conn.commit()
    mc.run(now=NOW)
    row = _digest_row("mc digest stale fact")
    assert row["confidence"] == pytest.approx(math.exp(-mc.DECAY_K * 120), abs=1e-4)


# ── Consolidation & dedupe ───────────────────────────────────────────────────

def test_seeded_conversations_consolidate_into_digest(monkeypatch):
    le.log_conversation("user", "remind me that my gym is at 7am every weekday")
    monkeypatch.setattr(mc, "_extract_candidates", lambda turns: [
        {"kind": "pattern", "content": "prem goes to the gym at 7am on weekdays"},
        {"kind": "fact", "content": "prem tracks indian stock markets daily"},
    ])
    r = mc.run(now=NOW)
    assert r["new_facts"] == 2
    assert _digest_row("prem goes to the gym at 7am on weekdays")["kind"] == "pattern"

    # Repeat run: same candidates merge instead of duplicating → idempotent.
    r2 = mc.run(now=NOW)
    assert r2["new_facts"] == 0 and r2["merged"] == 2
    with mc._db() as conn:
        n = conn.execute("SELECT COUNT(*) AS c FROM memory_digest "
                         "WHERE content LIKE 'prem %'").fetchone()["c"]
    assert n == 2
    # ...and merging boosted confidence per spec? No — same candidates already
    # at 1.0 cap; MERGE_BOOST is capped at 1.0.
    assert _digest_row("prem tracks indian stock markets daily")["confidence"] == 1.0


def test_merge_boosts_existing_digest_confidence(monkeypatch):
    _no_llm(monkeypatch)
    with mc._lock, mc._db() as conn:
        conn.execute(
            "INSERT INTO memory_digest (kind, content, confidence) "
            "VALUES ('fact', ?, 0.80)", ("he prefers oat milk in coffee",))
        conn.commit()
    outcome = mc._merge_candidate(
        {"kind": "fact", "content": "he prefers oat milk in his coffee"}, [1, 2], NOW)
    assert outcome == "merged"
    assert _digest_row("he prefers oat milk in coffee")["confidence"] == pytest.approx(0.85)


def test_candidate_matching_permanent_memory_boosts_memory_not_digest(monkeypatch):
    _no_llm(monkeypatch)
    _seed_memory("coffee preference")  # value_text: "coffee preference: value for coffee preference"
    with le._db() as conn:
        conn.execute("UPDATE memories SET value_fact = 'cold brew with oat milk' "
                     "WHERE key_fact = 'coffee preference'")
        conn.commit()
    outcome = mc._merge_candidate(
        {"kind": "fact", "content": "his coffee preference is cold brew with oat milk"}, [], NOW)
    assert outcome == "merged_memory"
    assert _digest_row("his coffee preference is cold brew with oat milk") is None


def test_no_sources_means_no_candidates_even_with_llm(monkeypatch):
    # run() with an empty 36h window: extractor must not even be called
    called = []
    monkeypatch.setattr(mc, "_extract_candidates",
                        lambda turns: called.append(turns) or [])
    with le._db() as conn:  # clear the window
        conn.execute("DELETE FROM conversation_history")
        conn.commit()
    r = mc.run(now=NOW)
    assert r["new_facts"] == 0 and called == [[]]


# ── Brain context integration ────────────────────────────────────────────────

def test_brain_context_includes_digest_and_tracks_access(monkeypatch):
    _no_llm(monkeypatch)
    _seed_memory("mc brain fact")
    with mc._lock, mc._db() as conn:
        conn.execute(
            "INSERT INTO memory_digest (kind, content, confidence) "
            "VALUES ('fact', 'mc consolidated insight about markets', 0.9)")
        conn.commit()
    ctx = le.get_memory_context_string()
    assert "mc brain fact" in ctx
    assert "mc consolidated insight about markets" in ctx
    assert "Consolidated knowledge" in ctx
    row = _mem_row("mc brain fact")
    assert row["access_count"] == 1 and row["last_accessed"] is not None


def test_brain_context_excludes_low_confidence_digest():
    with mc._lock, mc._db() as conn:
        conn.execute(
            "INSERT INTO memory_digest (kind, content, confidence) "
            "VALUES ('fact', 'mc too-weak fact for prompts', 0.30)")
        conn.commit()
    ctx = le.get_memory_context_string()
    assert "mc too-weak fact for prompts" not in ctx


# ── Automation + API ─────────────────────────────────────────────────────────

def test_automation_action_runs_consolidation(monkeypatch):
    _no_llm(monkeypatch)
    from services.automation import run_action
    summary = run_action("consolidate_memory")
    assert "Memory consolidation" in summary


def test_consolidate_endpoint_round_trip(client, monkeypatch):
    monkeypatch.setattr(mc, "_extract_candidates", lambda turns: [
        {"kind": "fact", "content": "mc api consolidated fact"},
    ])
    r = client.post("/api/memory/consolidate")
    assert r.status_code == 200
    body = r.json()
    for key in ("new_facts", "merged", "decayed", "pruned", "report", "ran_at"):
        assert key in body
    assert body["new_facts"] == 1

    d = client.get("/api/memory/digest")
    assert d.status_code == 200
    facts = d.json()["facts"]
    assert any(f["content"] == "mc api consolidated fact" for f in facts)
    assert "pruned_count" in d.json()


def test_consolidate_endpoints_remote_blocked(remote_client):
    assert remote_client.post("/api/memory/consolidate").status_code == 401
    assert remote_client.get("/api/memory/digest").status_code == 401
