"""devtools.py — Developer Mode helpers (v3.2).

A ring-buffer log handler captures app logging so the HUD Developer panel can
tail logs without touching disk; `get_log_tail` prefers the on-disk log files
written by start.sh and falls back to the ring buffer.
"""

import logging
import threading
import time
from collections import deque
from pathlib import Path

_START_TIME = time.time()


class RingBufferHandler(logging.Handler):
    def __init__(self, capacity: int = 1500):
        super().__init__()
        self.buf = deque(maxlen=capacity)
        self._lock = threading.Lock()

    def emit(self, record):
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        with self._lock:
            self.buf.append(
                f"{time.strftime('%H:%M:%S')} [{record.levelname}] {msg}")

    def tail(self, n: int) -> list:
        with self._lock:
            return list(self.buf)[-n:]


_ring = RingBufferHandler()
_ring.setFormatter(logging.Formatter("%(name)s: %(message)s"))
# Attach once (guards against reloader double-adding)
if _ring not in logging.getLogger().handlers:
    logging.getLogger().addHandler(_ring)
for _name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    lg = logging.getLogger(_name)
    if _ring not in lg.handlers:
        lg.addHandler(_ring)


def _log_file_candidates() -> list:
    base = Path(__file__).parent.parent            # backend/
    return [
        base / "backend.log",                      # legacy direct-run log
        base.parent / "logs" / "backend.log",      # start.sh log
    ]


def get_log_tail(n: int = 200) -> list:
    """Return the most recent log lines (file first, ring buffer fallback)."""
    for path in _log_file_candidates():
        try:
            if path.exists():
                lines = path.read_text(errors="ignore").splitlines()
                if lines:
                    return lines[-n:]
        except OSError:
            continue
    return _ring.tail(n)


def get_uptime_seconds() -> int:
    return int(time.time() - _START_TIME)
