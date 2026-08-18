"""routes/spotify.py — Spotify playback control & telemetry."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import require_boss, require_public_demo
from services.system_control import (
    get_spotify_current_track,
    set_spotify_position,
    duck_spotify_volume,
    unduck_spotify_volume,
)

router = APIRouter(prefix="/api", tags=["spotify"])


class SpotifySeekRequest(BaseModel):
    seconds: float


@router.get("/spotify/current-track", dependencies=[Depends(require_public_demo)])
def get_spotify_track_endpoint():
    """Retrieve details of currently playing track on Spotify"""
    return get_spotify_current_track()


@router.post("/spotify/seek", dependencies=[Depends(require_boss)])
def spotify_seek_endpoint(req: SpotifySeekRequest):
    """Seek to specific position in currently playing Spotify track"""
    ok = set_spotify_position(req.seconds)
    return {"status": "ok" if ok else "error"}


@router.post("/spotify/duck", dependencies=[Depends(require_boss)])
def spotify_duck_endpoint():
    """Lower Spotify volume while FRIDAY is speaking."""
    ok = duck_spotify_volume()
    return {"status": "ok" if ok else "ignored"}


@router.post("/spotify/unduck", dependencies=[Depends(require_boss)])
def spotify_unduck_endpoint():
    """Restore Spotify volume after FRIDAY finishes speaking."""
    ok = unduck_spotify_volume()
    return {"status": "ok" if ok else "ignored"}

