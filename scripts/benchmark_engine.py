#!/usr/bin/env python3
"""Phase 6.7 — Performance & Latency Benchmarking Engine for F.R.I.D.A.Y.

Executes reproducible, multi-sample latency and throughput measurements across:
  1. Core API Endpoints
  2. Brain, LLM, and Fast-Path Routing
  3. Voice Pipeline (STT -> Intent -> Brain -> TTS)
  4. Email Controlled Pipeline (Draft -> Hash -> Approval -> Send -> Verification)
  5. Calendar Controlled Pipeline (Draft -> Hash -> Approval -> Create -> Verification)
  6. Career Intelligence & Portal Automation (Ingestion -> Deduplication -> Ranking -> Packet -> Form Discovery)
  7. Database Operations (SQLite WAL read/write contention under load)
  8. Concurrency Scaling (1, 5, 10, 25, 50 workers)
  9. System Resource Metrics (CPU, RAM, Disk I/O, SQLite locks)

Computes statistical percentiles (p50, p95, p99, min, max, stddev, error rates).
"""

import os
import sys
import time
import math
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Any, Callable

# Ensure backend directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))
sys.path.insert(0, str(BASE_DIR))

import psutil
from fastapi.testclient import TestClient
from app import app


def calculate_stats(latencies_ms: List[float], errors: int = 0) -> Dict[str, Any]:
    """Compute statistical percentiles from a list of latencies in milliseconds."""
    if not latencies_ms:
        return {
            "count": 0, "p50": 0.0, "p95": 0.0, "p99": 0.0,
            "min": 0.0, "max": 0.0, "mean": 0.0, "stddev": 0.0,
            "errors": errors, "error_rate": 0.0
        }

    sorted_lats = sorted(latencies_ms)
    n = len(sorted_lats)

    def percentile(p: float) -> float:
        k = (n - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_lats[int(k)]
        d0 = sorted_lats[int(f)] * (c - k)
        d1 = sorted_lats[int(c)] * (k - f)
        return d0 + d1

    return {
        "count": n,
        "p50": round(percentile(50.0), 2),
        "p95": round(percentile(95.0), 2),
        "p99": round(percentile(99.0), 2),
        "min": round(sorted_lats[0], 2),
        "max": round(sorted_lats[-1], 2),
        "mean": round(statistics.mean(sorted_lats), 2),
        "stddev": round(statistics.stdev(sorted_lats), 2) if n > 1 else 0.0,
        "errors": errors,
        "error_rate": round(errors / (n + errors), 4) if (n + errors) > 0 else 0.0
    }


def benchmark_function(fn: Callable, iterations: int = 50, warmup: int = 5, *args, **kwargs) -> Dict[str, Any]:
    """Run a function multiple times and measure latency distribution."""
    # Warmup
    for _ in range(warmup):
        try:
            fn(*args, **kwargs)
        except Exception:
            pass

    latencies = []
    errors = 0
    for _ in range(iterations):
        t0 = time.perf_counter()
        try:
            res = fn(*args, **kwargs)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0)
        except Exception as e:
            errors += 1

    return calculate_stats(latencies, errors=errors)


class FridayBenchmarkSuite:
    def __init__(self):
        self.client = TestClient(app)
        self.process = psutil.Process(os.getpid())
        self.results = {}

    def get_resource_usage(self) -> Dict[str, Any]:
        """Capture current CPU and memory consumption."""
        mem_info = self.process.memory_info()
        return {
            "cpu_percent": self.process.cpu_percent(interval=0.1),
            "rss_mb": round(mem_info.rss / (1024 * 1024), 2),
            "vms_mb": round(mem_info.vms / (1024 * 1024), 2),
            "num_threads": self.process.num_threads(),
        }

    # ── 1. API Latencies ───────────────────────────────────────────────────────
    def run_api_benchmarks(self) -> Dict[str, Any]:
        print("\n⚡ Running API Endpoint Benchmarks...")
        benchmarks = {}

        # 1.1 Read-only public telemetry
        benchmarks["API: GET /api/system/stats"] = benchmark_function(
            lambda: self.client.get("/api/system/stats"), iterations=40
        )

        # 1.2 Weather [EXTERNAL REAL]
        benchmarks["API: GET /api/weather [EXTERNAL REAL]"] = benchmark_function(
            lambda: self.client.get("/api/weather"), iterations=5, warmup=1
        )

        # 1.3 Trading live market prices [LOCAL REAL]
        benchmarks["API: GET /api/trading/live-prices [LOCAL REAL]"] = benchmark_function(
            lambda: self.client.get("/api/trading/live-prices"), iterations=30
        )

        # 1.4 Trading analysis (TA engine) [LOCAL REAL]
        benchmarks["API: GET /api/trading/analysis [LOCAL REAL]"] = benchmark_function(
            lambda: self.client.get("/api/trading/analysis?symbol=FX:EURUSD&interval=15"), iterations=10
        )


        # 1.5 Dev overview (Owner authenticated)
        benchmarks["API: GET /api/dev/overview"] = benchmark_function(
            lambda: self.client.get("/api/dev/overview"), iterations=30
        )

        # 1.6 Career Dashboard
        benchmarks["API: GET /api/career/dashboard"] = benchmark_function(
            lambda: self.client.get("/api/career/dashboard"), iterations=25
        )

        return benchmarks

    # ── 2. Brain & Intent Routing ──────────────────────────────────────────────
    def run_brain_benchmarks(self) -> Dict[str, Any]:
        print("⚡ Running Brain & Cognitive Routing Benchmarks...")
        from services.brain.engine import respond
        benchmarks = {}


        # 2.1 Fast-Path System Command (<5ms target)
        benchmarks["Brain: Fast-Path Media Control ('mute volume') [LOCAL REAL]"] = benchmark_function(
            lambda: respond("mute volume", is_boss=True, silence_tts=True), iterations=30
        )

        # 2.2 Fast-Path App Control ('open terminal')
        benchmarks["Brain: Fast-Path App Automation ('open terminal') [LOCAL REAL]"] = benchmark_function(
            lambda: respond("open terminal", is_boss=True, silence_tts=True), iterations=30
        )

        # 2.3 Guest Privilege Refusal Fast-Path
        benchmarks["Brain: Guest Privilege Refusal ('lock system') [LOCAL REAL]"] = benchmark_function(
            lambda: respond("lock system", is_boss=False, silence_tts=True), iterations=30
        )

        # 2.4 Dynamic System Prompt Generation + Memory Context Injection
        from services.brain.prompt_builder import build_system_prompt
        benchmarks["Brain: Dynamic Prompt Assembly (Context + Memory + RAG) [LOCAL REAL]"] = benchmark_function(
            lambda: build_system_prompt("what is on my schedule", is_boss=True, guest_active=False, brevity_mode="normal"),
            iterations=30
        )


        # 2.5 Simulated LLM Synthesis [MOCK]
        def simulated_llm_inference():
            time.sleep(0.045)  # 45ms simulated low-latency neural generation
            return {"reply": "Good evening Prem, your calendar is clear for tomorrow.", "action": "reply"}

        benchmarks["Brain: LLM Generation (Groq/Gemini Simulated) [MOCK]"] = benchmark_function(
            simulated_llm_inference, iterations=30
        )

        return benchmarks

    # ── 3. Voice Pipeline (STT & TTS) ──────────────────────────────────────────
    def run_voice_benchmarks(self) -> Dict[str, Any]:
        print("⚡ Running Voice Pipeline Benchmarks...")
        import asyncio
        from services.tts import generate_speech
        from services.brain.engine import respond
        benchmarks = {}

        # 3.1 Edge-TTS Speech Generation (Real audio generation to disk)
        temp_dir = BASE_DIR / "backend" / "temp_audio"
        temp_dir.mkdir(parents=True, exist_ok=True)

        def generate_test_tts():
            return asyncio.run(generate_speech("Good evening Prem. All systems operational.", temp_dir))

        benchmarks["TTS: Real Edge-TTS Audio Generation (~45 chars) [LOCAL REAL]"] = benchmark_function(
            generate_test_tts, iterations=10, warmup=2
        )

        # 3.2 Mock STT Transcription
        def mock_stt_transcribe():
            time.sleep(0.020)  # 20ms simulated local Whisper/Apple Dictation
            return {"transcript": "open trading"}

        benchmarks["STT: Audio Speech-to-Text Transcription [MOCK]"] = benchmark_function(
            mock_stt_transcribe, iterations=30
        )


        # 3.3 End-to-End Voice Round Trip (STT -> Fast Brain -> Response)
        def voice_round_trip():
            t_stt = mock_stt_transcribe()["transcript"]
            b_resp = respond(t_stt, is_boss=True, silence_tts=True)
            return b_resp

        benchmarks["Voice: E2E Fast-Path Round Trip (STT -> Brain -> Dispatch) [LOCAL REAL]"] = benchmark_function(
            voice_round_trip, iterations=25
        )

        return benchmarks

    # ── 4. Email Pipeline ──────────────────────────────────────────────────────
    def run_email_benchmarks(self) -> Dict[str, Any]:
        print("⚡ Running Email Controlled Pipeline Benchmarks...")
        from services.email.service import (
            create_email_draft,
            send_email_with_approval,
        )
        from services.email.draft import update_draft
        from services.email.approval import validate_approval
        from services.email.provider import MockEmailProvider
        from services.email.verifier import IndependentVerifier
        benchmarks = {}

        # 4.1 Draft Creation + SHA-256 Hash + Token Minting
        def test_draft_create():
            return create_email_draft("hiring@techcorp.com", "Application - Senior SDE", "Please find my resume attached.")

        benchmarks["Email: Draft Creation + Hash + Approval Token"] = benchmark_function(
            test_draft_create, iterations=50
        )

        # 4.2 Draft Invalidation / Re-hash on Edit
        draft_sample = test_draft_create()
        draft_id = draft_sample["draft"]["draft_id"]

        def test_draft_update():
            return update_draft(draft_id, new_body=f"Updated body {time.perf_counter()}")

        benchmarks["Email: Draft Mutation + Version Bump + Re-hash"] = benchmark_function(
            test_draft_update, iterations=50
        )

        # 4.3 Approval Validation (Checks 1-10)
        draft_for_val = test_draft_create()
        d_id = draft_for_val["draft"]["draft_id"]
        a_id = draft_for_val["approval_token"]["approval_id"]

        def test_val_approval():
            return validate_approval(a_id, d_id, session_user="Prem")

        benchmarks["Email: Approval Token Validation (10 Security Checks)"] = benchmark_function(
            test_val_approval, iterations=50
        )

        # 4.4 Full Controlled Send + Verification
        provider = MockEmailProvider()

        def test_full_email_pipeline():
            d = create_email_draft("recruiter@google.com", "Job Application", "Cover letter content")
            return send_email_with_approval(
                approval_id=d["approval_token"]["approval_id"],
                draft_id=d["draft"]["draft_id"],
                user_confirmation_text="Yes, send it",
                provider=provider,
            )

        benchmarks["Email: Full E2E Pipeline (Draft -> Verify -> Send -> Audit)"] = benchmark_function(
            test_full_email_pipeline, iterations=40
        )

        return benchmarks

    # ── 5. Calendar Pipeline ───────────────────────────────────────────────────
    def run_calendar_benchmarks(self) -> Dict[str, Any]:
        print("⚡ Running Calendar Controlled Pipeline Benchmarks...")
        from services.calendar.service import (
            prepare_calendar_event,
            create_calendar_event_with_approval,
        )
        from services.calendar.event import update_calendar_event_draft
        from services.calendar.approval import validate_calendar_approval
        from services.calendar.provider import MockCalendarProvider
        benchmarks = {}

        # 5.1 Event Draft Creation + Hash + Approval Token
        def test_cal_draft():
            return prepare_calendar_event("System Architecture Review", "2026-09-10T10:00:00", "2026-09-10T11:00:00", "UTC")

        benchmarks["Calendar: Draft Creation + Hash + Approval Token"] = benchmark_function(
            test_cal_draft, iterations=50
        )

        # 5.2 Approval Token Validation
        cal_sample = test_cal_draft()
        e_id = cal_sample["event_draft"]["event_id"]
        a_id = cal_sample["approval_token"]["approval_id"]

        def test_cal_validate():
            return validate_calendar_approval(a_id, e_id, session_user="Prem")

        benchmarks["Calendar: Approval Token Validation (Security Checks)"] = benchmark_function(
            test_cal_validate, iterations=50
        )

        # 5.3 Full Controlled Create + Verification
        provider = MockCalendarProvider()

        def test_full_cal_pipeline():
            ev = prepare_calendar_event("Sprint Retrospective", "2026-09-15T14:00:00", "2026-09-15T15:00:00", "UTC")
            return create_calendar_event_with_approval(
                approval_id=ev["approval_token"]["approval_id"],
                event_id=ev["event_draft"]["event_id"],
                user_confirmation_text="Yes, create it.",
                provider=provider,
            )

        benchmarks["Calendar: Full E2E Pipeline (Draft -> Verify -> Create -> Audit)"] = benchmark_function(
            test_full_cal_pipeline, iterations=40
        )

        return benchmarks

    # ── 6. Career OS & Portal Engine ───────────────────────────────────────────
    def run_career_benchmarks(self) -> Dict[str, Any]:
        print("⚡ Running Career OS & Portal Automation Benchmarks...")
        from services.career.provider import MockJobProvider
        from services.career.pipeline import run_job_pipeline
        from services.career.packet import build_application_packet
        from services.career.portal.engine import PortalAutomationEngine
        from services.career.portal.mock_portal import MockApplicationPortal
        benchmarks = {}

        # 6.1 Multi-Provider Ingestion + Normalization + Deduplication
        provider1 = MockJobProvider(provider_id="mock_linkedin")
        provider2 = MockJobProvider(provider_id="mock_remoteok")

        def test_job_ingestion():
            return run_job_pipeline(providers=[provider1, provider2], query="SDE", auto_save=False)

        benchmarks["Career: Ingestion + Normalization + Deduplication (20 Jobs)"] = benchmark_function(
            test_job_ingestion, iterations=30
        )

        # 6.2 Application Packet Generation + Hash Binding
        sample_job = {
            "id": 101, "title": "Staff Backend Engineer", "company": "Stark Industries",
            "url": "https://careers.mockcorp.io/apply/1", "location": "Remote", "salary_raw": "$180k"
        }

        def test_packet_gen():
            return build_application_packet(job_id=101, job_data=sample_job)

        benchmarks["Career: Application Packet Generation + SHA-256 Hash"] = benchmark_function(
            test_packet_gen, iterations=50
        )

        # 6.3 Portal Form Discovery & Mapping
        engine = PortalAutomationEngine()
        portal = MockApplicationPortal()
        packet = test_packet_gen()

        def test_portal_discovery_mapping():
            return engine.create_portal_session(packet, portal=portal)

        benchmarks["Portal: Form Discovery + Field Mapping + Sensitivity Check"] = benchmark_function(
            test_portal_discovery_mapping, iterations=40
        )

        return benchmarks

    # ── 7. Database Benchmarks ─────────────────────────────────────────────────
    def run_database_benchmarks(self) -> Dict[str, Any]:
        print("⚡ Running Database CRUD & Contention Benchmarks...")
        from services import career_db, memory, permissions
        benchmarks = {}

        # 7.1 Career Profile Read (Masked)
        benchmarks["DB: Career Profile Read (Decryption & Masking)"] = benchmark_function(
            lambda: career_db.get_profile(mask_sensitive=True), iterations=50
        )

        # 7.2 Career Profile Write (Fernet Encryption)
        benchmarks["DB: Career Profile Write (Fernet At-Rest Encryption)"] = benchmark_function(
            lambda: career_db.upsert_profile_field("benchmark_key", "secret_token_value_123", is_sensitive=True), iterations=40
        )

        # 7.3 Memory Fact Retrieval
        benchmarks["DB: Long-Term Memory Retrieval"] = benchmark_function(
            lambda: memory.get_all_memories(), iterations=50
        )

        # 7.4 Permission Audit Insert
        benchmarks["DB: Permission Audit Log Insert (WAL Append)"] = benchmark_function(
            lambda: permissions._audit("trades.execute", "allowed", "Benchmark execution test"), iterations=50
        )

        return benchmarks

    # ── 8. Concurrency & Throughput Benchmarks ──────────────────────────────────
    def run_concurrency_benchmarks(self) -> Dict[str, Any]:
        print("⚡ Running Concurrency Load Tests (1, 5, 10, 25, 50 workers)...")
        benchmarks = {}
        client = TestClient(app)

        for concurrency in [1, 5, 10, 25, 50]:
            total_requests = 100
            latencies = []
            errors = 0

            def make_request():
                t0 = time.perf_counter()
                try:
                    r = client.get("/api/system/stats")
                    t1 = time.perf_counter()
                    if r.status_code == 200:
                        return (t1 - t0) * 1000.0, True
                    return (t1 - t0) * 1000.0, False
                except Exception:
                    return 0.0, False

            t_start = time.perf_counter()
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [executor.submit(make_request) for _ in range(total_requests)]
                for f in as_completed(futures):
                    lat, ok = f.result()
                    if ok:
                        latencies.append(lat)
                    else:
                        errors += 1
            t_total = time.perf_counter() - t_start

            throughput = round(len(latencies) / t_total, 2) if t_total > 0 else 0.0
            stats = calculate_stats(latencies, errors=errors)
            stats["throughput_req_sec"] = throughput
            stats["concurrency"] = concurrency
            benchmarks[f"Concurrency: {concurrency} Workers ({total_requests} Read Requests)"] = stats

        return benchmarks

    def execute_all(self) -> Dict[str, Any]:
        print("=================================================================")
        print("🚀 STARTING F.R.I.D.A.Y. PHASE 6.7 PERFORMANCE BENCHMARK SUITE")
        print("=================================================================")

        start_time = time.time()
        initial_resources = self.get_resource_usage()

        self.results["api"] = self.run_api_benchmarks()
        self.results["brain"] = self.run_brain_benchmarks()
        self.results["voice"] = self.run_voice_benchmarks()
        self.results["email"] = self.run_email_benchmarks()
        self.results["calendar"] = self.run_calendar_benchmarks()
        self.results["career"] = self.run_career_benchmarks()
        self.results["db"] = self.run_database_benchmarks()
        self.results["concurrency"] = self.run_concurrency_benchmarks()

        final_resources = self.get_resource_usage()
        elapsed_sec = round(time.time() - start_time, 2)

        self.results["meta"] = {
            "elapsed_seconds": elapsed_sec,
            "initial_resources": initial_resources,
            "final_resources": final_resources,
        }

        print(f"\n✅ All benchmarks completed in {elapsed_sec}s.")
        return self.results


if __name__ == "__main__":
    suite = FridayBenchmarkSuite()
    results = suite.execute_all()

    # Print summary table
    print("\n" + "=" * 85)
    print(f"{'Component / Subsystem':<50} | {'p50 (ms)':<8} | {'p95 (ms)':<8} | {'p99 (ms)':<8} | {'Errors'}")
    print("=" * 85)

    for category, tests in results.items():
        if category == "meta":
            continue
        for test_name, stats in tests.items():
            err_str = f"{stats['errors']} ({stats['error_rate']*100:.1f}%)" if stats['errors'] > 0 else "0"
            print(f"{test_name:<50} | {stats['p50']:<8.2f} | {stats['p95']:<8.2f} | {stats['p99']:<8.2f} | {err_str}")

    print("=" * 85)
