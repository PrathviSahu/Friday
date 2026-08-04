"""Tests for Career OS data layer: at-rest encryption of sensitive fields."""

import pytest


@pytest.fixture()
def isolated_career_db(tmp_path, monkeypatch):
    """Point career_db at a throwaway DB + vault key file."""
    import services.career_db as db

    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test_brain.db")
    monkeypatch.setattr(db, "_VAULT_KEY_FILE", tmp_path / ".vault_key")
    monkeypatch.setattr(db, "_fernet", None)

    db.init_career_db()
    return db


def test_sensitive_fields_encrypted_at_rest(isolated_career_db):
    db = isolated_career_db

    db.upsert_profile_field("github_token", "ghp_supersecret123", is_sensitive=True)
    db.upsert_profile_field("full_name", "Prathvi Sahu", is_sensitive=False)

    # The raw DB must contain ciphertext, never the secret.
    raw = db._db().execute(
        "SELECT field, value FROM career_profile WHERE field IN ('github_token','full_name')"
    ).fetchall()
    stored = {r["field"]: r["value"] for r in raw}
    assert stored["github_token"].startswith("enc:v1:")
    assert "ghp_supersecret123" not in stored["github_token"]
    assert stored["full_name"] == "Prathvi Sahu"  # non-sensitive stays plaintext

    # The API-facing getter returns the decrypted value.
    profile = db.get_profile()
    assert profile["github_token"]["value"] == "ghp_supersecret123"
    assert profile["github_token"]["sensitive"] is True


def test_sensitive_hint_detection(isolated_career_db):
    db = isolated_career_db
    assert db._is_sensitive_field("linkedin_password") is True
    assert db._is_sensitive_field("openai_key") is True
    assert db._is_sensitive_field("github_token") is True
    assert db._is_sensitive_field("full_name") is False
    assert db._is_sensitive_field("preferred_role") is False


def test_legacy_plaintext_still_readable(isolated_career_db, monkeypatch, tmp_path):
    """Values written before encryption was enabled must still decrypt to themselves."""
    db = isolated_career_db
    # Simulate a pre-encryption row: plaintext value, sensitive flag set.
    with db._db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO career_profile (field, value, is_sensitive, updated_at) "
            "VALUES ('linkedin_password', 'old-plaintext-pw', 1, CURRENT_TIMESTAMP)"
        )
        conn.commit()

    profile = db.get_profile()
    assert profile["linkedin_password"]["value"] == "old-plaintext-pw"
