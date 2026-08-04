"""ratelimit.py — small in-process sliding-window rate limiter (per IP).

Used to protect the LLM-backed endpoints (Groq/Gemini calls cost API
credits). A background eviction pass prunes stale entries so the store does
not grow unboundedly across many unique client IPs.
"""

import threading
import time

from fastapi import Request, HTTPException

DEFAULT_LIMIT = 30   # max requests
DEFAULT_WINDOW = 60  # per N seconds

_store: dict = {}
_lock = threading.Lock()
_last_evict = [0.0]


def _evict(now: float) -> None:
    """Periodically drop expired timestamps (runs at most every 30 s)."""
    if now - _last_evict[0] < 30:
        return
    _last_evict[0] = now
    for ip in list(_store):
        keep = [t for t in _store[ip] if now - t < DEFAULT_WINDOW]
        if keep:
            _store[ip] = keep
        else:
            _store.pop(ip, None)


def is_rate_limited(ip: str, limit: int = DEFAULT_LIMIT,
                    window: float = DEFAULT_WINDOW) -> bool:
    """Return True when `ip` has exceeded `limit` requests in `window` seconds.

    Records the current request when it is allowed.
    """
    now = time.time()
    with _lock:
        _evict(now)
        timestamps = [t for t in _store.get(ip, []) if now - t < window]
        if len(timestamps) >= limit:
            _store[ip] = timestamps
            return True
        timestamps.append(now)
        _store[ip] = timestamps
        return False


def rate_limit(limit: int = DEFAULT_LIMIT, window: float = DEFAULT_WINDOW):
    """Factory producing a FastAPI dependency that 429s when the IP is over.

    Usage:  dependencies=[Depends(rate_limit(limit=20, window=60))]
    """
    def dependency(request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        if is_rate_limited(ip, limit, window):
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please slow down — even FRIDAY needs a breather!",
            )
    return dependency
