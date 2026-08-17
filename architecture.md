# F.R.I.D.A.Y. Technical Architecture

**Document Purpose**
This document describes the technical architecture of the **F.R.I.D.A.Y. v5.0** personal AI desktop and mobile operating system, detailing component hierarchy, data flows, LLM orchestration, single-audio mutex locking, real-time market data pipelines, and the **Career Intelligence Center (Career OS)** — fully operational as of August 2026.

---

## 1. Core Architecture & System Vision

FRIDAY is built for **Prem** (Prathvi Sahu) as a voice-first personal operating system:

1. **Dual-Engine LLM Core**:
   - **Fast-Path Engine**: Groq (`llama-3.3-70b-versatile`) delivering low-latency voice responses and direct system action execution.
   - **Reasoning & Failover Engine**: Google Gemini 2.5 for complex multi-turn logic, fallback scenarios, and document analysis.

2. **Single-Audio Mutex & Monotonic Speech Generation Lock**:
   - **Deterministic Mutex**: Monotonic `audioGenRef` sequence counter enforces that only one audio source can play at any given moment.
   - **Instant Purge**: New incoming voice replies or barge-in triggers instantly cancel and purge in-flight audio pipelines.
   - **Primary TTS**: Microsoft Edge-TTS neural voices `en-IN-NeerjaNeural` (English) / `hi-IN-SwaraNeural` (Hindi).
   - **Browser Fallback Gating**: `ttsService.js` prefers female voices when the Edge-TTS backend is unreachable.

3. **Stark Industries 17-in-1 Sliding Dashboard**:
   - **Holographic Glassmorphic HUD**: Real-time capsule search, category filter pills (`AI Tools`, `System`, `Productivity`, `Communication`, `Security`, `Utilities`), and live armed/active capsule telemetry.
   - **Dedicated Workspace Navigation**: 1-tap workspace activation for Career OS, Quantum Trading Station, and DevTools.

4. **Quantum Trading Workstation**:
   - **TradingView Lightweight Charts Engine**: High-performance canvas-rendered candlestick charts with Volume histograms and full-screen responsive viewports on mobile devices.
   - **OHLCV Data Pipeline (`/api/trading/ohlcv`)**: Yahoo Finance (`yfinance`) supporting 7 resolutions (`1m`, `5m`, `15m`, `30m`, `1h`, `1D`, `1W`).
   - **Multi-Asset Watchlist & SQLite Persistence**: 5000+ instruments across NSE/BSE, Forex, Crypto, US Equities. Stored in `friday_trading_db.sqlite`.
   - **Live Polling Loop**: Intraday charts update every 30 seconds.

5. **Career Intelligence Center (Career OS)** — ✅ **Fully Operational**:
   - **AI Engine** (`career_intelligence.py`): Groq Llama 3.3 70B for job match scoring, cover letter generation, interview questions, skill gap analysis, daily briefing, and preference learning.
   - **Database Layer** (`career_db.py`): 10 SQLite tables in `friday_brain.db` (WAL mode).
   - **REST API** (`routers/career.py`): 42 endpoints across 31 paths at `/api/career/*`.
   - **React Frontend**: 12 fully functional modules, lazy-loaded, with mobile horizontal sub-navigation.
   - **Voice Integration**: `"career"` command routes to Career OS via `useOrbState.jsx`.

6. **Native Android & Mobile Ecosystem**:
   - **Push-to-Talk (PTT)**: Continuous speech capture via Spacebar hold (desktop) or Pointer Hold-to-Talk (mobile) with **0ms release latency**.
   - **Android Hardware Release**: `visibilitychange` listener immediately shuts down microphone streams on tab blur/minimize to prevent Android audio subsystem conflicts.
   - **Spotify Mobile Deep-Linking**: Direct URL navigation opening the native Android Spotify app with zero blank tabs.

---

## 2. System Component Diagram

```
+-----------------------------------------------------------------------+
|                    React 19 Frontend (friday-ui)                      |
|                                                                       |
|  [useSpeech PTT] --> [ttsService: Single Audio Mutex]                 |
|        |                    |              |              |           |
|  [LockScreen]        [Stark 17-in-1] [TradingWS]    [Career OS]       |
|                       Dashboard       Full-screen    Horizontal       |
|                       + HUD Stream    Mobile Charts  Subnav           |
+-----------------------------------------------------------------------+
|                                                                       |
|  [useSpeech STT] --> [useOrbState: workspace router]                  |
|        |                    |              |              |            |
|  [LockScreen]        [Dashboard]    [TradingWS]    [Career OS]        |
|                       + HUD cards    Lightweight    CareerOS.jsx       |
|                                      Charts         12 modules         |
+-----------------------------------------------------------------------+
                               | HTTP / JSON (REST) via Vite proxy
                               v
+-----------------------------------------------------------------------+
|                 FastAPI Python Backend (:8000)                        |
|                                                                       |
|  [app.py]  — thin wiring: CORS, static mount, lifespan lifecycle      |
|     ├── routes/chat.py        chat, memory, speech/correct+transcribe |
|     ├── routes/email.py       Email Agent (IMAP+SMTP, draft→confirm)  |
|     ├── routes/calendar.py    Calendar Agent (Google, draft→confirm)  |
|     ├── routes/meetings.py    Meeting Assistant (Whisper→LLM→todos)   |
|     ├── routes/whatsapp.py    WhatsApp Agent (Playwright driver)      |
|     ├── routes/documents.py   Document AI (upload→ask/summarize)      |
|     ├── routes/company.py     Company Intelligence                    |
|     ├── routes/coding.py      Coding AI (review/bugs/tests/docs)      |
|     ├── routes/system.py      display/brightness/volume/lock, apps    |
|     ├── routes/spotify.py     current-track, seek, duck/unduck        |
|     ├── routes/todos.py       todo CRUD (thread-locked)               |
|     ├── routes/utilities.py   tts, weather, search, reminders, gdrive |
|     ├── routes/watchlist.py   watchlist CRUD + default seed           |
|     ├── routes/trading.py     ohlcv, live-prices, analysis, search    |
|     ├── routes/devtools.py    overview, metrics, logs, config, tester |
|     └── routers/career.py     Career OS (/api/career/*)               |
|                                                                       |
|  Services Layer:                                                       |
|  ├── brain_v2.py + function_engine.py  (v4 agentic brain, 41 tools)  |
|  ├── brain/                     (Modular Brain Package with Plugins)  |
|  │   ├── engine.py              (Cognitive Decision Orchestrator)     |
|  │   ├── prompt_builder.py      (Dynamic System Prompt & Context)     |
|  │   ├── clients.py             (Groq & Gemini Singletons)            |
|  │   ├── constants.py           (System Prompts & Action Registry)    |
|  │   └── handlers/              (Fast-Path Handlers, <15ms response)  |
|  │       ├── security_handler.py    (Permissions, Guest Delegation)   |
|  │       ├── navigation_handler.py  (Career, Trading, Dashboard)      |
|  │       ├── agents_handler.py      (Meetings, WhatsApp, Email, Docs) |
|  │       ├── hardware_handler.py    (Brightness, Dark Mode, Lock)     |
|  │       ├── utilities_handler.py   (Weather, Reminders, Tasks, Time) |
|  │       └── media_handler.py       (Spotify Playback, Vol, Aliases)  |
|  ├── embeddings.py              (Gemini RAG over facts/notes/meetings)|
|  ├── metrics.py                 (LLM/STT/TTS/tool latency ring buffer)|
|  ├── email_agent / calendar_agent / meeting_agent / whatsapp_agent   |
|  ├── document_agent / coding_agent / company_intelligence             |
|  ├── stt.py                     (Groq Whisper large-v3-turbo + Gemini)|
|  ├── job_scraper.py             (LinkedIn Scraper with Date Filters)  |
|  ├── technical_analysis.py      (real TA from live OHLCV)             |
|  ├── telegram_bot.py            (remote phone interface)              |
|  ├── learning_engine.py         (habits, corrections, RAG memory)     |
|  ├── career_db.py               (career tables, upsert & purge, vault)|
|  ├── chart_data.py              (shared OHLCV fetch + symbol search)  |
|  ├── market_data.py / indian_market_data.py (lifespan-managed pollers)|
|  ├── system_control.py          (macOS AppleScript + Spotify, locked) |
|  ├── auth.py / ratelimit.py     (owner auth + per-IP limiting)        |
|  └── tts.py                     (Edge-TTS + temp audio cleanup)       |
|                                                                       |
|  Databases:                                                           |
|  ├── friday_brain.db        (AI memory + Career OS, WAL, thread-safe) |
|  ├── friday_trading_db.sqlite (Trading watchlist & chart state, WAL)  |
|  ├── meetings.db / documents.db / embeddings.db                       |
|  └── email_drafts.json / calendar_drafts.json / whatsapp_drafts.json  |
+-----------------------------------------------------------------------+
        |                    |                        |
        v                    v                        v
[Groq Llama 70B]   [Google Gemini 2.5]      [macOS / Spotify / Open-Meteo / Telegram]
```

---

## 3. Smart Function Calling AI Brain (v4)

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
      │     • top-3 SEMANTIC memories (embeddings.semantic_context → Gemini
      │       text-embedding-004 RAG over facts/notes/meetings)
      │     • the user's request
      │
      ├── AGENTIC LOOP (max 4 steps):
      │     Groq (GROQ_MODEL, default llama-3.3-70b-versatile) with
      │     tools=function_engine.get_tools_schema()
      │       → ALL tool_calls executed via dispatch(), results appended as
      │         tool messages → loop until the model answers
      │       → send_*/create_* tools surface email_confirm /
      │         calendar_confirm / whatsapp_confirm approval actions
      │
      ├── Step 2: Gemini failover — structured JSON {"reply", "function", "args"}
      │            (also receives history + semantic memory context)
      │
      └── Step 3: legacy brain.respond() regex fallback (always works)
```

**The tool registry (`function_engine.py`):** **41 registered functions** across
12 categories — time/weather, music, tasks/reminders, computer control, web,
trading, memory/knowledge, learning, **email ×3**, **calendar ×3**,
**meetings ×3**, **whatsapp ×3**, **documents ×3**, **company_intel**,
**review_code**, access. Each capability is registered once with an OpenAI-style
JSON schema; adding a feature no longer requires inserting a regex among ~30
patterns in `brain.py`.

**Semantic memory (`services/embeddings.py`):** facts (on `save_fact`), knowledge
notes (on `add_note`) and meeting summaries (via the note mirror) are embedded
with Gemini `text-embedding-004` into `data/embeddings.db`; cosine retrieval
injects the top-3 relevant items per request. Without `GEMINI_API_KEY` the layer
degrades to keyword search — never crashes.

**Latency telemetry (`services/metrics.py`):** LLM/STT/TTS/tool calls are timed
into a ring buffer; `GET /api/dev/metrics` + the DevTools Latency tab surface
per-op averages and the last agent/tool/action.

## 4. Technical Analysis Pipeline (v3)

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

## 5. Background Task Management (lifespan)

Previously, background threads were spawned at module import time
(`market_data.py`, `indian_market_data.py`), making testing impossible and
leaving zombie threads. All background work now starts and stops with the
FastAPI lifespan in `app.py`:

| Task | Startup | Shutdown |
|---|---|---|
| Global prices + TradingView pollers | `start_market_pollers()` | `stop_market_pollers()` |
| Indian market poller | `start_indian_poller()` | `stop_indian_poller()` |
| Google Drive DB backup (300 s) | `start_background_gdrive_sync()` | `stop_background_gdrive_sync()` |
| Temp audio cleanup (120 s) | `asyncio.create_task(cleanup_temp_audio())` | task cancelled |

All loops check a stop-event, so shutdown is prompt and tests run thread-free.

## 6. Technology Stack Specification

| Component | Technology | Role / Function |
|---|---|---|
| **Frontend Core** | React 19, Vite 8, Framer Motion | Dynamic HUD dashboard, panel routing, animations |
| **Charting Engine** | Lightweight Charts (TradingView) | Canvas rendering, OHLCV candles, Volume histogram |
| **Voice & Audio** | Web Speech API (instant) + **Groq Whisper `whisper-large-v3-turbo` fallback (free tier)** + Gemini audio last resort + Edge-TTS `en-IN-NeerjaNeural` / `hi-IN-SwaraNeural` | STT input w/ **barge-in** + **push-to-talk**, Neural TTS output queue |
| **Backend Framework** | FastAPI + Uvicorn | Async ASGI REST backend (:8000), 173 routes |
| **Market Data** | yfinance + TradingView Scanner API | Multi-exchange market quotes & candle history |
| **AI LLMs** | Groq Llama 3.3 70B + Gemini 2.5 + Gemini `text-embedding-004` | Intent extraction, agentic tool loop, semantic memory RAG, career intelligence |
| **Email** | IMAP4_SSL + SMTP (app password) | Gmail/Outlook read + **approval-first send** |
| **Calendar** | Google Calendar API (OAuth, own `calendar_token.json`) | Read + **approval-first create**, TZ-aware (Docker `TZ`) |
| **WhatsApp** | FRIDAY's own Playwright driver (opt-in) | QR pairing, unread chats, **approval-first send** (experimental) |
| **Documents** | pypdf / python-docx / python-pptx / openpyxl | PDF/DOCX/PPTX/XLSX/TXT extraction + Groq RAG Q&A |
| **Database Layer** | SQLite (WAL) + JSON (thread-locked) | `friday_brain.db`, `friday_trading_db.sqlite`, `meetings.db`, `documents.db`, `embeddings.db`, drafts |
| **System Automation** | Python `subprocess` + AppleScript | macOS application management, system volume (auto-disabled in Docker) |
| **Career AI** | Groq Llama 3.3 70B (JSON mode) | Job scoring, cover letters, skill gap, briefing |
| **Typography** | Inter (Google Fonts) | Career OS UI — professional, clean typography |

---

## 7. v3.1 Foundation Modules

### Permission Center (`services/permissions.py`)
- `permissions` table (capability → mode: enabled/ask/disabled) + `permission_audit` table.
- Enforcement: `require_permission(cap)` FastAPI dependency → 403 with structured
  detail (`permission`, `decision: approval_required`) when an `ask` capability
  has no valid one-time approval.
- Wired into: `trades.execute` (paper-order endpoint), `system.control`
  (brightness/volume/lock/open-app/close-app), plus a ready catalog for
  email/whatsapp/phone/jobs/files.

### Automation Engine (`services/automation.py`) + Notifications + Briefing
- `automations` table; runner thread (lifespan-managed) checks due workflows
  every 30 s; actions push into `notifications` table.
- `briefing.py` aggregates weather/tasks/reminders/career/markets/inbox.

### Multi-Agent (`services/agents.py`)
- 6 agents with capability-scoped tool filters; keyword router (deterministic);
  `agent.autonomy` permission gates autonomous action.

## 8. v3.2 Foundation Modules

### Learning Coach (`services/learning.py`)
- `learning_goals` (seeded tracks + weekly targets) + `learning_log` (sessions).
- Streak math (consecutive calendar days), weekly goal progress, `learning_check`
  automation action → Notification Center when idle ≥ 3 days.

### Life Memory (`services/life_memory.py`)
- `life_memories` triples (subject → relation → target) + token/prefix search.
- `remember_fact` writes both facts and triples; `search_memories` function tool.

### Developer Mode (`routes/devtools.py`)
- Owner-only `/api/dev/*`: overview, memory viewer, log tail (file + ring buffer),
  safe config (booleans only, never values), in-process API tester via
  `httpx.ASGITransport`.

## 9. v3.3 Knowledge OS

- `kb_notes` (type/title/content/tags/project/source) + `project_memory`
  (project × section) — second brain with auto-categorization and
  token/prefix search.
- `timeline_events` (event/category/date/detail) — memory timeline with
  period summaries ("last month", "this year") + auto-snapshot from existing
  application/learning data.
- `goals` (title/category/target/current/unit/deadline/status/skill_gaps/
  resources) — goal manager with auto-done at 100%.
- Function tools: `remember_idea`, `search_notes`, `log_milestone`,
  `update_goal` (engine now 41 tools).
- Explainable AI: career recommendations carry `reasons[]`.

## 10. Database Schema — Career OS Tables (in `friday_brain.db`)

All 10 Career OS tables live in the same unified `friday_brain.db` database (WAL mode):

| Table | Purpose |
|---|---|
| `career_preferences` | Salary, remote type, tech stack, blacklisted companies, job types |
| `career_profile` | Personal vault — name, email, phone, LinkedIn, GitHub, portfolio |
| `career_resumes` | Multi-version resumes with ATS score, content JSON |
| `career_jobs` | Scraped/added job listings with match score JSON |
| `career_applications` | Application tracking with status, notes, follow-up dates |
| `career_cover_letters` | Generated cover letters linked to jobs and resumes |
| `career_recruiters` | Recruiter CRM with contact info and notes |
| `career_interviews` | Interview scheduling, stage, outcome, prep questions |
| `career_companies` | Company tracker with blacklist reason |
| `career_activity_log` | Audit log of all Career OS actions |

---

## 11. Active API Endpoint Reference

### Core Endpoints
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat/text` | Main voice/text AI brain entrypoint (owner-only, rate-limited) |
| `POST` | `/api/speech/transcribe` | STT: Groq Whisper `large-v3-turbo` (free tier) → Gemini fallback (owner-only) |
| `GET` | `/api/memory` / `POST` `/api/memory` | Long-term memory read/write (owner-only) |
| `POST` | `/api/permission` | Grant/revoke guest access (owner-only) |
| `GET` | `/api/proactive` | Time-aware proactive suggestion |
| `POST` | `/api/tts` | Edge-TTS speech generation (relative audio URL) |
| `GET` | `/api/email/unread` · `/summary` · `/search` | Email read (permission `email.read`) |
| `POST` | `/api/email/draft` · `/send` · `/cancel` | Email **approval-first send** (`email.send`) |
| `GET` | `/api/calendar/today` · `/upcoming` · `/search` | Calendar read (`calendar.read`) |
| `POST` | `/api/calendar/draft` · `/create` · `/cancel` | Calendar **approval-first create** (`calendar.write`) |
| `POST` | `/api/meetings/process` · `/transcribe` | Meeting summaries from transcript / audio (Whisper) |
| `GET` | `/api/meetings` · `/search` · `/action-items` · `/{id}` | Meeting records & action items |
| `POST` | `/api/meetings/{id}/todos` | Push action items into Todos |
| `GET` | `/api/whatsapp/status` · `/qr` | WhatsApp driver state + pairing QR (opt-in) |
| `GET` | `/api/whatsapp/chats` · `/search` | WhatsApp read (`whatsapp.read`) |
| `POST` | `/api/whatsapp/draft` · `/send` · `/cancel` | WhatsApp **approval-first send** (`whatsapp.send`) |
| `POST` | `/api/documents/upload` | Document ingestion (PDF/DOCX/PPTX/XLSX/TXT, 10 MB cap) |
| `GET` | `/api/documents` · `/search` · `/{id}` | Document list / search / full text |
| `POST` | `/api/documents/{id}/ask` · `/summarize` · `/compare` | Document Q&A (Groq RAG) |
| `GET` | `/api/company/intel?name=` | Company Intelligence brief |
| `POST` | `/api/coding/review` · `/bugs` · `/explain` · `/tests` · `/docs` · `/refactor` | Coding AI on pasted code |
| `GET` | `/api/dev/metrics` | Latency dashboard (LLM/STT/TTS/tool averages) |
| `GET` | `/api/weather` | Open-Meteo weather with IP geolocation |
| `GET` | `/api/weather` | Open-Meteo weather with IP geolocation |
| `POST` | `/api/search` | DuckDuckGo instant-answer search |
| `GET/POST` | `/api/reminders` | Active timers / set a reminder (write = owner-only) |
| `GET/POST` | `/api/todos` | Fetch / create persistent todo tasks (write = owner-only) |
| `PATCH` | `/api/todos/{id}/toggle` · `/text` | Toggle / edit todo (owner-only) |
| `DELETE` | `/api/todos/{id}` · `/done` | Delete todos (owner-only) |
| `GET` | `/api/system/stats` | Telemetry: CPU, RAM, Disk, Power |
| `GET/POST` | `/api/system/display/*` | Brightness, dark mode, volume, mute, lock (write = owner-only) |
| `POST` | `/api/open-app` · `/close-app` | Launch / quit macOS apps (owner-only) |
| `GET` | `/api/spotify/current-track` | Active Spotify playback telemetry |
| `POST` | `/api/spotify/seek` · `duck` · `unduck` | Seek / volume ducking (owner-only) |
| `GET/POST` | `/api/watchlist` | Retrieve/add watchlist items (write = owner-only) |
| `DELETE` | `/api/watchlist/{symbol}` | Delete watchlist item (owner-only) |
| `GET` | `/api/trading/ohlcv` | Historical & intraday candle data |
| `GET` | `/api/trading/analysis` | **v3:** real technical analysis (RSI, MACD, patterns…) |
| `GET` | `/api/trading/live-prices` · `indian-prices` | Real-time market prices |
| `GET` | `/api/trading/search` | Symbol search (NSE/BSE/FX/Crypto/US) |
| `GET/POST` | `/api/trading/chart-db` | Chart drawings persistence |
| `GET` | `/api/gdrive/status` | Drive backup status |
| `POST` | `/api/gdrive/sync-now` | Trigger immediate backup (owner-only) |

### Career OS Endpoints (`/api/career/*`)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/career/dashboard` | Daily briefing, stats, recommendations, activity |
| `GET/PUT` | `/api/career/preferences` | Get/update career preferences |
| `POST` | `/api/career/learn` | Natural language preference learning |
| `GET/PUT` | `/api/career/profile` | Get/update personal vault |
| `GET/POST` | `/api/career/resumes` | List/create resumes |
| `GET/PUT` | `/api/career/resumes/{id}` | Get/update specific resume |
| `POST` | `/api/career/resumes/{id}/duplicate` | Duplicate a resume |
| `POST` | `/api/career/resumes/{id}/recommend` | Mark resume as recommended |
| `GET/POST` | `/api/career/jobs` | List/add job opportunities |
| `GET/PUT` | `/api/career/jobs/{id}` | Get/update job details |
| `POST` | `/api/career/jobs/analyze` | AI match analysis for a job |
| `GET/POST` | `/api/career/applications` | List/create applications |
| `PUT` | `/api/career/applications/{id}` | Update application (status, notes) |
| `POST` | `/api/career/cover-letter` | Generate AI cover letter |
| `GET` | `/api/career/cover-letters` | List generated cover letters |
| `GET/POST` | `/api/career/recruiters` | List/add recruiters |
| `PUT` | `/api/career/recruiters/{id}` | Update recruiter notes |
| `GET/POST` | `/api/career/interviews` | List/schedule interviews |
| `PUT` | `/api/career/interviews/{id}` | Update interview outcome |
| `POST` | `/api/career/interviews/questions` | Generate AI prep questions |
| `GET` | `/api/career/companies` | List tracked companies |
| `POST` | `/api/career/companies/blacklist` | Blacklist a company |
| `POST` | `/api/career/companies` | Add a company |
| `GET` | `/api/career/analytics` | Career analytics data |
| `GET` | `/api/career/skill-gap` | AI skill gap analysis |
| `GET` | `/api/career/activity` | Career activity log |

---

## 12. Communication Center Architecture

All communication modules follow one pattern — **Planner → Tool Router → Agent →
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
| **WhatsApp Agent** | Playwright driver chats/search | Driver send via server-side draft | `data/whatsapp_drafts.json` + `data/whatsapp_session/` |
| **Document AI** | SQLite full-text search | Groq Q&A/summary/compare | `data/documents.db` (text only) |
| **Company Intel** | Web search + Career OS data | Groq-composed brief | stateless |
| **Coding AI** | — | Groq review/bugs/tests/docs/refactor | stateless |

Shared safeguards: drafts expire after 15 min; `send_*`/`create_*` tools can
never send without a previewed draft; the LLM system prompt forbids claiming
a send that was only previewed.

## 13. Voice Command Routing


All workspace navigation is handled by `useOrbState.jsx`:

| Command | F.R.I.D.A.Y. Response | Routes To |
|---|---|---|
| `"trading"` | "Opening trading systems now." | Quantum Trading Workstation |
| `"dashboard"` | "Displaying the dashboard." | HUD Dashboard |
| `"career"` | "Opening your Career Intelligence Center, Boss." | Career OS |
| `"lock"` | "Securing the system and locking down access." | Lock Screen |
| `"vscode"` | "Opening Visual Studio Code." | VS Code (macOS) |
| `"browser"` | "Opening your browser." | Browser (macOS) |

---

## 14. Security & Protection Guidelines

1. **Owner Authentication**: Loopback clients are the owner; non-localhost callers must present `FRIDAY_API_TOKEN` via the `X-FRIDAY-Token` header (401 otherwise). `is_boss` is never accepted from the client body. Chat, machine-control, memory, and the whole `/api/career/*` router are owner-gated.
2. **Proxy-Header Spoofing Defense**: uvicorn runs with `--no-proxy-headers` so client-supplied `X-Forwarded-For` / `X-Real-IP` are ignored — otherwise a remote caller could spoof `127.0.0.1` and bypass auth.
3. **CORS Isolation**: Restricts API calls to authorized local frontend origins (`http://localhost:5173`, `http://127.0.0.1:5173`, plus `:3000` variants) with explicit methods/headers (no wildcards).
4. **AppleScript & Shell Sanitization**: App names and user inputs filtered via strict regex (`re.sub(r'[^a-zA-Z0-9\s._\-]', '', app_name)`).
5. **Defensive Data Handling**: All database and dictionary operations use safe fallback getters (`dict.get()`).
6. **Adaptive Polling Backoff**: Background pollers scale back during network interruptions.
7. **Career Data Privacy & Encryption at Rest**: Sensitive career profile fields (passwords, tokens, API keys) are Fernet-encrypted before writing to `friday_brain.db`; the key lives in `FRIDAY_VAULT_KEY` or `backend/data/.vault_key` (chmod 600).
8. **Honest Status Reporting**: Platform account verification returns `needs_login` until a real session is captured — no fabricated "connected" responses.
9. **Rate Limiting**: LLM-backed endpoints (chat + career AI) are limited per IP to protect Groq/Gemini credits.
10. **Telegram Access Control**: `TELEGRAM_OWNER_ID` — only the owner's Telegram id can interact with the bot.
11. **No Blind Career Submissions**: Career OS enforces a mandatory human confirmation step before any application submission.
12. **Approval-First Communication**: email/WhatsApp sends and calendar creates only act on server-side previewed drafts (15-min TTL) with a one-time permission grant; the LLM is instructed to never claim a send that was only previewed.
13. **Docker Auth**: in containers every request arrives from the bridge network, so the frontend injects `X-FRIDAY-Token` (baked at build time) and `FRIDAY_API_TOKEN` is required via compose.
14. **Data Integrity**: todos, reminders and the Spotify cache lock their read-modify-write cycles; uploaded documents are stored as extracted text only (originals discarded).
---

*Last Updated:* August 2026
*Lead Architect:* Prem (Prathvi Sahu) & F.R.I.D.A.Y.
