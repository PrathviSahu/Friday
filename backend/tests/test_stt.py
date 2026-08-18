"""Tests for the server-side STT endpoint (Groq Whisper free tier + fallback).

The real Groq/Gemini clients are never invoked — provider functions are
monkeypatched so tests stay offline and free.
"""

import pytest


def test_stt_public_demo_accessible(remote_client, monkeypatch):
    """Public demo callers can transcribe speech without a token (mocked STT)."""
    monkeypatch.setattr("routes.chat.transcribe_audio", lambda data, fn, mt: {"transcript": "hello friday", "engine": "groq"})
    r = remote_client.post(
        "/api/speech/transcribe",
        files={"audio": ("clip.ogg", b"fake-audio", "audio/ogg")},
    )
    assert r.status_code == 200
    assert r.json()["transcript"] == "hello friday"


def test_stt_oversized_upload_rejected(client):
    """Oversized clips must be rejected (413), matching Groq's cap guard."""
    blob = b"\x00" * (10 * 1024 * 1024 + 1)
    r = client.post(
        "/api/speech/transcribe",
        files={"audio": ("big.webm", blob, "audio/webm")},
    )
    assert r.status_code == 413


def test_stt_empty_upload_rejected(client):
    r = client.post(
        "/api/speech/transcribe",
        files={"audio": ("clip.ogg", b"", "audio/ogg")},
    )
    assert r.status_code == 400


def test_stt_transcribes_and_applies_personal_corrections(client, monkeypatch):
    """The endpoint returns the transcript and runs it through the
    personal vocabulary engine (saved 'No, I meant X' corrections)."""
    import routes.chat as chat_module

    def fake_transcribe(audio_bytes, filename, mime_type):
        return {"transcript": "help away by temper city", "language": "en", "source": "groq"}

    monkeypatch.setattr(chat_module, "transcribe_audio", fake_transcribe)

    # Record a permanent correction first
    r = client.post(
        "/api/speech/correct",
        json={"original_text": "temper city", "corrected_text": "Temper City"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    r = client.post(
        "/api/speech/transcribe",
        files={"audio": ("clip.ogg", b"fake-audio", "audio/ogg")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "groq"
    assert body["language"] == "en"
    assert body["transcript"] == "help away by Temper City"


def test_stt_unavailable_returns_503(client, monkeypatch):
    """When every provider fails, the client gets a clean 503."""
    import routes.chat as chat_module

    def boom(audio_bytes, filename, mime_type):
        raise chat_module.STTUnavailableError("GROQ_API_KEY is not configured; GEMINI_API_KEY is not configured")

    monkeypatch.setattr(chat_module, "transcribe_audio", boom)

    r = client.post(
        "/api/speech/transcribe",
        files={"audio": ("clip.ogg", b"fake-audio", "audio/ogg")},
    )
    assert r.status_code == 503
    assert "GROQ_API_KEY" in r.json()["detail"]


# ── Service-level tests ──────────────────────────────────────────────────


def test_stt_service_groq_then_gemini_fallback(monkeypatch):
    """Groq failure must fall through to Gemini and report its source."""
    import services.stt as stt_module

    calls = []

    def fake_groq(audio_bytes, filename, mime_type):
        calls.append("groq")
        raise RuntimeError("groq down")

    def fake_gemini(audio_bytes, filename, mime_type):
        calls.append("gemini")
        return {"transcript": "hello boss", "language": "auto", "source": "gemini"}

    monkeypatch.setattr(stt_module, "_transcribe_groq", fake_groq)
    monkeypatch.setattr(stt_module, "_transcribe_gemini", fake_gemini)

    result = stt_module.transcribe_audio(b"abc", "clip.ogg", "audio/ogg")
    assert calls == ["groq", "gemini"]
    assert result["transcript"] == "hello boss"
    assert result["source"] == "gemini"


def test_stt_service_skips_gemini_when_groq_succeeds(monkeypatch):
    import services.stt as stt_module

    def fake_groq(audio_bytes, filename, mime_type):
        return {"transcript": "play kesariya", "language": "hi", "source": "groq"}

    def fake_gemini(audio_bytes, filename, mime_type):
        raise AssertionError("Gemini must not be called when Groq succeeds")

    monkeypatch.setattr(stt_module, "_transcribe_groq", fake_groq)
    monkeypatch.setattr(stt_module, "_transcribe_gemini", fake_gemini)

    result = stt_module.transcribe_audio(b"abc", "clip.ogg", "audio/ogg")
    assert result["transcript"] == "play kesariya"
    assert result["source"] == "groq"


def test_stt_service_all_providers_fail(monkeypatch):
    import services.stt as stt_module

    def fail(*args, **kwargs):
        raise RuntimeError("nope")

    monkeypatch.setattr(stt_module, "_transcribe_groq", fail)
    monkeypatch.setattr(stt_module, "_transcribe_gemini", fail)

    with pytest.raises(stt_module.STTUnavailableError):
        stt_module.transcribe_audio(b"abc", "clip.ogg", "audio/ogg")


def test_stt_service_rejects_empty_audio(monkeypatch):
    import services.stt as stt_module

    with pytest.raises(stt_module.STTUnavailableError):
        stt_module.transcribe_audio(b"", "clip.ogg", "audio/ogg")


# ── Personal vocabulary engine ───────────────────────────────────────────


def test_personal_vocabulary_roundtrip():
    """record_correction → apply_corrections must rewrite future transcripts."""
    from speech.personal_vocabulary import PersonalVocabularyEngine

    engine = PersonalVocabularyEngine()
    assert engine.record_correction("temper city", "Temper City") is True
    assert engine.apply_corrections("play temper city now") == "play Temper City now"
