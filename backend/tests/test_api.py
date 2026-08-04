"""Security & correctness tests for the FRIDAY FastAPI app."""


def test_public_endpoint_open(client):
    """System stats (lock-screen poll) must work without auth."""
    r = client.get("/api/system/stats")
    assert r.status_code == 200


def test_remote_caller_rejected_without_token(remote_client):
    """A non-localhost caller must NOT be able to chat / control the machine."""
    r = remote_client.post("/api/chat/text", json={"text": "lock yourself"})
    assert r.status_code == 401

    r = remote_client.get("/api/career/preferences")
    assert r.status_code == 401

    r = remote_client.post("/api/system/display/lock")
    assert r.status_code == 401

    r = remote_client.get("/api/memory")
    assert r.status_code == 401


def test_remote_caller_with_token_allowed(remote_client_with_token):
    r = remote_client_with_token.get("/api/career/preferences")
    assert r.status_code == 200


def test_chat_accepts_no_is_boss_field(client):
    """is_boss must no longer be client-controlled; owner is derived server-side."""
    r = client.post("/api/chat/text", json={"text": "hello"})
    assert r.status_code == 200
    body = r.json()
    assert "reply" in body


def test_account_verify_is_honest(client):
    """No fabricated 'connected' response when no session is stored."""
    r = client.post("/api/career/accounts/verify/linkedin")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "needs_login"
    assert body["verified"] is False
    assert body["healthy"] is False


def test_tts_returns_relative_url(client, monkeypatch, tmp_path):
    """audio_url must be relative so any frontend host can resolve it."""
    fake = tmp_path / "abc.mp3"
    fake.write_bytes(b"fake-mp3")

    async def fake_generate_speech(text, output_dir, voice=None):
        return fake

    import routes.utilities as utilities_module
    monkeypatch.setattr(utilities_module, "generate_speech", fake_generate_speech)

    r = client.post("/api/tts", json={"text": "hello"})
    assert r.status_code == 200
    url = r.json()["audio_url"]
    assert url.startswith("/temp_audio/abc.mp3")
    assert "localhost" not in url


def test_resume_upload_size_cap(client):
    """Oversized uploads must be rejected (413), not buffered blindly."""
    blob = b"x" * (5 * 1024 * 1024 + 100)
    r = client.post(
        "/api/career/resumes/upload",
        files={"file": ("big.pdf", blob, "application/pdf")},
    )
    assert r.status_code == 413


def test_rate_limiter_sliding_window():
    from ratelimit import is_rate_limited
    ip = "203.0.113.7"
    results = [is_rate_limited(ip, limit=5, window=60) for _ in range(8)]
    assert results == [False] * 5 + [True] * 3
