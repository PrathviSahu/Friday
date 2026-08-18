# F.R.I.D.A.Y. Technical Architecture

**Document Purpose**
This document describes the technical architecture of **F.R.I.D.A.Y. v5.0** —
a voice-controlled personal AI operating system. It covers component hierarchy,
data flows, LLM orchestration (47-tool agentic loop), real-time market-data
pipelines, the Career Intelligence Center (Career OS), the permission/security
model, and deployment topologies.

**Verified facts (August 2026):** 195 REST operations across 168 `/api/*`
paths · 47 function-calling tools · 24 permission capabilities · 17 dashboard
capsules · 323 backend tests + 16 frontend tests passing.

---

## 1. System Vision

F.R.I.D.A.Y. is built as a voice-first personal operating system:

1. **Dual-Engine LLM Core**:
   - **Fast path**: deterministic handlers (<15 ms) for time, weather, volume,
     Spotify, navigation, macros, security/permissions.
   - **Primary LLM**: Groq `llama-3.3-70b-versatile` with 47 tool schemas and a
     4-step agentic loop.
   - **Failover**: Google Gemini 2.5 flash pool → legacy regex fallback.

2. **Single-Audio Mutex** (`ttsService.js`): a monotonic sequence counter
   guarantees only one audio source plays at a time; any new utterance/barge-in
   instantly purges the in-flight pipeline. TTS is Microsoft Edge-TTS
   (`en-IN-NeerjaNeural` / `hi-IN-SwaraNeural`).

3. **Stark HUD — 17-in-1 Sliding Dashboard**: holographic capsule center with
   live search, category filters and armed-state telemetry; 1-tap workspace
   launching for Career OS, Trading Workstation and DevTools.

4. **Quantum Trading Workstation**: TradingView Lightweight Charts, live OHLCV
   across 7 resolutions, 5,000+-instrument universe (NSE/BSE, Forex, Crypto,
   US equities), drag-and-drop SQLite watchlist, lifespan-managed price
   pollers, and a real technical-analysis engine.

5. **Career Intelligence Center (Career OS)** — fully operational:
   - AI engine (`career_intelligence.py`): Groq for job-match scoring, cover
     letters, interview questions, skill-gap analysis, daily briefing.
   - DB layer (`career_db.py`): 10 SQLite tables in `friday_brain.db` (WAL),
     with Fernet-encrypted sensitive fields.
   - REST API (`routers/career.py`): **32 paths / 43 operations** at `/api/career/*`.
   - React frontend: 12 lazy-loaded modules with mobile horizontal sub-nav.

6. **Mobile & PWA**: push-to-talk (Spacebar / thumb hold), Android mic release
   on tab blur (`visibilitychange`), Spotify deep-linking, PWA meta tags.

---

## 2. Component Diagram

```
+----------------------------------------------------------------------------+
|                    React 19 Frontend (friday-ui)                           |
|                                                                            |
|  [useSpeech PTT] --> [ttsService: Single-Audio Mutex]                      |
|        |                    |                                             |
|  [LockScreen]        [Stark 17-in-1 Dashboard]  [TradingWS]  [Career OS]   |
|  (WebAuthn / typed   (17 capsules)              (charts)      (12 modules) |
|   password unlock)                                                         |
+----------------------------------------------------------------------------+
          | HTTP/JSON (REST) — Vite dev proxy or nginx /api proxy
          v
+----------------------------------------------------------------------------+
|                 FastAPI Python Backend (:8000)                             |
|                                                                            |
|  [app.py] — thin wiring: CORS, static mount, lifespan lifecycle            |
|     ├── routes/chat.py         brain, memory, speech, proactive            |
|     ├── routes/automation.py   permissions, automations, notifications,    |
|     │                          briefing                                    |
|     ├── routes/agents.py       agent list / chat / route                   |
|     ├── routes/autonomy.py     autonomous-action journal, undo, revoke     |
|     ├── routes/context.py      focus context (time-of-day, market state)   |
|     ├── routes/knowledge.py    second brain, timeline, goals               |
|     ├── routes/learning.py     learning coach                              |
|     ├── routes/life_memory.py  subject→relation→target memories            |
|     ├── routes/macros.py       voice macros                                |
|     ├── routes/presence.py     cross-device approvals + Web Push           |
|     ├── routes/email.py / calendar.py / meetings.py / whatsapp.py          |
|     ├── routes/documents.py / company.py / coding.py                       |
|     ├── routes/system.py       display/stats/apps (macOS host)             |
|     ├── routes/spotify.py      current-track, seek, duck/unduck            |
|     ├── routes/todos.py / utilities.py / watchlist.py                      |
|     ├── routes/trading.py      ohlcv, live-prices, analysis, search,       |
|     │                          chart-db, paper order                       |
|     ├── routes/devtools.py     overview, metrics, logs, config, tester     |
|     └── routers/career.py      Career OS (32 paths, 43 operations)         |
|                                                                            |
|  Services layer:                                                           |
|  ├── brain/                   modular brain package + fast-path handlers   |
|  ├── brain_v2.py              agentic tool loop (max_steps=4)              |
|  ├── function_engine.py       47-tool registry + dispatcher                |
|  ├── embeddings.py            Gemini text-embedding-004 RAG                |
|  ├── technical_analysis.py    real TA engine                               |
|  ├── market_data.py / indian_market_data.py   lifespan-managed pollers     |
|  ├── automation.py / briefing.py / notifications.py / permissions.py       |
|  ├── autonomy_engine.py / presence.py / macros.py / context_engine.py      |
|  ├── knowledge.py / timeline.py / goals.py / learning.py / life_memory.py  |
|  ├── memory.py / memory_consolidator.py / reminders.py / todos.py          |
|  ├── email_agent.py / calendar_agent.py / meeting_agent.py                 |
|  ├── whatsapp_agent.py / document_agent.py / coding_agent.py               |
|  ├── company_intelligence.py / job_scraper.py / platform_session.py        |
|  ├── system_control.py / mac_controls.py / system_stats.py                 |
|  ├── stt.py / tts.py / weather.py / web_search.py                          |
|  ├── gdrive_api.py / gdrive_sync.py / telegram_bot.py / agents.py          |
|  ├── metrics.py / voice_auth.py / learning_engine.py / chart_data.py       |
|  └── auth.py / ratelimit.py    owner auth + per-IP sliding window          |
|                                                                            |
|  Databases:                                                                |
|  ├── friday_brain.db         AI memory + Career OS + permissions +         |
|  │                           automations + presence (WAL, thread-safe)     |
|  ├── friday_trading_db.sqlite  watchlist + chart drawings (WAL)            |
|  ├── meetings.db / documents.db / embeddings.db                            |
|  └── data/*.json             drafts, todos, reminders, settings            |
+----------------------------------------------------------------------------+
          |                       |                        |
          v                       v                        v
   [Groq Llama 70B]      [Google Gemini 2.5]     [macOS host / Spotify /
   (primary + tools)    (failover + embeddings)  Open-Meteo / Telegram /
                                                 Gmail / Google Calendar]
```

---

## 3. Smart Function-Calling Brain (v4)

```
User Voice / Text
      │
      ▼
brain_v2.respond_v2(text)
      │
      ├─ _build_context_messages(text):
      │     • system prompt (personality + honesty rules)
      │     • last 6 conversation turns (get_recent_conversation)
      │     • permanent facts (get_memory_context_string)
      │     • top-3 SEMANTIC memories (embeddings.semantic_context →
      │       Gemini text-embedding-004 RAG over facts/notes/meetings)
      │     • the user's request
      │
      ├── AGENTIC LOOP (max 4 steps, max_steps=4):
      │     Groq (GROQ_MODEL, default llama-3.3-70b-versatile) with
      │     tools=function_engine.get_tools_schema()  → 47 tools
      │       → ALL tool_calls executed via dispatch(), results appended as
      │         tool messages → loop until the model answers
      │       → send_*/create_* tools surface email_confirm /
      │         calendar_confirm / whatsapp_confirm approval actions
      │
      ├── Fast-path handlers (before LLM):
      │     security/permissions, navigation, hardware, utilities, media,
      │     agents, macros — deterministic, <15 ms
      │
      ├── Step 2: Gemini failover pool — structured JSON {"reply","action",...}
      │            (also receives history + semantic memory context)
      │
      └── Step 3: legacy regex fallback (always works)
```

**Tool registry (`function_engine.py`):** **47 registered functions** across
categories — time/weather, music/media (incl. song aliases), tasks/reminders,
computer control, web, trading, memory/knowledge, learning, email ×3,
calendar ×3, meetings ×3, WhatsApp ×3, documents ×3, company_intel,
review_code, access. Each is registered once with an OpenAI-style JSON schema.

**Semantic memory (`services/embeddings.py`):** facts, notes and meeting
summaries are embedded with Gemini `text-embedding-004` into
`data/embeddings.db`; cosine retrieval injects the top-3 relevant items per
request. Without `GEMINI_API_KEY` it degrades to keyword search — never
crashes.

**Latency telemetry (`services/metrics.py`):** LLM/STT/TTS/tool calls are
timed into a ring buffer; `GET /api/dev/metrics` + the DevTools Latency tab
surface per-operation averages and the last agent/tool/action.

---

## 4. Technical Analysis Pipeline

```
GET /api/trading/analysis?symbol=FX:EURUSD&interval=15
      │
      ▼
chart_data.fetch_ohlcv()  ──►  yfinance candles {time, open, high, low, close, volume}
      │
      ▼
technical_analysis.analyze_candles(candles)
      ├── SMA(200), EMA(9/20/50), RSI(14, Wilder), MACD(12/26/9), Bollinger(20, 2σ)
      ├── ATR(14), Stochastic(%K14/%D3), VWAP
      ├── Patterns: Doji, Hammer, Shooting Star, Bullish/Bearish Engulfing
      ├── Trend: price-vs-EMA bias + confidence, golden/death cross
      ├── Support/resistance from swing points; 5-candle momentum
      ▼
      structured JSON + _build_summary() → natural-language spoken reply
```

The same engine powers the `technical_analysis` function tool, so the brain can
run it autonomously ("what's the trend on gold?").

---

## 5. Background Task Management (lifespan)

All background work starts and stops with the FastAPI lifespan in `app.py`
(no import-time zombie threads — this is what makes the test suite clean):

| Task | Startup | Shutdown |
|---|---|---|
| Global prices + TradingView pollers (60 s) | `start_market_pollers()` | `stop_market_pollers()` |
| Indian market poller (60 s, market-hours aware) | `start_indian_poller()` | `stop_indian_poller()` |
| Google Drive DB backup (300 s) | `start_background_gdrive_sync()` | `stop_background_gdrive_sync()` |
| Automation runner (30 s due-check) | `start_automation_runner()` | `stop_automation_runner()` |
| Temp audio cleanup (120 s) | `asyncio.create_task(cleanup_temp_audio())` | task cancelled |

All loops check a stop-event, so shutdown is prompt and tests run thread-free.

---

## 6. Technology Stack

| Component | Technology | Role / Function |
|---|---|---|
| **Frontend Core** | React 19, Vite 8, Framer Motion, GSAP | HUD dashboard, capsule panels, animations |
| **3D HUD Orb** | React Three Fiber / Three.js + GLSL shaders | Lock-screen orb, bloom/ring effects |
| **Charting Engine** | Lightweight Charts (TradingView) | Canvas OHLCV candles, volume histogram |
| **Voice & Audio** | Web Speech API → Groq Whisper `large-v3-turbo` → Gemini audio; Edge-TTS `en-IN-NeerjaNeural` / `hi-IN-SwaraNeural` | STT with barge-in + PTT; neural TTS queue with single-audio mutex |
| **Backend Framework** | FastAPI + Uvicorn (`--no-proxy-headers`) | Async ASGI REST backend — 195 operations / 168 paths |
| **Market Data** | yfinance + TradingView Scanner API | Multi-exchange quotes & candle history |
| **AI LLMs** | Groq Llama 3.3 70B + Gemini 2.5 flash + Gemini `text-embedding-004` | Intent extraction, 47-tool agentic loop, semantic memory RAG, career intelligence |
| **Email** | IMAP4_SSL + SMTP (app password) | Gmail/Outlook read + **approval-first send** |
| **Calendar** | Google Calendar API (OAuth, own `calendar_token.json`) | Read + **approval-first create**, TZ-aware |
| **WhatsApp** | FRIDAY's own Playwright driver (opt-in) | QR pairing, unread chats, **approval-first send** |
| **Documents** | pypdf / python-docx / python-pptx / openpyxl | PDF/DOCX/PPTX/XLSX/TXT extraction + Groq RAG (10 MB cap) |
| **Database Layer** | SQLite (WAL, busy_timeout, thread-safe) + thread-locked JSON | `friday_brain.db`, `friday_trading_db.sqlite`, `meetings.db`, `documents.db`, `embeddings.db`, drafts |
| **System Automation** | Python subprocess + AppleScript (whitelist + regex-sanitized) | macOS host control — auto-disabled (no-op) in Docker |
| **Career AI** | Groq Llama 3.3 70B (JSON mode) | Job scoring, cover letters, skill gap, briefing |
| **Desktop Shell** | Tauri 2 (Rust) with scoped CSP | Native desktop packaging |

---

## 7. Foundation Modules

### Permission Center (`services/permissions.py`)
- `permissions` table (capability → mode: enabled/ask/disabled) +
  `permission_audit` table.
- `require_permission(cap)` FastAPI dependency → 403 with structured detail
  (`permission`, `decision: approval_required`) when an `ask` capability has no
  valid one-time approval.
- Wired into: `trades.execute` (paper-order endpoint), `system.control`
  (brightness/volume/lock/open-app/close-app), `email.*`, `calendar.*`,
  `whatsapp.*`, `documents.*`, `web.search`, `meetings.*`, `coding.analyze`.

### Automation Engine (`services/automation.py`) + Notifications + Briefing
- `automations` table; lifespan-managed runner checks due workflows every 30 s;
  actions push into the `notifications` table.
- `briefing.py` aggregates weather / tasks / reminders / career / markets /
  inbox into a structured + spoken report.

### Multi-Agent (`services/agents.py`)
- 6 agents (career, coding, research, finance, communication, automation) with
  capability-scoped tool filters; deterministic keyword router;
  `agent.autonomy` permission gates autonomous action.

### Knowledge OS, Learning Coach, Life Memory, Developer Mode
- `kb_notes` + `project_memory` (second brain, auto-categorized, token/prefix
  search, auto-embedded).
- `timeline_events` (memory timeline, period summaries, auto-snapshot) +
  `goals` (progress %, skill gaps, auto-done at 100%).
- `life_memories` triples (subject → relation → target) + natural recall.
- `learning_log` / `learning_goals` (streaks, weekly targets, reminders).
- Owner-only `/api/dev/*`: overview, memory viewer, log tail, safe config
  (booleans only), in-process API tester via `httpx.ASGITransport`.

---

## 8. Database Schema — Career OS (in `friday_brain.db`)

All Career OS tables live in the unified `friday_brain.db` (WAL mode):

| Table | Purpose |
|---|---|
| `career_preferences` | Salary, remote type, tech stack, blacklisted companies, job types |
| `career_profile` | Personal profile — sensitive fields Fernet-encrypted at rest |
| `career_resumes` | Multi-version resumes with content JSON (AI-parsed sections) |
| `career_jobs` | Scraped/added job listings with match-score JSON |
| `career_applications` | Application tracking with status, notes, follow-up dates |
| `career_cover_letters` | Generated cover letters linked to jobs and resumes |
| `career_recruiters` | Recruiter CRM with contact info and notes |
| `career_interviews` | Interview scheduling, stage, outcome, prep questions |
| `career_companies` | Company tracker with blacklist reason |
| `career_activity_log` | Audit log of all Career OS actions |

Other DBs: `friday_trading_db.sqlite` (watchlist, chart drawings),
`meetings.db`, `documents.db`, `embeddings.db`, plus JSON draft/state stores.

---

## 9. Communication Center Architecture

All communication modules follow one pattern — **Brain → Tool Router → Agent →
Permission → Approval-first action**:

```
Voice: "email rahul@x.com that I'll reach in 20"
   │
   ▼
brain_v2 agentic loop → function_engine.dispatch("send_email", …)
   │
   ▼
email_agent.create_draft()  → server-side draft (15-min TTL, preview only)
   │
   ▼
reply surfaces action="email_confirm" + email_draft_id
   │
   ▼
Frontend: PendingApprovalCard shows the preview → user says "yes" / clicks Send
   │
   ▼
POST /api/email/send (requires fresh draft + one-time email.send approval)
```

| Module | Read | Write (always approval-first) | Storage |
|---|---|---|---|
| **Email Agent** | IMAP unread/search/summary/priority | SMTP via server-side draft | `data/email_drafts.json` |
| **Calendar Agent** | Google Calendar today/upcoming/search | Insert via server-side draft | `data/calendar_drafts.json` |
| **Meeting Assistant** | SQLite list/search/action-items | Whisper+LLM → SQLite + Knowledge mirror | `data/meetings.db` |
| **WhatsApp Agent** | Playwright driver chats/search | Driver send via server-side draft | `data/whatsapp_drafts.json` + session dir |
| **Document AI** | SQLite full-text search | Groq Q&A/summary/compare | `data/documents.db` (text only) |
| **Company Intel** | Web search + Career OS data | Groq-composed brief | stateless |
| **Coding AI** | — | Groq review/bugs/tests/docs/refactor | stateless |

Shared safeguards: drafts expire after 15 min; `send_*`/`create_*` tools can
never send without a previewed draft; the LLM system prompt forbids claiming a
send that was only previewed.

---

## 10. Voice Command Routing

Workspace navigation is handled by `useOrbState.jsx` (client-side) and the
`navigation_handler` fast-path (server-side fallback):

| Command | Result |
|---|---|
| "trading" / "open trading" | Quantum Trading Workstation |
| "dashboard" / "home" | HUD Dashboard |
| "career" / "job portal" | Career OS |
| "lock" / "lock yourself" | Lock Screen (macOS host) |
| "open vscode" / "open chrome" | Launch app on macOS host (sanitized) |
| "open my gym song" | Song alias → Spotify playback |

---

## 11. Security Model

1. **Owner Authentication** — loopback clients are the owner; non-localhost
   callers must present `FRIDAY_API_TOKEN` via `X-FRIDAY-Token` (constant-time
   compare, 401 otherwise). `is_boss` is never accepted from the client body.
2. **Proxy-Header Spoofing Defense** — uvicorn runs with `--no-proxy-headers`
   in every deployment path (Dockerfile CMD, start.sh, app.py) so
   client-supplied `X-Forwarded-For` / `X-Real-IP` are ignored. Verified live:
   a remote caller sending `X-Forwarded-For: 127.0.0.1` gets 401.
3. **Full read-path gating** — every personal-data read endpoint (todos,
   reminders, knowledge, timeline, goals, learning, life-memory,
   notifications, briefing, proactive, watchlist, chart drawings, spotify
   state, system telemetry, TTS, web search, permissions, agents) requires
   owner auth. Enforced with regression tests.
4. **Permission Center** — 24 capabilities, modes enabled/ask/disabled,
   audit-logged; high-stakes capabilities default to `ask`.
5. **CORS Isolation** — explicit origin allowlist via `ALLOWED_ORIGINS`
   (defaults: localhost dev ports + 8080), explicit methods incl. PATCH,
   explicit headers, no wildcards with credentials.
6. **AppleScript & Shell Sanitization** — app names filtered via strict regex
   (`re.sub(r'[^a-zA-Z0-9\s._\-]', '', app_name)`); whitelist-routed commands.
7. **Encryption at Rest** — sensitive career fields Fernet-encrypted; browser
   vault PBKDF2-250k + AES-GCM-256; passphrase never persisted.
8. **Honest Status Reporting** — platform verification returns `needs_login`
   until a real session is captured — no fabricated "connected" responses.
9. **Rate Limiting** — per-IP sliding window on chat, STT, meetings, career AI
   (Groq-consuming) endpoints.
10. **Telegram Access Control** — `TELEGRAM_OWNER_ID` gates the bot.
11. **No Blind Career Submissions** — mandatory human confirmation before any
    application submission.
12. **Approval-First Communication** — email/WhatsApp sends and calendar
    creates only act on server-side previewed drafts (15-min TTL) with a
    one-time permission grant.
13. **Docker Auth** — every container request is non-loopback, so the frontend
    injects `X-FRIDAY-Token` (baked at build time from `FRIDAY_API_TOKEN`,
    which compose requires).
14. **Data Integrity** — SQLite WAL + busy_timeout; todos/reminders/Spotify
    cache lock read-modify-write; upload caps (resume 5 MB, STT 10 MB,
    documents 10 MB, meetings 25 MB) with 413 responses.

---

## 12. Deployment Topologies

| Topology | Components | Notes |
|---|---|---|
| **Native macOS** (`start.sh`) | uvicorn :8000 (`--no-proxy-headers`) + Vite dev :5173 | Full system automation (brightness, volume, apps, Spotify) |
| **Docker Compose** | nginx :8080 → FastAPI :8000 | Same-origin proxy (no CORS); `./backend/data` volume persists; `FRIDAY_API_TOKEN` baked into the frontend build |
| **Render** (`render.yaml`) | FastAPI container, `${PORT:-8000}` | `FRIDAY_MODE=demo` is opt-in (never default); data is ephemeral unless a persistent disk is mounted at `/app/data` |
| **Vercel / static** | `vercel.json` SPA rewrite | Build with `VITE_API_BASE_URL` + `VITE_FRIDAY_TOKEN` |
| **Tauri 2** | Rust shell + webview | Scoped CSP; desktop packaging |

---

*Last Updated:* August 2026
*Lead Architect:* Prem (Prathvi Sahu) & F.R.I.D.A.Y.
