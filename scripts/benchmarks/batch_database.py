import time
from common import benchmark_call, save_batch_results
from services import career_db, memory, permissions



def run_batch_database():
    print("\n🚀 [BATCH E] Running Database (SQLite WAL & At-Rest Encryption) Benchmarks...")
    results = []

    # 1. Profile Read with Decryption & Masking
    results.append(benchmark_call(
        name="DB: Career Profile Read (Decryption & Masking)",
        category="Database",
        mode="LOCAL_REAL",
        fn=lambda: career_db.get_profile(mask_sensitive=True),
        iterations=50,
    ))

    # 2. Profile Write with Fernet AES-128-CBC Encryption
    results.append(benchmark_call(
        name="DB: Career Profile Write (Fernet Encryption)",
        category="Database",
        mode="LOCAL_REAL",
        fn=lambda: career_db.upsert_profile_field("benchmark_field", "super_secret_val", is_sensitive=True),
        iterations=40,
    ))

    # 3. Career Job Lookup
    results.append(benchmark_call(
        name="DB: Career Job Store Query",
        category="Database",
        mode="LOCAL_REAL",
        fn=lambda: career_db.get_jobs(),
        iterations=50,
    ))


    # 4. Long-Term Memory Retrieval
    results.append(benchmark_call(
        name="DB: Long-Term Memory Query",
        category="Database",
        mode="LOCAL_REAL",
        fn=lambda: memory.get_all_memories(),
        iterations=50,
    ))

    # 5. Permission Audit WAL Log Append
    results.append(benchmark_call(
        name="DB: Permission Audit Log Insert (WAL Append)",
        category="Database",
        mode="LOCAL_REAL",
        fn=lambda: permissions._audit("trades.execute", "allowed", "Benchmark execution test"),
        iterations=50,
    ))

    save_batch_results("batch_database", results)


if __name__ == "__main__":
    run_batch_database()
