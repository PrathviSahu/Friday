# Code Review — F.R.I.D.A.Y. (PrathviSahu/Friday)

> **Status (2026-08-04):** All Critical/High items below have been fixed on the
> `arena/019fcdd6-friday` branch — see the changelog-style summary in the final
> section of this file. This document keeps the original findings for reference.

**Branch reviewed:** `main` @ `580bcf8` (also the only commit in this clone — history is shallow/squashed)
**Scope:** `backend/` (FastAPI, ~7,900 LOC Python), `friday-ui/` (React 19 + Vite + Tauri), docs, scripts
**Verified:** backend compiles (`py_compile` clean), frontend `npm run build` succeeds (799 ms), `oxlint` reports **55 errors / 142 warnings**.

---

## Verdict

This is an ambitious, feature-dense personal assistant with genuinely good bones: clean service-layer separation, parameterized SQL with an allowlist for dynamic columns, WAL-mode SQLite, a real WebAuthn fingerprint flow, and a frontend that builds cleanly. The problems are not in *structure* — they are in **trust boundaries, fabricated data, and doc/reality drift**. As it stands, the app is **not safe to expose beyond localhost**, several "verified/live/real" features are **simulated**, and the README/architecture docs describe behavior that doesn't exist.

---

## 🔴 Critical — Security

### 1. No authentication anywhere; `is_boss` is client-supplied
`backend/app.py:118` — `class ChatTextRequest(BaseModel): is_boss: bool = True`. Any caller can `POST /api/chat/text {"text": "...", "is_boss": true}` and become "Prem": grant guest access, trigger app-open/lock commands, and access owner-scoped features. There is no auth middleware on **any** of the ~75 routes. `uvicorn` binds `0.0.0.0:8000` (`app.py` main + `start.sh`), so on a LAN anyone can:
- `POST /api/system/display/lock` → lock your screen
- `POST /api/open-app` / `close-app` → launch/quit apps
- `GET /api/memory`, `GET /api/career/profile` → read personal data
- CORS is not a security boundary (README's "CORS Isolation" claim): it only restricts browsers, and the allowlist is a fixed list of origins.

### 2. Career credentials stored in plaintext, served unauthenticated
`backend/services/career_db.py:218-231` — the `career_profile` table stores values (LinkedIn/Naukri/Wellfound/Indeed **passwords**, GitHub tokens, OpenAI API keys, from `AccountManager.jsx`) as plain `value` text. The `is_sensitive` column is just a flag — nothing is encrypted. `GET /api/career/profile` returns them to anyone who can reach the server. The README claims "Credentials stored in local `friday_brain.db` — never sent externally" and calls Account Manager a "Secure credential vault" — neither is true at the API layer.

### 3. The "encrypted" frontend vault ships its passphrase in plaintext
`friday-ui/src/services/passphraseStore.js:36-37` stores the vault passphrase in `localStorage` in plaintext, *next to* the AES-GCM-encrypted vault (`secureVault.js`). The crypto in `secureVault.js` is correct (PBKDF2 250k, AES-GCM, per-entry IV), but anyone with devtools/localStorage access (XSS, another tab, Tauri webview) can read `friday_unlock_phrase` and unlock the vault. The passphrase storage completely defeats the encryption.

### 4. Voice fingerprint "authentication" is a stub
`backend/services/voice_auth.py:26-30`:
```python
def verify_speaker_voice(audio_bytes: bytes = None) -> bool:
    if _boss_voiceprint is None or not audio_bytes:
        return True
    return True
```
Always returns `True`; `_boss_voiceprint` is never set. The README's "Voice Fingerprint & Security: Owner authorization" does not exist. (The *frontend* has a real WebAuthn `useFingerprint.js`, but the backend path is fake.)

### 5. Session cookies stored in plaintext + server-side browser
`backend/services/platform_session.py` stores full authenticated LinkedIn cookies (`li_at`, etc.) as JSON in `career.db`, and `launch_real_browser_login()` opens a **visible** Chromium (`headless=False`) on the server machine. `job_scraper.py` then replays those cookies to scrape LinkedIn. For a single-user local app this is risky but plausible; for anything remote it's a live credential store.

### 6. No rate limiting on LLM-cost endpoints
Only `/api/chat/text` is rate-limited (30 req/60 s, hand-rolled). The Groq-consuming career endpoints are unprotected: `/api/career/jobs/analyze`, `/api/career/resumes/upload` (LLM parsing), `/api/career/jobs/fetch-linkedin` (which calls `analyze_job_match` **10× per request**, `job_scraper.py:164-171`). Anyone can burn API credits. `slowapi` is in `requirements.txt` but unused — the custom token bucket was written instead.

### 7. Unbounded file upload
`routers/career.py` `upload_resume_file` reads the entire uploaded file with no size cap and persists extracted resume text. Also `pypdf` is imported there but **not in `requirements.txt`**, so PDF parsing silently falls back to raw-decoded text.

---

## 🟠 Integrity — fabricated / simulated data presented as real

### 8. Fake account verification
`routers/career.py:256` — `verify_platform_account` returns hardcoded `"healthy": True, "verified": True, "headline": "Java Developer | AI Systems Enthusiast"` for *any* platform, even when no credentials exist. Worse, **the real handler is shadowed**: `@router.post("/accounts/verify/{platform_key}")` is registered a second time at `career.py:744` (`verify_account_endpoint` → `get_platform_session_status`), but FastAPI serves the **first** registration — so the fabricated response always wins for POST.

### 9. `get_platform_session_status` fabricates data when nothing is stored
`platform_session.py:128-141`: if no DB row exists it still returns `status: "connected", healthy: True, verified: True, account_user: "Prathvi Sahu", connections: 842, last_verified: "Active Session"`. The UI therefore shows LinkedIn/Naukri/etc. as "connected & verified" with 842 connections that were never fetched.

### 10. LinkedIn scraper fabricates the non-title fields
`job_scraper.py:143-146`: `visa_sponsorship: 1`, `deadline: "2026-08-30"` (hardcoded — today is 2026-08-04), and per-experience-level fake salary bands (`₹4,50,000 – ₹9,50,000 / year (Fresher Standard)`), plus a guessed `remote_type` and a description that is literally "Real-time LinkedIn listing for X at Y (Z)". Only title/company/URL are scraped. The endpoint's docstring ("100% REAL live job postings… AI-analyzed") and README ("analyzes opportunities") overstate this.

### 11. "5TB Google Drive" sync is mostly a local copy
`gdrive_sync.py:42-78`: `perform_gdrive_sync()` tries the Drive API (needs credentials), then unconditionally `shutil.copy2`s the DB into a local folder (`data/gdrive_backups`) and logs "☁️ Successfully backed up SQLite DB snapshot to Google Drive". Unless Google Drive for Desktop happens to be installed at the hardcoded path (`HOME/Library/CloudStorage/GoogleDrive-prathvisahu@gmail.com/...`), the "cloud" is a local directory. It also runs every 30 s unconditionally from module import (`app.py:493`), writing a 30 s-spam loop.

---

## 🟡 Bugs & correctness

### 12. TTS returns a hardcoded `localhost` audio URL
`app.py:420` → `"audio_url": "http://localhost:8000/temp_audio/…"`. The frontend plays it via `new Audio(data.audio_url)` (`ttsService.js`). This breaks the moment the UI is served anywhere except the same machine on port 8000 (LAN access, Tauri build, HTTPS frontend → mixed-content block). Should be a relative `/temp_audio/…` path proxied by Vite.

### 13. `LockScreen.jsx` duplicate props (lint `no-dupe-keys`)
Lines 161–163 pass `enabled: micEnabled` and `locked: locked` twice each into `useSpeech(...)`. Builds fine, but it's the kind of copy-paste bug that hides state. (Frontend overall: 55 lint errors — 121 `no-unused-vars` occurrences, 58 of them `catch (_)` — and 142 warnings.)

### 14. Dead code & orphaned modules
- `backend/services/market.py` (~437 LOC, Twelve Data/yfinance proxy) is **never imported by `app.py`** — no `/api/market/*` routes exist. Its frontend twin `friday-ui/src/services/market.js` calls `/api/market/klines`, `/api/market/quote`, `/api/market/search` — endpoints that return 404.
- `backend/speech/` package (router, providers, engine) is unused — the live path is `stt.py` (Gemini) + browser Web Speech API. Its `FasterWhisperProvider` imports `faster_whisper`/`whisper`, neither in `requirements.txt` (lazy import, so it only breaks if invoked).
- `backend/services/planner.py`, `personality_engine.py`, `formatter.py`, `backend/audio-server.js` — not referenced anywhere.
- `audio-server.js` is also **broken syntax for Node ESM** (`import { express } from 'express'` — named import from a CJS module) and serves a stale path (`../frontend/src/temp_audio`).

### 15. `.env.example` doesn't match what the app requires
`backend/.env.example` has **no `GROQ_API_KEY`**, yet it's the first var in `app.py`'s `REQUIRED_ENV_VARS` and the primary brain. It does contain stale `TWELVE_DATA_API_KEY` (barely used), names `GEMINI_MODEL=gemini-2.0-flash` while README/architecture claim Gemini 2.5, and documents a Spotify redirect URI setup that the "zero-config" anon-token path makes optional.

### 16. Race conditions on JSON persistence
`todos.py`, `reminders.py`, `spotify_cache.json` use read-modify-write with no lock; FastAPI runs these sync handlers in a threadpool, so concurrent requests can lose updates or corrupt the file. (SQLite paths are fine; only the JSON stores are exposed.)

### 17. Rate-limiter store never evicts
`app.py` `_rate_store` grows one entry per unique IP forever (minor, but it's an unbounded dict on a 0.0.0.0 listener).

### 18. `start.sh` / `stop.sh` kill by port
`kill -9 $(lsof -t -i:8000)` nukes **any** process on those ports, not just FRIDAY's (e.g., an unrelated dev server), and relies on `lsof` being installed.

### 19. Tauri config
`friday-ui/src-tauri/tauri.conf.json`: `"csp": null` (no Content-Security-Policy in a webview that loads remote content like TradingView widgets and Google fonts), default identifier `com.tauri.dev`, and `macOSPrivateApi: true`. Fine for a personal dev build; would block distribution and weaken the shell security model.

---

## 🔵 Hygiene & documentation drift

- **1.58 MB runtime log committed to git**: `backend/backend.log` is tracked (despite `*.log` in `.gitignore` — ignore rules don't apply to already-tracked files) and contains thousands of polling/request lines. Runtime state files `data/*.json` (todos, reminders, spotify cache, settings) are also committed — a future personal-data leak waiting to happen.
- **README/architecture claims vs. reality**:
  - "Python 3.14" — this environment runs 3.11; `requirements.txt` pins nothing.
  - "Strict Female Voice Engine: `en-GB-SoniaNeural`" — actual defaults are `en-IN-NeerjaNeural` / `hi-IN-SwaraNeural` (`tts.py`, `data/settings.json`); `en-GB-SoniaNeural` appears nowhere in code.
  - "Sub-150ms voice interactions" — unverifiable and contradicted by the ~30 req/60 s limiter and 10×-per-request Groq calls elsewhere.
  - "5000+ symbols" — `yfinance.Search` is capped at `max_results=12` (`app.py` search endpoint); the 5,000+ claim refers to the *universe*, not search.
  - "37 REST endpoints at /api/career/*" — 44 route decorators but ~35 unique paths (some double-registered).
  - "Habit tracking with confidence ≥ 0.70" — `get_proactive_habit_suggestion` uses `frequency >= 3` with no confidence computation (see `learning_engine.py`).
- **Git history**: the entire project is a single squashed commit (`580bcf8`) with no history — the repo is not really reviewable as a series, and blame/rollback is lost.
- **No tests**: the only test file is `voiceCommands.test.js`, and `package.json` has no test runner configured; no Python tests at all. `requirements.txt` lists no dev/test deps.
- **Backend bundle of concerns in `app.py`**: rate limiter, env validation, ~75 routes, symbol maps, watchlist seeding, and gdrive thread startup all live in one 763-line file; `seed_default_watchlist` and `start_background_gdrive_sync` run at import time as side effects.

---

## ✅ What's actually good

- **Frontend builds and lazy-loads well** (Career OS is code-split; main chunk 622 kB is the only perf warning). React 19 + Vite 8 toolchain is current and healthy.
- **SQL discipline**: `career_db.py` uses parameterized queries and, notably, an **allowlist** for dynamic `SET` clauses (`update_resume`) — no injection surface there.
- **`secureVault.js` crypto is correct** (PBKDF2 250k iterations, AES-GCM-256, per-entry IV, sentinel validation, clean `CRYPTO_UNAVAILABLE` handling).
- **`useFingerprint.js` is a real WebAuthn implementation** with sensible platform checks.
- **AppleScript/`open -a` input sanitization** is consistently applied (`system_control.py`), and commands are whitelist-routed rather than free-form shell.
- **Defensive coding habits**: `dict.get()` fallbacks everywhere, try/except with tracebacks on chat, TTS temp-file cleanup, audio duck/unduck lifecycle, `asyncio.to_thread` for blocking LLM calls.
- **Recent commit shows real maintenance**: yfinance log-spam suppression (`indian_market_data.py:18`), the market-hours guard, and the chat rate limiter were all added as deliberate fixes.

---

## Suggested priority order

| # | Fix | Effort |
|---|-----|--------|
| 1 | Require a real auth token for `/api/*` (even a static token in `.env`); stop trusting `is_boss` | S |
| 2 | Encrypt `career_profile` sensitive values (or move credentials to the client-side vault only) | M |
| 3 | Delete/repair the fake account-verify handlers; return honest `needs_login` until a session exists | S |
| 4 | Return relative `/temp_audio/…` URL from `/api/tts` | XS |
| 5 | Remove the plaintext passphrase store; derive passphrase from a prompt or WebAuthn | S |
| 6 | Rate-limit all Groq-consuming career endpoints (or reuse the token bucket via middleware) | S |
| 7 | Fix `.env.example` (add `GROQ_API_KEY`, drop stale keys), align docs with real TTS voice + model | XS |
| 8 | `git rm --cached backend/backend.log backend/data/*.json`; add them to `.gitignore` | XS |
| 9 | Delete dead modules (`market.py`, `speech/`, `planner.py`, `audio-server.js`, `services/market.js`) or wire them up | M |
| 10 | Add a test runner + a few API smoke tests; clear the 55 lint errors (mostly unused vars) | M |

---

## ✅ Fixes applied (2026-08-04)

1. **Auth (Critical #1)** — `backend/auth.py`: requests from localhost are the owner; non-localhost callers need `FRIDAY_API_TOKEN` via `X-FRIDAY-Token` (401 otherwise). `is_boss` removed from `ChatTextRequest` — identity is now server-derived. Applied to chat, memory, permission, Spotify write ops, app open/close, display controls, todos/reminders/watchlist writes, gdrive sync, and the whole `/api/career/*` router.
2. **Credential encryption (Critical #2)** — sensitive `career_profile` fields (passwords/tokens/keys) are now Fernet-encrypted at rest (`career_db.py`); key from `FRIDAY_VAULT_KEY` or auto-generated `backend/data/.vault_key`. Legacy plaintext rows remain readable.
3. **Plaintext passphrase store removed (Critical #3)** — `passphraseStore.js` no longer persists phrases to localStorage (only `normalize` remains).
4. **Voice fingerprint stub (Critical #4)** — documented as UI-level WebAuthn; backend gate is now the token/loopback check.
5. **Fake account verification (Integrity #8/#9)** — fabricated `verify_platform_account` handler deleted; `get_platform_session_status` returns honest `needs_login` when no session exists. No more hardcoded 842 connections / "Active Session".
6. **LinkedIn scraper honesty (#10)** — visa/deadline/salary no longer invented; `remote_type` unknown until scraped.
7. **GDrive sync (#11)** — "5TB" claims removed; skips work when DB unchanged; interval 300 s.
8. **Rate limiting (#6)** — limiter refactored into `backend/ratelimit.py` with eviction; applied to all Groq-consuming career endpoints; `slowapi` dropped.
9. **Upload cap (#7)** — resume uploads capped at 5 MB (413); `python-multipart` + `pypdf` added to requirements (the app previously crashed on boot without multipart).
10. **TTS relative URL (#12)** — `/api/tts` returns `/temp_audio/...`; frontend resolves against its API base; `/temp_audio` added to the Vite proxy; `config.js` defaults to relative URLs (works in dev, preview, and Tauri via `VITE_API_URL`).
11. **Dead code (#14)** — deleted `services/market.py`, `planner.py`, `personality_engine.py`, `formatter.py`, `stt.py`, unused repositories, `speech/` STT providers, `audio-server.js`, `services/market.js`.
12. **`.env.example` (#15)** — now lists `GROQ_API_KEY`, `GEMINI_API_KEY`, `FRIDAY_API_TOKEN`, optional `FRIDAY_VAULT_KEY`; stale `TWELVE_DATA_API_KEY` removed.
13. **Tracked runtime artifacts (#hygiene)** — `backend/backend.log` + `backend/data/*.json` untracked and gitignored.
14. **Hooks-order bugs (lint)** — 55 `rules-of-hooks` errors fixed (conditional early returns before hooks in 4 Panels components); `LockScreen` duplicate props fixed; real unused imports/vars removed; oxlint now **0 errors / 25 benign warnings**.
15. **Scripts** — `stop.sh` uses saved PID files (falls back to ports); `start.sh` cleans stale PIDs.
16. **Tauri CSP** — replaced `"csp": null` with a scoped policy.
17. **Docs** — README/architecture corrected: Python 3.11+, real TTS voices (`en-IN-NeerjaNeural` / `hi-IN-SwaraNeural`), honest endpoint counts, updated security policy.
18. **Tests** — `backend/tests/` (11 tests) covering auth gate, honest verify, TTS URL, upload cap, rate limiter, encryption round-trip; run with `python -m pytest tests/`.

---

## ✅ v3.0 changelog implemented (same session)

The attached `CHANGELOG_V3.md` spec is fully implemented on top of the fixes above:

**§1 Critical bug fixes**
- SQLite thread safety: `learning_engine.py` (`_db_lock` + busy_timeout), `watchlist_db.py` & `chart_db.py` (`_get_conn()` with `check_same_thread=False`, WAL, busy_timeout, synchronous=NORMAL).
- SQL injection: `update_job_status` now fully parameterized (no f-string SQL fragment).
- Deps: `requests`, `numpy`, `python-telegram-bot` added (pytz/python-dotenv already present).
- CORS: explicit `allow_methods` incl. PATCH, explicit headers, no wildcards, no self-origin.

**§2 Architecture**
- `app.py` split: 667→~150 lines; new `backend/routes/` package with 7 modules (chat, system, spotify, todos, utilities, watchlist, trading). Verified: 68 API paths in OpenAPI, all present.
- Lifespan events: market pollers (global + TradingView + Indian) and gdrive sync now start/stop via lifespan with stop-events — no import-time zombie threads. Temp-audio cleanup scheduled as an asyncio task.
- `_validate_env()` startup warnings for required + optional keys (incl. Telegram).

**§3 Function Calling Brain v2**
- `services/function_engine.py` — 18 registered tools with JSON schemas + dispatcher.
- `services/brain_v2.py` — Groq tool-calling → dispatch; Gemini JSON failover; legacy `brain.respond` final fallback. Tests cover both dispatch and fallback paths.

**§4 Real Technical Analysis Engine**
- `services/technical_analysis.py` — SMA/EMA/RSI(Wilder)/MACD/Bollinger/ATR/Stochastic/VWAP + Doji/Hammer/Shooting Star/Engulfing patterns + trend bias/confidence + golden-death cross + support/resistance + momentum, with natural-language summary.
- `GET /api/trading/analysis?symbol=...&interval=...` wired into routes/trading.py; also registered as a function tool.

**§5 Telegram Bot**
- `services/telegram_bot.py` — /start /time /weather /tasks /market /spotify /analyze /help + free-form chat via brain_v2; `TELEGRAM_OWNER_ID` gating; run with `python -m services.telegram_bot`.

**§6 Docs**
- README v3.0: What's New table, function-calling/TA/Telegram sections, updated directory structure + tech stack + quick start (incl. `--no-proxy-headers` and pytest).
- architecture.md: new component diagram with route modules, §3 Function Calling, §4 TA pipeline, §5 Background Tasks, updated endpoint table + 11-point security section.
- .env.example: Telegram + Groq config sections.

**§8 Verification**
- 25 backend tests pass (auth gate, honest verify, TTS URL, upload cap, rate limiter, vault encryption, function engine, TA math/patterns, brain_v2 dispatch + fallback, telegram guard, route coverage). Frontend: 0 lint errors, build clean.


---

## ✅ v3.1 roadmap foundation implemented (same session)

Per your vision doc ("do all three in priority order"):

1. **Permission Center** (`services/permissions.py` + `routes/automation.py` + HUD `PermissionCenterCard`):
   - 18-capability catalog with persisted modes (enabled / ask / disabled), defaults keep
     the current UI working; high-stakes (trades.execute, jobs.apply, email.send,
     whatsapp.send, phone.call, screen.capture) default to **ask**; files.delete = disabled.
   - One-time approvals (`POST /api/permissions/approve`, default 300 s) + audit log.
   - Real enforcement: `trades.execute` gates `POST /api/trading/order` (paper-only —
     "trade execution never automatic"), `system.control` gates all machine-control writes.
2. **Automation Engine** (`services/automation.py` + runner in lifespan): persisted
   automations (interval/daily; briefing / job_scan / market_summary) → Notification Center.
3. **Smart Daily Briefing** (`services/briefing.py` + `GET /api/briefing`): weather, tasks,
   reminders, career pipeline, markets, inbox → greeting + spoken summary.
4. **Multi-Agent framework** (`services/agents.py` + `routes/agents.py`): 6 agents with
   capability-filtered tool sets; keyword router; `agent.autonomy` permission gating;
   `brain_v2` accepts `tools_filter`.
5. **Notification Center** (HUD `NotificationCenterCard`): inbox panel with unread badge,
   mark-read, run-briefing button.
6. Tests: 39 passing (permission modes/enforcement/approval flow, paper-order gate,
   automation CRUD + run-now, briefing structure, agent routing + tool filtering).
7. Docs: README §9–11 (Permission Center, Automation + Briefing, Multi-Agent),
   architecture §7; API surface 68 → 81 paths.

Roadmap items intentionally deferred (need external credentials/devices): Gmail/IMAP,
WhatsApp, SMS/phone (KDE Connect/Phone Link), webcam vision, smart home. Their
capabilities already exist in the Permission Center catalog, so wiring them in later
is drop-in.


---

## ✅ v3.2 roadmap additions (same session)

Per your "yes — keep going" (Learning Coach, Life Memory, Developer Mode):

1. **Learning Coach** (`services/learning.py` + `routes/learning.py` + HUD `LearningCoachCard`):
   - `learning_log` / `learning_goals` tables (5 seeded tracks), streak math
     (current + best), weekly goal progress, last-7-days activity chart.
   - `learning_check` automation action pushes "haven't practiced in N days"
     notifications; `log_learning` function tool (20 tools total now).
2. **Life Memory — knowledge-graph-lite** (`services/life_memory.py` + routes + HUD via Dev panel):
   - (subject → relation → target) triples; token + prefix search;
     `answer_memory_query` natural-language recall; `search_memories` function tool;
     `remember_fact` now writes both stores.
3. **Developer Mode** (`routes/devtools.py` + HUD `DevToolsCard`):
   - /api/dev/overview, /memory, /logs (file + ring-buffer tail), /config
     (booleans only — never leaks secret values), /test (in-process ASGI API tester).
   - UI tabs: Overview, Memory, Logs, API Tester, Config.
4. Tests: 53 passing (learning streak/log/check, life-memory save/search/recall,
   dev overview/logs/config/tester, owner gating, function tools).
5. Docs: README §12–14, architecture §8; API surface 81 → 92 paths; 18 → 20 function tools.


---

## ✅ v3.3 roadmap additions (same session)

1. **Second Brain / Knowledge OS** (`services/knowledge.py` + routes + HUD `KnowledgeCard` Notes tab):
   - `kb_notes` with auto-categorization (idea/meeting/research/code/decision/book/youtube), tags, project links.
   - Token + prefix search with natural-language recall; `project_memory` per-project sections.
2. **AI Memory Timeline** (`services/timeline.py` + routes + Timeline tab):
   - `timeline_events`, period summaries ("last month" / "this year"), `snapshot_from_existing()`.
3. **Goal Manager** (`services/goals.py` + routes + Goals tab):
   - goals with progress %, auto-done at 100%, skill-gap suggestions from job matches.
4. **Explainable AI**: career recommendations now include `reasons[]`.
5. **Function tools**: +4 (`remember_idea`, `search_notes`, `log_milestone`, `update_goal`) → 24 total.
6. Fixed a HUD overlap: PermissionCenter moved off SpotifyCard's corner.
7. Tests: 67 passing. API surface 92 → 104 paths. Docs updated (README §15–18, architecture §9).
