"""Tests for the brain smartness upgrade:
  A) conversation context in every LLM call
  B) semantic memory (embeddings RAG) with graceful fallback
  C) multi-step agentic tool loop
"""

import pytest


# ── A: conversation context ──────────────────────────────────────────────

def test_build_context_messages_includes_history_and_memory(monkeypatch):
    """The message list must contain system, history, memory and user turns."""
    from services import brain_v2

    fake_history = [
        {"role": "user", "message": "what's my schedule tomorrow?"},
        {"role": "assistant", "message": "You have a standup at 10 AM."},
    ]
    monkeypatch.setattr("services.learning_engine.get_recent_conversation",
                        lambda limit: fake_history)
    monkeypatch.setattr("services.learning_engine.get_memory_context_string",
                        lambda: "Permanent facts:\n- [preference] boss_name: Prem")
    monkeypatch.setattr("services.embeddings.semantic_context", lambda q, k: "")

    messages = brain_v2._build_context_messages("what about the day after?")
    roles = [m["role"] for m in messages]
    assert roles == ["system", "user", "assistant", "system", "user"]
    assert messages[-1]["content"] == "what about the day after?"
    assert "Prem" in messages[3]["content"]
    assert "standup" in messages[2]["content"]


def test_build_context_injects_semantic_memories(monkeypatch):
    from services import brain_v2
    monkeypatch.setattr("services.learning_engine.get_recent_conversation", lambda limit: [])
    monkeypatch.setattr("services.learning_engine.get_memory_context_string",
                        lambda: "No prior user preferences saved yet.")
    monkeypatch.setattr("services.embeddings.semantic_context",
                        lambda q, k: "Relevant memories:\n- [meeting] Standup tomorrow 10 AM")
    messages = brain_v2._build_context_messages("any meetings soon?")
    assert "Standup tomorrow" in messages[-2]["content"]


# ── C: multi-step agentic loop ───────────────────────────────────────────

def test_respond_v2_loops_until_final_answer(monkeypatch):
    """Tool call → result fed back → second call answers."""
    from services import brain_v2
    calls = []

    def fake_groq(messages, tools):
        calls.append(len(messages))
        if len(calls) == 1:
            return {"tool_calls": [{"id": "c1", "name": "get_time", "arguments": {}}],
                    "content": ""}
        return {"tool_calls": [], "content": "It's 10:00 AM, Prem."}

    monkeypatch.setattr(brain_v2, "_call_groq_with_messages", fake_groq)
    monkeypatch.setattr(brain_v2, "_groq_client", lambda: object())
    monkeypatch.setattr("services.learning_engine.get_recent_conversation", lambda limit: [])
    monkeypatch.setattr("services.learning_engine.get_memory_context_string",
                        lambda: "No prior user preferences saved yet.")
    monkeypatch.setattr("services.embeddings.semantic_context", lambda q, k: "")

    result = brain_v2.respond_v2("what time is it", is_boss=True)
    assert len(calls) == 2
    assert result["function"] == "get_time"
    assert result["reply"] == "It's 10:00 AM, Prem."


def test_respond_v2_multiple_tools_one_request(monkeypatch):
    """Two different tools can run in one request before the answer."""
    from services import brain_v2
    executed = []

    def fake_dispatch(name, args):
        executed.append(name)
        return f"ran {name}"

    monkeypatch.setattr(brain_v2.function_engine, "dispatch", fake_dispatch)

    def fake_groq(messages, tools):
        if len(executed) == 0:
            return {"tool_calls": [
                {"id": "c1", "name": "get_weather", "arguments": {}},
                {"id": "c2", "name": "get_todos", "arguments": {}},
            ], "content": ""}
        return {"tool_calls": [], "content": "Done both."}

    monkeypatch.setattr(brain_v2, "_call_groq_with_messages", fake_groq)
    monkeypatch.setattr(brain_v2, "_groq_client", lambda: object())
    monkeypatch.setattr("services.learning_engine.get_recent_conversation", lambda limit: [])
    monkeypatch.setattr("services.learning_engine.get_memory_context_string",
                        lambda: "No prior user preferences saved yet.")
    monkeypatch.setattr("services.embeddings.semantic_context", lambda q, k: "")

    result = brain_v2.respond_v2("weather and my todos", is_boss=True)
    assert executed == ["get_weather", "get_todos"]
    assert result["reply"] == "Done both."


def test_respond_v2_loop_capped(monkeypatch):
    """Runaway tool loops are capped, not infinite."""
    from services import brain_v2
    calls = []

    def fake_groq(messages, tools):
        calls.append(1)
        return {"tool_calls": [{"id": "c1", "name": "get_time", "arguments": {}}],
                "content": ""}

    monkeypatch.setattr(brain_v2, "_call_groq_with_messages", fake_groq)
    monkeypatch.setattr(brain_v2, "_groq_client", lambda: object())
    monkeypatch.setattr("services.learning_engine.get_recent_conversation", lambda limit: [])
    monkeypatch.setattr("services.learning_engine.get_memory_context_string",
                        lambda: "No prior user preferences saved yet.")
    monkeypatch.setattr("services.embeddings.semantic_context", lambda q, k: "")

    result = brain_v2.respond_v2("loop forever", is_boss=True)
    assert len(calls) == 4  # max steps
    assert result["reply"]  # last tool reply used as wrap-up


# ── B: semantic memory (embeddings RAG) ─────────────────────────────────

def _fake_embedder():
    """Deterministic 'embedding': words → unit vectors via char hashing."""
    def embed(texts):
        import numpy as np
        out = []
        for t in texts:
            vec = np.zeros(64)
            for ch in t.lower():
                if ch.isalnum():
                    vec[ord(ch) % 64] += 1
            norm = np.linalg.norm(vec) or 1.0
            out.append((vec / norm).tolist())
        return out
    return embed


def test_embeddings_index_and_retrieve(monkeypatch, tmp_path):
    """Items are stored with vectors; retrieval ranks by cosine similarity."""
    from services import embeddings
    monkeypatch.setattr(embeddings, "DB_PATH", tmp_path / "emb.db")
    embeddings.init_embeddings_db()
    monkeypatch.setattr(embeddings, "_get_embedder", _fake_embedder)

    assert embeddings.index_text("memory", "f1", "Boss has a job interview on Friday")
    assert embeddings.index_text("note", "n1", "Gym workout plan for the week")

    hits = embeddings.retrieve("job interview upcoming", k=2)
    assert len(hits) == 2
    assert hits[0]["text"].startswith("Boss has a job interview")
    assert hits[0]["source"] == "memory"


def test_embeddings_unavailable_falls_back_gracefully(monkeypatch, tmp_path):
    """No embedder → retrieve returns empty, never crashes."""
    from services import embeddings
    monkeypatch.setattr(embeddings, "DB_PATH", tmp_path / "emb2.db")
    embeddings.init_embeddings_db()
    monkeypatch.setattr(embeddings, "_get_embedder", lambda: None)

    assert embeddings.available() is False
    assert embeddings.retrieve("anything") == []
    assert embeddings.semantic_context("anything") == ""
    assert embeddings.index_text("memory", "x", "y") is False


def test_embeddings_collect_sources(monkeypatch, tmp_path):
    """ensure_indexed pulls from memories, notes and meetings."""
    from services import embeddings
    monkeypatch.setattr(embeddings, "DB_PATH", tmp_path / "emb3.db")
    embeddings.init_embeddings_db()
    monkeypatch.setattr(embeddings, "_get_embedder", _fake_embedder)
    monkeypatch.setattr(embeddings, "_last_indexed", [0.0])

    monkeypatch.setattr("services.learning_engine.get_all_memories",
                        lambda: [{"category": "preference", "key": "boss_name", "value": "Prem"}])
    monkeypatch.setattr("services.knowledge.list_notes",
                        lambda limit=300: [{"id": 1, "title": "Idea", "content": "Build a spaceship"}])
    monkeypatch.setattr("services.meeting_agent.list_meetings",
                        lambda limit=100: [{"id": "m1", "title": "Standup", "summary": "Quick sync"}])

    assert embeddings.ensure_indexed() is True
    hits = embeddings.retrieve("standup sync", k=3)
    assert any("Standup" in h["text"] for h in hits)
