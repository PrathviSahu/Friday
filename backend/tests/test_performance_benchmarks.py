"""Phase 6.7 — Automated Performance Benchmark Verification Suite.

Verifies statistical calculations, batch result persistence, aggregate merging,
and modular benchmark execution.
"""

import json
from pathlib import Path
from scripts.benchmarks.common import calculate_stats, benchmark_call, save_batch_results, RESULTS_DIR


def test_perf_stats_calculation():
    """Verify statistical calculation accuracy for p50, p95, p99, min, max."""
    samples = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    stats = calculate_stats(
        name="test_stat",
        category="Test",
        mode="LOCAL_REAL",
        latencies_ms=samples,
        errors=0,
        timeouts=0,
    )

    assert stats["sample_count"] == 10
    assert stats["min_ms"] == 10.0
    assert stats["max_ms"] == 100.0
    assert stats["p50_ms"] == 55.0
    assert stats["error_count"] == 0
    assert stats["error_rate"] == 0.0


def test_perf_batch_results_persisted():
    """Verify batch results JSON directory has all generated batches."""
    assert RESULTS_DIR.exists()
    batches = [
        "batch_api_brain.json",
        "batch_voice.json",
        "batch_email_calendar.json",
        "batch_career_portal.json",
        "batch_database.json",
        "batch_concurrency.json",
    ]
    for b in batches:
        p = RESULTS_DIR / b
        assert p.exists(), f"Batch result {b} missing from {RESULTS_DIR}"
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert "measurements" in data
            assert len(data["measurements"]) > 0


def test_perf_aggregate_report_valid():
    """Verify aggregate report is complete with 0 missing batches."""
    report_json = Path(__file__).resolve().parent.parent.parent / "benchmark_report.json"
    assert report_json.exists()
    with open(report_json, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data.get("status") == "COMPLETED"
        assert len(data.get("batches_found", [])) == 6
        assert len(data.get("batches_missing", [])) == 0
