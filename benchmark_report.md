# ⚡ F.R.I.D.A.Y. Phase 6.7 — Performance & Latency Benchmark Report

**Found Batches:** 6 / 6
**Missing Batches:** None

## 1. Component Latency Distribution

| Component / Subsystem | Category | Mode | p50 (ms) | p95 (ms) | p99 (ms) | Min (ms) | Max (ms) | Error Rate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| API: GET /api/system/stats | API | `LOCAL_REAL` | **109.22** | 110.77 | 113.78 | 104.18 | 113.92 | 0.0% |
| API: GET /api/trading/live-prices | API | `LOCAL_REAL` | **1.22** | 1.78 | 1.82 | 1.0 | 1.82 | 0.0% |
| API: GET /api/trading/analysis | API | `LOCAL_REAL` | **200.21** | 364.3 | 436.83 | 134.44 | 454.96 | 0.0% |
| API: GET /api/dev/overview | API | `LOCAL_REAL` | **3.0** | 5.2 | 5.69 | 2.77 | 5.77 | 0.0% |
| API: GET /api/career/dashboard (LLM Briefing) | API | `LOCAL_REAL` | **307.99** | 411.93 | 421.17 | 192.5 | 423.48 | 0.0% |
| API: GET /api/career/resumes (Pure SQLite) | API | `LOCAL_REAL` | **1.62** | 2.77 | 5.71 | 1.44 | 6.91 | 0.0% |
| Brain: Fast-Path System ('lock display') | Brain | `LOCAL_REAL` | **63.14** | 81.43 | 83.41 | 55.51 | 83.82 | 0.0% |
| Brain: Fast-Path App ('open trading') | Brain | `LOCAL_REAL` | **1.52** | 1.69 | 4.6 | 1.4 | 5.78 | 0.0% |
| Brain: Guest Privilege Refusal ('lock system') | Brain | `LOCAL_REAL` | **0.92** | 0.95 | 3.65 | 0.92 | 4.75 | 0.0% |
| Brain: Dynamic Prompt Assembly (Context + Memory) | Brain | `LOCAL_REAL` | **1.41** | 2.19 | 2.32 | 1.16 | 2.34 | 0.0% |
| Brain: LLM Neural Inference (Groq/Gemini Target) | Brain | `SIMULATED` | **51.08** | 55.04 | 55.05 | 45.15 | 55.05 | 0.0% |
| TTS: Edge-TTS Time To First Audio (TTFA) | TTS | `LOCAL_REAL` | **958.74** | 1064.92 | 1069.42 | 846.55 | 1070.55 | 0.0% |
| TTS: Edge-TTS Audio Synthesis Total (~45 chars) | TTS | `LOCAL_REAL` | **929.96** | 985.53 | 992.37 | 878.51 | 994.07 | 0.0% |
| TTS: First Sentence Chunk Synthesis (Early Burst) | TTS | `LOCAL_REAL` | **922.73** | 1221.54 | 1311.55 | 789.71 | 1334.05 | 0.0% |
| TTS: In-Memory Audio Mock Generator | TTS | `MOCK` | **7.52** | 7.55 | 7.62 | 5.57 | 7.63 | 0.0% |
| STT: Simulated Local Whisper Engine | STT | `MOCK` | **24.22** | 30.03 | 30.03 | 20.07 | 30.03 | 0.0% |
| Voice: E2E Fast-Path Round Trip (STT -> Brain -> Response) | Voice_E2E | `LOCAL_REAL` | **34.14** | 41.84 | 47.18 | 23.39 | 49.23 | 0.0% |
| Email: Draft Creation + SHA-256 Hash + Approval Token | Email | `LOCAL_REAL` | **0.03** | 0.04 | 0.13 | 0.03 | 0.2 | 0.0% |
| Email: Draft Mutation + Version Bump + Re-hash | Email | `LOCAL_REAL` | **0.01** | 0.01 | 0.01 | 0.01 | 0.01 | 0.0% |
| Email: Approval Token Validation (10 Security Checks) | Email | `LOCAL_REAL` | **0.0** | 0.0 | 0.0 | 0.0 | 0.0 | 0.0% |
| Email: Full Pipeline (Draft -> Validate -> Send -> Verify -> Audit) | Email | `LOCAL_REAL` | **0.05** | 0.06 | 0.06 | 0.05 | 0.07 | 0.0% |
| Calendar: Draft Creation + Hash + Approval Token | Calendar | `LOCAL_REAL` | **0.03** | 0.06 | 0.07 | 0.03 | 0.07 | 0.0% |
| Calendar: Event Mutation + Version Bump + Re-hash | Calendar | `LOCAL_REAL` | **0.01** | 0.01 | 0.02 | 0.01 | 0.03 | 0.0% |
| Calendar: Approval Token Validation (Security Checks) | Calendar | `LOCAL_REAL` | **0.0** | 0.0 | 0.0 | 0.0 | 0.0 | 0.0% |
| Calendar: Full Pipeline (Draft -> Validate -> Create -> Verify -> Audit) | Calendar | `LOCAL_REAL` | **0.07** | 0.09 | 0.1 | 0.07 | 0.1 | 0.0% |
| Career: Multi-Provider Ingestion + Normalization + Dedup (20 Jobs) | Career | `LOCAL_REAL` | **2.75** | 3.85 | 6.05 | 2.49 | 6.9 | 0.0% |
| Career: Application Packet Assembly + SHA-256 Hash Binding | Career | `LOCAL_REAL` | **1.96** | 2.56 | 5.64 | 1.79 | 5.65 | 0.0% |
| Portal: Form Schema Discovery + Sensitivity Classification | Portal | `LOCAL_REAL` | **2.97** | 3.97 | 5.46 | 2.77 | 5.49 | 0.0% |
| Portal: Approved Submission Execution + Independent Verification | Portal | `LOCAL_REAL` | **9.05** | 13.67 | 15.74 | 7.4 | 16.56 | 0.0% |
| DB: Career Profile Read (Decryption & Masking) | Database | `LOCAL_REAL` | **0.26** | 0.3 | 0.43 | 0.25 | 0.51 | 0.0% |
| DB: Career Profile Write (Fernet Encryption) | Database | `LOCAL_REAL` | **0.27** | 0.29 | 2.16 | 0.24 | 3.34 | 0.0% |
| DB: Career Job Store Query | Database | `LOCAL_REAL` | **1.22** | 1.25 | 1.27 | 1.2 | 1.28 | 0.0% |
| DB: Long-Term Memory Query | Database | `LOCAL_REAL` | **0.24** | 0.26 | 2.36 | 0.22 | 4.36 | 0.0% |
| DB: Permission Audit Log Insert (WAL Append) | Database | `LOCAL_REAL` | **0.31** | 0.35 | 0.38 | 0.3 | 0.41 | 0.0% |

## 2. Concurrency & Throughput Scaling

| Concurrency Workers | Total Requests | Throughput (req/s) | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 Workers | 100 | **8.92** | 112.3 | 116.29 | 117.46 | 0 |
| 5 Workers | 100 | **39.76** | 125.95 | 131.73 | 133.97 | 0 |
| 10 Workers | 100 | **80.08** | 120.96 | 138.09 | 142.11 | 0 |
| 25 Workers | 100 | **150.01** | 134.61 | 263.68 | 267.84 | 0 |
| 50 Workers | 100 | **330.7** | 139.63 | 150.35 | 153.94 | 0 |

## 3. Top 5 Measured Latency Drivers & Bottlenecks

| Rank | Component | Measured p95 | Target | Classification | Nature & Analysis |
| :--- | :--- | :--- | :--- | :--- | :--- |
| #1 | TTS: First Sentence Chunk Synthesis (Early Burst) | 1221.54ms | <100ms | **P0** | TTS (LOCAL_REAL) |
| #2 | TTS: Edge-TTS Time To First Audio (TTFA) | 1064.92ms | <100ms | **P0** | TTS (LOCAL_REAL) |
| #3 | TTS: Edge-TTS Audio Synthesis Total (~45 chars) | 985.53ms | <100ms | **P1** | TTS (LOCAL_REAL) |
| #4 | API: GET /api/career/dashboard (LLM Briefing) | 411.93ms | <100ms | **P1** | API (LOCAL_REAL) |
| #5 | API: GET /api/trading/analysis | 364.3ms | <100ms | **P1** | API (LOCAL_REAL) |
