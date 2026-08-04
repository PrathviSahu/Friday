"""services/metrics.py — lightweight in-process performance metrics.

Records operation timings (LLM calls, STT, TTS, tool dispatch) into a small
ring buffer and exposes recent samples + averages for the Dev Dashboard.
Thread-safe; never raises — instrumentation must never break a request.
"""

import threading
import time
from collections import deque
from functools import wraps

MAX_SAMPLES = 200
_samples: deque = deque(maxlen=MAX_SAMPLES)
_lock = threading.Lock()

_last = {
    "agent": "",
    "tool": "",
    "action": "none",
}


def record(op: str, ms: float, meta: str = "") -> None:
    """Record one timing sample."""
    try:
        with _lock:
            _samples.append({
                "op": str(op)[:40],
                "ms": round(float(ms), 1),
                "meta": str(meta)[:80],
                "ts": time.time(),
            })
    except Exception:
        pass


class timed:
    """Context manager / decorator: records elapsed ms of the wrapped block.

    Usage:
        with timed("llm", meta=model): ...
        @timed("stt")
        def transcribe(...): ...
    """

    def __init__(self, op: str, meta: str = ""):
        self.op = op
        self.meta = meta

    def __call__(self, fn):
        import inspect

        if inspect.iscoroutinefunction(fn):
            @wraps(fn)
            async def async_wrapper(*args, **kwargs):
                start = time.perf_counter()
                try:
                    return await fn(*args, **kwargs)
                finally:
                    record(self.op, (time.perf_counter() - start) * 1000, self.meta)
            return async_wrapper

        @wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                record(self.op, (time.perf_counter() - start) * 1000, self.meta)
        return wrapper

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        record(self.op, (time.perf_counter() - self._start) * 1000, self.meta)
        return False


def set_last(agent: str = "", tool: str = "", action: str = "") -> None:
    """Track the most recently used agent / tool / action."""
    try:
        with _lock:
            if agent:
                _last["agent"] = str(agent)[:40]
            if tool:
                _last["tool"] = str(tool)[:40]
            if action:
                _last["action"] = str(action)[:40]
    except Exception:
        pass


def snapshot() -> dict:
    """Recent samples + per-op averages + last agent/tool/action."""
    try:
        with _lock:
            samples = list(_samples)
            last = dict(_last)
    except Exception:
        return {"samples": [], "averages": {}, "last": {}}

    totals: dict = {}
    for s in samples:
        t = totals.setdefault(s["op"], {"count": 0, "total_ms": 0.0, "last_ms": 0.0})
        t["count"] += 1
        t["total_ms"] += s["ms"]
        t["last_ms"] = s["ms"]

    averages = {
        op: {
            "count": t["count"],
            "avg_ms": round(t["total_ms"] / t["count"], 1),
            "last_ms": t["last_ms"],
        }
        for op, t in totals.items()
    }
    return {
        "samples": list(reversed(samples[-40:])),  # newest first
        "averages": averages,
        "last": last,
    }


def reset() -> None:
    with _lock:
        _samples.clear()
