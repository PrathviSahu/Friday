"""Shared pytest fixtures for the FRIDAY backend."""

import os
import sys
from pathlib import Path

# Ensure backend/ is importable when running `python -m pytest` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    """TestClient — its client host is 'testclient', treated as loopback."""
    from app import app
    return TestClient(app)


@pytest.fixture()
def remote_client(monkeypatch):
    """TestClient that looks like a NON-localhost caller (no auth)."""
    import auth
    monkeypatch.setattr(auth, "LOOPBACK_HOSTS", {"127.0.0.1", "::1", "localhost"})
    from app import app
    return TestClient(app)


@pytest.fixture()
def remote_client_with_token(monkeypatch):
    """Non-localhost caller presenting a valid FRIDAY_API_TOKEN."""
    import auth
    monkeypatch.setattr(auth, "LOOPBACK_HOSTS", {"127.0.0.1", "::1", "localhost"})
    monkeypatch.setenv("FRIDAY_API_TOKEN", "test_token_123")
    from app import app
    client = TestClient(app)
    client.headers.update({"X-FRIDAY-Token": "test_token_123"})
    return client
