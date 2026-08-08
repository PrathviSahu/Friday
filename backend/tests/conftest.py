"""Shared pytest fixtures for the FRIDAY backend.

Every service writes to a throwaway SQLite file under tmp_path_factory so
tests never pollute the real `data/friday_brain.db` (notifications, learning
logs, timeline events, notes, goals from tests used to leak into the user's
actual database).
"""

import os
import sys
from pathlib import Path

# Ensure backend/ is importable when running `python -m pytest` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

# Modules that hold a DB_PATH / DB_FILE module-global read at connect-time,
# plus the init function to (re)run so the redirected temp DB gets its tables.
_DB_MODULES = [
    ("services.knowledge", "init_knowledge_db"),
    ("services.timeline", "init_timeline_db"),
    ("services.goals", "init_goals_db"),
    ("services.learning", "init_learning_db"),
    ("services.life_memory", "init_life_memory_db"),
    ("services.notifications", "init_notifications_db"),
    ("services.permissions", "init_permissions_db"),
    ("services.automation", "init_automations_db"),
    ("services.learning_engine", "init_brain_db"),
    ("services.autonomy_engine", "init_autonomy_db"),
    ("services.memory_consolidator", "init_consolidator_db"),
    ("services.career_db", "init_career_db"),
    ("services.platform_session", "init_session_db"),
    ("services.meeting_agent", "init_meetings_db"),
    ("services.document_agent", "init_documents_db"),
    ("services.embeddings", "init_embeddings_db"),
    ("database.watchlist_db", "init_watchlist_table"),
    ("database.chart_db", "init_trading_db"),
    ("database.connection", None),  # holds DB_PATH used by speech/personal_vocabulary
]


@pytest.fixture(scope="session", autouse=True)
def _isolate_databases(tmp_path_factory):
    """Redirect every SQLite path to a temp dir for the whole test session.

    Module imports run init_*_db() immediately, so after redirecting the path
    globals we re-run the init functions against the temp DB to create tables
    there. The real data/friday_brain.db is never written by tests.
    """
    tmp = tmp_path_factory.mktemp("friday_test_db")
    for mod_name, init_fn in _DB_MODULES:
        try:
            mod = __import__(mod_name, fromlist=["x"])
            for attr in ("DB_PATH", "DB_FILE"):
                if hasattr(mod, attr):
                    setattr(mod, attr, tmp / f"{mod_name.rsplit('.', 1)[-1]}.sqlite")
            if init_fn and hasattr(mod, init_fn):
                getattr(mod, init_fn)()
        except ImportError:
            pass
    yield tmp


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
