"""scripts/benchmarks/common.py — Shared utilities, stats math, timeouts, and JSON persistence."""

import os
import sys
import json
import time
import math
import statistics
from pathlib import Path
from typing import List, Dict, Any, Callable

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

RESULTS_DIR = BASE_DIR / "benchmark_results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)



def calculate_stats(
    name: str,
    category: str,
    mode: str,
    latencies_ms: List[float],
    errors: int = 0,
    timeouts: int = 0
) -> Dict[str, Any]:
    """Calculate statistical percentiles and metadata."""
    n = len(latencies_ms)
    if n == 0:
        return {
            "name": name,
            "category": category,
            "mode": mode,
            "sample_count": 0,
            "min_ms": 0.0,
            "p50_ms": 0.0,
            "p95_ms": 0.0,
            "p99_ms": 0.0,
            "max_ms": 0.0,
            "mean_ms": 0.0,
            "stddev_ms": 0.0,
            "error_count": errors,
            "timeout_count": timeouts,
            "error_rate": 1.0 if (errors + timeouts) > 0 else 0.0,
            "timestamp": time.time(),
        }

    sorted_lats = sorted(latencies_ms)

    def percentile(p: float) -> float:
        k = (n - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_lats[int(k)]
        d0 = sorted_lats[int(f)] * (c - k)
        d1 = sorted_lats[int(c)] * (k - f)
        return d0 + d1

    total_attempts = n + errors + timeouts
    return {
        "name": name,
        "category": category,
        "mode": mode,
        "sample_count": n,
        "min_ms": round(sorted_lats[0], 2),
        "p50_ms": round(percentile(50.0), 2),
        "p95_ms": round(percentile(95.0), 2),
        "p99_ms": round(percentile(99.0), 2),
        "max_ms": round(sorted_lats[-1], 2),
        "mean_ms": round(statistics.mean(sorted_lats), 2),
        "stddev_ms": round(statistics.stdev(sorted_lats), 2) if n > 1 else 0.0,
        "error_count": errors,
        "timeout_count": timeouts,
        "error_rate": round((errors + timeouts) / total_attempts, 4) if total_attempts > 0 else 0.0,
        "timestamp": time.time(),
    }


def benchmark_call(
    name: str,
    category: str,
    mode: str,
    fn: Callable,
    iterations: int = 30,
    warmup: int = 2,
    timeout_sec: float = 3.0,
    *args, **kwargs
) -> Dict[str, Any]:
    """Execute a function across multiple iterations with per-iteration timeouts."""
    # Warmup
    for _ in range(warmup):
        try:
            fn(*args, **kwargs)
        except Exception:
            pass

    latencies = []
    errors = 0
    timeouts = 0

    for _ in range(iterations):
        t0 = time.perf_counter()
        try:
            # Execute with elapsed timing
            res = fn(*args, **kwargs)
            t1 = time.perf_counter()
            elapsed_ms = (t1 - t0) * 1000.0
            if (t1 - t0) > timeout_sec:
                timeouts += 1
            else:
                latencies.append(elapsed_ms)
        except Exception:
            errors += 1

    return calculate_stats(name, category, mode, latencies, errors=errors, timeouts=timeouts)


def save_batch_results(batch_name: str, results: List[Dict[str, Any]]) -> Path:
    """Save batch results to benchmark_results/<batch_name>.json."""
    out_path = RESULTS_DIR / f"{batch_name}.json"
    payload = {
        "batch": batch_name,
        "timestamp": time.time(),
        "measurements": results,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"✅ Saved {len(results)} measurements to {out_path}")
    return out_path
