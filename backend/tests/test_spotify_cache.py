import pytest
import json
import urllib.request
from pathlib import Path
from services import system_control


def test_spotify_cache_does_not_deadlock(tmp_path, monkeypatch):
    # Setup temporary cache file path
    temp_cache_file = tmp_path / "spotify_cache_test.json"
    monkeypatch.setattr(system_control, "SPOTIFY_CACHE_FILE", temp_cache_file)

    # 1. Test saving cache works without deadlocking
    test_data = {"test_query": "spotify:track:12345"}
    system_control._save_spotify_cache(test_data)

    # 2. Test loading cache works without deadlocking
    loaded = system_control._load_spotify_cache()
    assert loaded == test_data

    # 3. Test nested locking works (which previously deadlocked with Lock)
    with system_control._spotify_cache_lock:
        # Since _spotify_cache_lock is now an RLock, these calls inside the lock block should succeed!
        inner_loaded = system_control._load_spotify_cache()
        assert inner_loaded == test_data

        test_data_nested = {
            "test_query": "spotify:track:12345",
            "another": "spotify:track:67890",
        }
        system_control._save_spotify_cache(test_data_nested)

    final_loaded = system_control._load_spotify_cache()
    assert final_loaded == test_data_nested


def test_spotify_current_track_web_empty(monkeypatch):
    from services.system_control import _get_spotify_current_track_web

    # Mock token
    monkeypatch.setattr(
        "services.system_control._get_spotify_access_token", lambda: "fake_token"
    )

    # Mock urlopen returning 204
    class MockResponse:
        def __init__(self, status):
            self.status = status

        def read(self):
            return b""

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    def fake_urlopen(req, timeout=5):
        return MockResponse(204)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    res = _get_spotify_current_track_web()
    assert res == {}


def test_spotify_current_track_web_playing(monkeypatch):
    from services.system_control import _get_spotify_current_track_web

    # Mock token
    monkeypatch.setattr(
        "services.system_control._get_spotify_access_token", lambda: "fake_token"
    )

    track_json = {
        "is_playing": True,
        "progress_ms": 50000,
        "device": {"volume_percent": 85},
        "item": {
            "name": "Kesariya",
            "duration_ms": 200000,
            "type": "track",
            "artists": [{"name": "Arijit Singh"}],
            "album": {
                "name": "Brahmastra",
                "images": [{"url": "https://example.com/art.jpg"}],
            },
        },
    }

    class MockResponse200:
        def __init__(self):
            self.status = 200

        def read(self):
            return json.dumps(track_json).encode()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr(
        urllib.request, "urlopen", lambda req, timeout=5: MockResponse200()
    )

    res = _get_spotify_current_track_web()
    assert res["playing"] is True
    assert res["title"] == "Kesariya"
    assert res["artist"] == "Arijit Singh"
    assert res["album"] == "Brahmastra"
    assert res["artwork_url"] == "https://example.com/art.jpg"
    assert res["position"] == 50
    assert res["duration"] == 200
    assert res["volume"] == 85
