"""scripts/benchmarks/aggregate.py — Consolidates batch results into report artifacts."""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = BASE_DIR / "benchmark_results"
REPORT_JSON = BASE_DIR / "benchmark_report.json"
REPORT_MD = BASE_DIR / "benchmark_report.md"

BATCHES = [
    "batch_api_brain",
    "batch_voice",
    "batch_email_calendar",
    "batch_career_portal",
    "batch_database",
    "batch_concurrency",
]


def generate_aggregate_report():
    aggregated = {
        "status": "COMPLETED",
        "batches_found": [],
        "batches_missing": [],
        "measurements": [],
        "concurrency": [],
    }

    for b in BATCHES:
        p = RESULTS_DIR / f"{b}.json"
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    aggregated["batches_found"].append(b)
                    if b == "batch_concurrency":
                        aggregated["concurrency"].extend(data.get("measurements", []))
                    else:
                        aggregated["measurements"].extend(data.get("measurements", []))
            except Exception as e:
                print(f"⚠️ Error loading {b}.json: {e}")
        else:
            aggregated["batches_missing"].append(b)

    # Write aggregate JSON
    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(aggregated, f, indent=2)
    print(f"✅ Wrote aggregate JSON report to {REPORT_JSON}")

    # Generate Markdown Report
    lines = [
        "# ⚡ F.R.I.D.A.Y. Phase 6.7 — Performance & Latency Benchmark Report",
        "",
        f"**Found Batches:** {len(aggregated['batches_found'])} / {len(BATCHES)}",
        f"**Missing Batches:** {', '.join(aggregated['batches_missing']) if aggregated['batches_missing'] else 'None'}",
        "",
        "## 1. Component Latency Distribution",
        "",
        "| Component / Subsystem | Category | Mode | p50 (ms) | p95 (ms) | p99 (ms) | Min (ms) | Max (ms) | Error Rate |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for m in aggregated["measurements"]:
        err_str = f"{m.get('error_rate', 0)*100:.1f}%"
        lines.append(
            f"| {m['name']} | {m['category']} | `{m['mode']}` | **{m['p50_ms']}** | {m['p95_ms']} | {m['p99_ms']} | {m['min_ms']} | {m['max_ms']} | {err_str} |"
        )

    lines.extend([
        "",
        "## 2. Concurrency & Throughput Scaling",
        "",
        "| Concurrency Workers | Total Requests | Throughput (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ])

    for c in aggregated["concurrency"]:
        lines.append(
            f"| {c['concurrency']} Workers | {c['sample_count']} | **{c['throughput_req_sec']}** | {c['p50_ms']} | {c['p95_ms']} | {c['p99_ms']} | {c['error_count']} |"
        )

    # Sort bottlenecks by p95 latency
    bottlenecks = sorted(aggregated["measurements"], key=lambda x: x["p95_ms"], reverse=True)
    top5 = bottlenecks[:5]

    lines.extend([
        "",
        "## 3. Top 5 Measured Latency Drivers & Bottlenecks",
        "",
        "| Rank | Component | Measured p95 | Target | Classification | Nature & Analysis |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ])

    for idx, b in enumerate(top5, 1):
        p95 = b["p95_ms"]
        severity = "P0" if p95 > 1000 else ("P1" if p95 > 250 else ("P2" if p95 > 50 else "P3"))
        lines.append(
            f"| #{idx} | {b['name']} | {p95}ms | <100ms | **{severity}** | {b['category']} ({b['mode']}) |"
        )

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"✅ Wrote aggregate Markdown report to {REPORT_MD}")


if __name__ == "__main__":
    generate_aggregate_report()
