import time
from common import benchmark_call, save_batch_results
from fastapi.testclient import TestClient
from app import app
from services.brain.engine import respond
from services.brain.prompt_builder import build_system_prompt



def run_batch_api_brain():
    print("\n🚀 [BATCH A] Running API & Brain Intent Routing Benchmarks...")
    client = TestClient(app)
    results = []

    # 1. System Telemetry
    results.append(benchmark_call(
        name="API: GET /api/system/stats",
        category="API",
        mode="LOCAL_REAL",
        fn=lambda: client.get("/api/system/stats"),
        iterations=40,
    ))

    # 2. Trading Live Prices
    results.append(benchmark_call(
        name="API: GET /api/trading/live-prices",
        category="API",
        mode="LOCAL_REAL",
        fn=lambda: client.get("/api/trading/live-prices"),
        iterations=40,
    ))

    # 3. Technical Analysis
    results.append(benchmark_call(
        name="API: GET /api/trading/analysis",
        category="API",
        mode="LOCAL_REAL",
        fn=lambda: client.get("/api/trading/analysis?symbol=FX:EURUSD&interval=15"),
        iterations=15,
    ))

    # 4. Dev Overview (Owner Authenticated)
    results.append(benchmark_call(
        name="API: GET /api/dev/overview",
        category="API",
        mode="LOCAL_REAL",
        fn=lambda: client.get("/api/dev/overview"),
        iterations=30,
    ))

    # 5. Career Dashboard (Includes synchronous LLM briefing)
    results.append(benchmark_call(
        name="API: GET /api/career/dashboard (LLM Briefing)",
        category="API",
        mode="LOCAL_REAL",
        fn=lambda: client.get("/api/career/dashboard"),
        iterations=2,
        warmup=0,
        timeout_sec=2.0,
    ))

    # 5b. Career Resumes Store Query (Pure SQLite)
    results.append(benchmark_call(
        name="API: GET /api/career/resumes (Pure SQLite)",
        category="API",
        mode="LOCAL_REAL",
        fn=lambda: client.get("/api/career/resumes"),
        iterations=30,
    ))


    # 6. Brain Fast-Path System Control
    results.append(benchmark_call(
        name="Brain: Fast-Path System ('lock display')",
        category="Brain",
        mode="LOCAL_REAL",
        fn=lambda: respond("lock display", is_boss=True, silence_tts=True),
        iterations=30,
    ))

    # 7. Brain Fast-Path App Automation
    results.append(benchmark_call(
        name="Brain: Fast-Path App ('open trading')",
        category="Brain",
        mode="LOCAL_REAL",
        fn=lambda: respond("open trading", is_boss=True, silence_tts=True),
        iterations=30,
    ))

    # 8. Brain Guest Privilege Refusal (Instant Local Security Interceptor)
    results.append(benchmark_call(
        name="Brain: Guest Privilege Refusal ('lock system')",
        category="Brain",
        mode="LOCAL_REAL",
        fn=lambda: respond("lock system", is_boss=False, silence_tts=True),
        iterations=30,
    ))



    # 9. Dynamic System Prompt Assembly (Memories + Track + Context)
    results.append(benchmark_call(
        name="Brain: Dynamic Prompt Assembly (Context + Memory)",
        category="Brain",
        mode="LOCAL_REAL",
        fn=lambda: build_system_prompt("", is_boss=True, guest_active=False, brevity_mode="normal"),
        iterations=30,
    ))



    # 10. Neural LLM Inference (Simulated)
    def simulated_llm():
        time.sleep(0.045)  # 45ms simulated low-latency LLM inference
        return {"reply": "Good evening Prem, all systems operational.", "action": "reply"}

    results.append(benchmark_call(
        name="Brain: LLM Neural Inference (Groq/Gemini Target)",
        category="Brain",
        mode="SIMULATED",
        fn=simulated_llm,
        iterations=30,
    ))

    save_batch_results("batch_api_brain", results)


if __name__ == "__main__":
    run_batch_api_brain()
