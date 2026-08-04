"""Tests for the Document Agent (service + routes).

LLM calls are faked — no network, no API credits.
"""

import pytest


# ── Service: extraction ──────────────────────────────────────────────────

def test_extract_txt():
    from services import document_agent
    text, meta = document_agent.extract_text("notes.txt", b"Hello Boss, this is a note.")
    assert "Hello Boss" in text
    assert meta["ext"] == ".txt"


def test_extract_unsupported_type():
    from services import document_agent
    with pytest.raises(document_agent.DocumentUnavailableError):
        document_agent.extract_text("virus.exe", b"MZ...")


def test_extract_empty_txt_rejected():
    from services import document_agent
    with pytest.raises(document_agent.DocumentUnavailableError):
        document_agent.extract_text("empty.txt", b"   \n  ")


def test_add_and_get_document():
    from services import document_agent
    doc = document_agent.add_document("meeting_notes.txt", b"We discussed the roadmap.")
    assert doc["title"] == "meeting_notes"
    assert doc["snippet"]
    full = document_agent.get_document(doc["id"], include_text=True)
    assert "roadmap" in full["text"]
    listed = document_agent.list_documents()
    assert listed[0]["id"] == doc["id"]
    assert "text" not in listed[0]  # list is snippet-only


def test_search_and_delete():
    from services import document_agent
    document_agent.add_document("resume.txt", b"Java Spring Boot AWS experience")
    document_agent.add_document("gym.txt", b"Workout plan for the week")
    hits = document_agent.search_documents("spring")
    assert len(hits) == 1
    assert "resume" in hits[0]["title"]
    assert document_agent.delete_document(hits[0]["id"]) is True


# ── Service: LLM paths (faked) ──────────────────────────────────────────

def test_ask_document_uses_llm(monkeypatch):
    from services import document_agent
    doc = document_agent.add_document("resume.txt", b"Java and Spring Boot experience")
    monkeypatch.setattr(document_agent, "_llm",
                        lambda system, user: "The candidate knows Java and Spring Boot.")
    answer = document_agent.ask_document(doc["id"], "What does the candidate know?")
    assert "Java" in answer


def test_summarize_document_uses_llm(monkeypatch):
    from services import document_agent
    doc = document_agent.add_document("notes.txt", b"Lots of content here.")
    monkeypatch.setattr(document_agent, "_llm", lambda system, user: "- Point one\n- Point two")
    summary = document_agent.summarize_document(doc["id"])
    assert "- Point one" in summary


def test_compare_needs_two(monkeypatch):
    from services import document_agent
    d1 = document_agent.add_document("a.txt", b"A content")
    monkeypatch.setattr(document_agent, "_llm", lambda system, user: "same")
    with pytest.raises(document_agent.DocumentUnavailableError):
        document_agent.compare_documents([d1["id"]])


def test_voice_handle_search_and_ask(monkeypatch):
    from services import document_agent
    document_agent.add_document("resume.txt", b"Java Spring Boot AWS")
    monkeypatch.setattr(document_agent, "ask_document", lambda did, q: f"ANSWER about {q}")
    reply = document_agent.handle_voice_request("ask my documents about java")
    assert "ANSWER about java" in reply

    reply2 = document_agent.handle_voice_request("search my documents for spring")
    assert "resume" in reply2


# ── Routes ───────────────────────────────────────────────────────────────

def test_documents_upload_requires_auth(remote_client):
    r = remote_client.post("/api/documents/upload",
                           files={"file": ("n.txt", b"hi", "text/plain")})
    assert r.status_code == 401


def test_documents_list_requires_auth(remote_client):
    r = remote_client.get("/api/documents")
    assert r.status_code == 401


def test_documents_upload_ok(client):
    r = client.post("/api/documents/upload",
                    files={"file": ("notes.txt", b"We discussed the roadmap", "text/plain")})
    assert r.status_code == 200
    assert r.json()["document"]["title"] == "notes"
    assert "roadmap" in r.json()["document"]["snippet"]


def test_documents_upload_oversized(client, monkeypatch):
    from routes import documents as docs_routes
    monkeypatch.setattr(docs_routes.document_agent, "MAX_UPLOAD_BYTES", 100)
    blob = b"x" * 200
    r = client.post("/api/documents/upload", files={"file": ("big.txt", blob, "text/plain")})
    assert r.status_code == 413


def test_documents_upload_unsupported(client):
    r = client.post("/api/documents/upload", files={"file": ("evil.exe", b"MZ", "application/octet-stream")})
    assert r.status_code == 400


def test_documents_ask_route(client, monkeypatch):
    from routes import documents as docs_routes
    doc = docs_routes.document_agent.add_document("resume.txt", b"Java Spring Boot")
    monkeypatch.setattr(docs_routes.document_agent, "ask_document",
                        lambda did, q: "Java and Spring Boot")
    r = client.post(f"/api/documents/{doc['id']}/ask", json={"question": "skills?"})
    assert r.status_code == 200
    assert "Java" in r.json()["answer"]


def test_documents_summarize_route(client, monkeypatch):
    from routes import documents as docs_routes
    doc = docs_routes.document_agent.add_document("n.txt", b"content")
    monkeypatch.setattr(docs_routes.document_agent, "summarize_document",
                        lambda did: "- Summary")
    r = client.post(f"/api/documents/{doc['id']}/summarize")
    assert r.status_code == 200
    assert r.json()["summary"] == "- Summary"


def test_documents_compare_route(client, monkeypatch):
    from routes import documents as docs_routes
    d1 = docs_routes.document_agent.add_document("a.txt", b"aaa")
    d2 = docs_routes.document_agent.add_document("b.txt", b"bbb")
    monkeypatch.setattr(docs_routes.document_agent, "compare_documents",
                        lambda ids: "- Similarities: both text")
    r = client.post("/api/documents/compare", json={"ids": [d1["id"], d2["id"]]})
    assert r.status_code == 200
    assert "Similarities" in r.json()["comparison"]


def test_documents_delete_route(client):
    from routes import documents as docs_routes
    doc = docs_routes.document_agent.add_document("n.txt", b"content")
    r = client.delete(f"/api/documents/{doc['id']}")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert docs_routes.document_agent.get_document(doc["id"]) is None
