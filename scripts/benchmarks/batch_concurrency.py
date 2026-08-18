import time
import math
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from common import save_batch_results
from fastapi.testclient import TestClient
from app import app



def run_batch_concurrency():
    print("\n🚀 [BATCH F] Running Concurrency Scaling Load Tests (1, 5, 10, 25, 50 Workers)...")
    client = TestClient(app)
    results = []

    for concurrency in [1, 5, 10, 25, 50]:
        total_requests = 100
        latencies = []
        errors = 0

        def make_call():
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
            futures = [executor.submit(make_call) for _ in range(total_requests)]
            for f in as_completed(futures):
                lat, ok = f.result()
                if ok:
                    latencies.append(lat)
                else:
                    errors += 1
        t_total = time.perf_counter() - t_start

        n = len(latencies)
        sorted_lats = sorted(latencies) if n > 0 else [0.0]

        def percentile(p: float) -> float:
            if n == 0:
                return 0.0
            k = (n - 1) * (p / 100.0)
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return sorted_lats[int(k)]
            d0 = sorted_lats[int(f)] * (c - k)
            d1 = sorted_lats[int(c)] * (k - f)
            return d0 + d1

        throughput = round(n / t_total, 2) if t_total > 0 else 0.0

        item = {
            "name": f"Concurrency: {concurrency} Workers (100 Requests)",
            "category": "Concurrency",
            "mode": "LOCAL_REAL",
            "concurrency": concurrency,
            "sample_count": n,
            "throughput_req_sec": throughput,
            "min_ms": round(sorted_lats[0], 2) if n > 0 else 0.0,
            "p50_ms": round(percentile(50.0), 2),
            "p95_ms": round(percentile(95.0), 2),
            "p99_ms": round(percentile(99.0), 2),
            "max_ms": round(sorted_lats[-1], 2) if n > 0 else 0.0,
            "mean_ms": round(statistics.mean(sorted_lats), 2) if n > 0 else 0.0,
            "stddev_ms": round(statistics.stdev(sorted_lats), 2) if n > 1 else 0.0,
            "error_count": errors,
            "error_rate": round(errors / total_requests, 4),
            "timestamp": time.time(),
        }
        results.append(item)
        print(f"   ↳ {concurrency} Workers: {throughput} req/s | p50: {item['p50_ms']}ms | p95: {item['p95_ms']}ms | Errors: {errors}")

    save_batch_results("batch_concurrency", results)


if __name__ == "__main__":
    run_batch_concurrency()
