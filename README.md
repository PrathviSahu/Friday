# ⚡ F.R.I.D.A.Y. v3.0 — Voice-Controlled AI Operating System & Quantum Trading Workstation

> **F.R.I.D.A.Y.** is a full-stack, voice-controlled AI desktop operating system inspired by Iron Man's J.A.R.V.I.S., built using **React 19**, **Vite 8**, **Python FastAPI**, **Groq (Llama 3.3 70B)**, and **Google Gemini 2.5**.

---

## 🆕 What's New in v3.0

| Feature | Description |
|---|---|
| **Function Calling AI Brain** | `brain_v2.py` + `function_engine.py` — the LLM picks from 18 registered tools instead of 30 fragile regex patterns |
| **Real Technical Analysis Engine** | `technical_analysis.py` — RSI, MACD, Bollinger, ATR, Stochastic, VWAP, candlestick patterns, support/resistance from live OHLCV |
| **Telegram Bot Interface** | `telegram_bot.py` — control FRIDAY from your phone anywhere (`/time`, `/weather`, `/tasks`, `/market`, `/analyze`, free-form chat) |
| **Permission Center** | Persisted capability policy (`enabled` / `ask` / `disabled`) + one-time approvals + enforcement on every sensitive endpoint + HUD panel |
| **Automation Engine** | Scheduled workflows (`briefing`, `job_scan`, `market_summary`) with a lifespan-managed runner → Notification Center |
| **Smart Daily Briefing** | Aggregates weather, tasks, reminders, career pipeline, markets, notifications into `GET /api/briefing` |
| **Multi-Agent Framework** | 6 specialized agents (career, coding, research, finance, communication, automation) with filtered tool sets |
| **Learning Coach** | Practice tracking (DSA / Java / AWS / System Design / interview prep), streaks, weekly goals, gentle "haven't practiced in N days" reminders |
| **Life Memory (graph-lite)** | Searchable (subject → relation → target) memory: "Boss loves cold brew", "don't apply below 7 LPA" |
| **Developer Mode** | HUD panel: overview counts, memory viewer, log tail, safe config inspector, in-process API tester |
| **Second Brain (Knowledge OS)** | Auto-categorized notes (ideas, meetings, research, code, decisions…), full-text search, per-project memory |
| **AI Memory Timeline** | Chronological milestones — "what changed last month?", "progress this year" |
| **Goal Manager** | Goals → tasks → progress → deadlines → skill gaps → resources, voice-trackable |
| **Explainable AI** | Career recommendations now include "reasons" (why I suggested this) |
| **Modular API Routes** | Monolithic `app.py` (667 lines) split into 7 focused route modules under `backend/routes/` |
| **Lifespan-managed Background Tasks** | Market pollers, gdrive sync & audio cleanup now start/stop cleanly with the FastAPI lifespan (no import-time zombie threads) |
| **Thread-safe SQLite** | `check_same_thread=False` + WAL + `busy_timeout` across all DB layers, `_db_lock` serializes writes |
| **SQL Injection Fix** | `update_job_status` now fully parameterized |
| **Startup Env Validation** | Clear warnings for every missing/stubbed API key |

---

## 📖 Overview

**F.R.I.D.A.Y.** is a comprehensive personal AI assistant designed to streamline career management, trading, daily productivity, media control, and macOS system automation.

Key architectural pillars:
- **Function-Calling AI Brain (v3)**: Groq Llama 3.3 70B receives 18 tool schemas and dispatches to real handlers; Gemini failover; legacy regex brain retained as final fallback.
- **Dual-Engine Hybrid AI Brain**: Low-latency voice interactions via Groq Llama 3.3 70B + complex reasoning & fallbacks via Google Gemini 2.5.
- **Female Voice Engine**: Microsoft Edge-TTS neural voices (`en-IN-NeerjaNeural` for English, `hi-IN-SwaraNeural` for Hindi) with a browser fallback filter that prefers female voices.
- **Career Intelligence Center (Career OS)**: A fully operational AI-powered career operating system — not a job portal. Analyzes opportunities, drafts cover letters, tracks interviews, manages resumes, and learns your preferences. Never submits without your final approval.
- **Quantum Trading Workstation**: TradingView Lightweight Charts with live OHLCV candle streaming across 7 timeframes (`1m` to `1W`) for 5000+ symbols (NSE/BSE Indian Equities, Forex, Crypto, US Stocks), 30-second live auto-polling, a drag-and-drop watchlist backed by SQLite persistence, and **real technical analysis on demand**.
- **Zero-Config Spotify Automation**: Control music playback, track search, volume, and progress seek bar via an anonymous web player token without manual OAuth setup.
- **macOS Automation & Hardware Telemetry**: Voice-driven application management, system volume control, and real-time CPU, RAM, Disk, and Power monitoring.

---

## ✨ Full Feature Breakdown

### 🧠 1. Adaptive Self-Learning AI Brain & Memory Core (`learning_engine.py`)
- **Function Calling Brain v2** (`brain_v2.py` + `function_engine.py`): 18 registered tools (time, weather, Spotify, todos, reminders, apps, system control, web search, navigation, screenshots, guest permission, memory, technical analysis). The LLM picks the tool; no regex ordering.
- **Low-latency Dual-Engine LLM**: Groq Llama 3.3 70B primary + Google Gemini 2.5 failover.
- **Unified SQLite Brain Database (`friday_brain.db`)**:
  - `memories`: Permanent facts & user preferences.
  - `conversation_history`: Short-term context & RAG keyword-token semantic memory.
  - `user_action_habits`: Habit tracking with proactive suggestions when confidence ≥ 0.70.
  - `user_corrections`: Voice correction detection with -40.0 soft penalty weights.
  - 10 Career OS tables — see §6 below.
- **Dynamic Brevity Controller**: Auto-adjusts response length based on query complexity.
- **Owner Authentication & Security**: loopback/`FRIDAY_API_TOKEN` gating (see Security Policy) + guest permission gating.

### 🎵 2. Zero-Config Spotify Automation & Smart Audio Ducking
- **Zero-OAuth Token Engine**: Anonymous token resolver for instant playback without credentials.
- **Automatic Audio Ducking**: Spotify dips to 20% when F.R.I.D.A.Y. speaks, restores after.
- **Voice Media Control**: "play Kesariya", "volume down", "next track", "pause", "mute".
- **Now Playing Telemetry**: Live track title, artist, artwork, position timer, click-to-seek.

### 📈 3. Quantum Trading Workstation
- **TradingView Widget Engine**: Full drawing toolbar + technical indicators + all chart styles.
- **Live 24/5 Global Data Feeds**: Forex, Gold, Bitcoin, Nasdaq, DXY default pairs.
- **Multi-Chart Layouts**: 1x1 / 2x1 / 2x2 grid views.
- **Custom Resizable Watchlist**: Drag-and-drop, SQLite-persisted, 5000+ instruments.
- **Risk & Lot Size Calculator**: Position size calc for account balance, risk %, stop loss pips.
- **SQLite Auto-Save**: Silent background sync every 5 seconds to `friday_trading_db.sqlite`.

### 💻 4. macOS System Automation & Telemetry (`mac_controls.py`)
- **Zero-Latency Display Brightness**: macOS `DisplayServices` + keycode hardware simulation.
- **System Dark Mode Toggle**: Instant AppleScript switching between Dark / Light Mode.
- **Master Audio & Mute Controls**: Voice and slider control for system output and mute.
- **Lock Display**: Instant screen locking via voice or UI HUD.
- **Voice Application Control**: Open/quit macOS apps via sanitized AppleScript wrappers.
- **System Telemetry**: Real-time CPU %, RAM, SSD, and Battery monitoring via `psutil`.

### 📋 5. HUD Dashboard & Widgets
- **Spotify Card**: Floating player with album art, seek bar, and playback controls.
- **Todo Card**: Task manager with priority tags, status filters, inline editing, voice creation.
- **Weather Card**: Live weather via Open-Meteo API with auto IP geolocation.
- **System Monitor Card**: Real-time hardware telemetry charts.
- **Web Search Card**: Inline web search widget.
- **Ambient Lock Screen**: Glassmorphism UI with GLSL shader orb animation.
- **Career OS Button**: One-click access to Career Intelligence Center from the Dashboard HUD.

### 💼 6. Career Intelligence Center (Career OS) — ✅ LIVE & FULLY OPERATIONAL

> *"Never build a CRUD dashboard. Build an AI employee that manages my career."*

F.R.I.D.A.Y.'s Career OS is a fully operational AI career operating system with 12 modules:

| Module | Description |
|---|---|
| **Dashboard** | Daily AI briefing, pipeline stats, recommendations, activity feed |
| **Opportunities** | Job board with source/status/score filters, AI match analysis |
| **Applications** | Kanban board + table — drag-and-drop pipeline (`saved → offer`) |
| **Resume Manager** | Multi-version editor with ATS scoring, section editing, duplication |
| **Interview Center** | Schedule, track, generate AI prep questions, log outcomes |
| **Analytics** | SVG charts — monthly apps, pipeline funnel, resume performance |
| **Learning Center** | Skill gap analysis + AI-generated learning roadmap |
| **Preferences** | Tag-based prefs + natural language learning ("Tell F.R.I.D.A.Y.") |
| **Personal Vault** | Encrypted local storage for personal info & application auto-fill |
| **Companies** | Company tracker with blacklist/block functionality |
| **Recruiters** | Recruiter CRM with contact history, notes, last contact tracking |
| **Account Manager** | Secure credential vault for LinkedIn, Naukri, Wellfound, Indeed |

**Core AI capabilities (Groq Llama 3.3 70B)**:
- Job match scoring with detailed reasoning & salary/growth assessment
- Cover letter generation tailored per job + resume
- Interview question generation per role
- Natural language preference learning
- Skill gap analysis & learning roadmap generation
- Daily career briefing & proactive recommendations

**Backend**: `career_db.py` (10 SQLite tables in `friday_brain.db`) + `career_intelligence.py` (AI engine) + `routers/career.py` (42 endpoints across 31 paths at `/api/career/*`).

**Voice**: Say `"career"` → F.R.I.D.A.Y. navigates to Career OS.

---

### 📈 7. Real Technical Analysis Engine (`technical_analysis.py`)

No more hardcoded "RSI is at 64" — every value is computed from live OHLCV data:

| Indicator | Period | | Indicator | Period |
|---|---|---|---|---|
| SMA | 200 | | ATR | 14 |
| EMA | 9 / 20 / 50 | | Stochastic | %K(14) / %D(3) |
| RSI (Wilder) | 14 | | VWAP | volume-weighted |
| MACD | 12/26/9 + histogram | | Bollinger Bands | 20, 2σ |

Plus candlestick patterns (Doji, Hammer, Shooting Star, Bullish/Bearish Engulfing), trend bias with confidence, golden/death cross detection, support & resistance from swing points, and 5-candle momentum.

**Endpoint:** `GET /api/trading/analysis?symbol=FX:EURUSD&interval=15` returns structured indicators + a natural-language spoken summary. Also registered as the `technical_analysis` function tool, so you can just say *"what's the trend on gold?"*

### 📱 8. Telegram Bot Interface (`telegram_bot.py`)

FRIDAY is no longer Mac-only — reach it from your phone anywhere:

| Command | Action |
|---|---|
| `/time` `/weather` `/tasks` | Time, live weather, pending tasks |
| `/market` | Quick overview (EURUSD, Gold, NASDAQ, BTC, DXY) |
| `/spotify` | What's currently playing |
| `/analyze <SYMBOL>` | Real technical analysis |
| *any text* | Free-form chat through the same brain_v2 engine |

**Security:** `TELEGRAM_OWNER_ID` — only your Telegram user id may interact; everyone else gets "⛔ Access denied".

**Setup:** create a bot via @BotFather → set `TELEGRAM_BOT_TOKEN` + `TELEGRAM_OWNER_ID` in `backend/.env` → run `python -m services.telegram_bot` from `backend/`.

---

### 🛡️ 9. Permission Center & Approval-First Design

Every sensitive capability has a mode — `Enabled` / `Ask` / `Disabled` — persisted in SQLite and enforced server-side:

| Capability | Default | | Capability | Default |
|---|---|---|---|---|
| system.control | enabled | | email.send | ask |
| music.control | enabled | | whatsapp.send | ask |
| tasks.write | enabled | | phone.call | ask |
| web.search | enabled | | jobs.apply | ask |
| screen.capture | ask | | trades.execute | ask |
| vault.access | enabled | | files.delete | disabled |

- `Ask` = one-time approval (default 5 min) via `POST /api/permissions/approve` — nothing sensitive runs without your explicit grant.
- Every enforcement decision is audit-logged (`GET /api/permissions` returns the log; HUD Permission Center shows it).
- Trade execution **never happens automatically**: `POST /api/trading/order` (paper/simulated) returns 403 `approval_required` until you approve — matching the roadmap constraint.

### 🤖 10. Automation Engine & Smart Daily Briefing

Persisted workflows run on a background scheduler (lifespan-managed):

```
POST /api/automations   {"name": "Morning Briefing", "trigger_type": "daily",
                         "daily_time": "09:00", "action": "briefing"}
```

Actions: `briefing` (smart daily briefing), `job_scan` (notify on high-match /
high-salary jobs), `market_summary`. Results land in the **Notification Center**
(`GET /api/notifications`) instead of interrupting — the HUD Inbox panel shows
them, and `GET /api/briefing` gives the full morning report (weather, tasks,
reminders, career pipeline, markets, inbox).

### 🧠 11. Multi-Agent Framework

FRIDAY routes requests to specialized agents — Career, Coding, Research,
Finance, Communication, Automation — each running the same function-calling
brain but with a **filtered tool set** (an agent can only call its capabilities).
`POST /api/agent/chat` handles routing + execution; `GET /api/agents` lists them.
Agent autonomy is gated by the `agent.autonomy` permission (default `ask`).

```
"what's the trend on gold?"      → Finance Agent (technical_analysis tool)
"debug this React error"         → Coding Agent
"apply for Java jobs in Mumbai"  → Career Agent
```

---

### 🎓 12. Learning Coach (`services/learning.py`)

Track practice across tracks (DSA, Java, System Design, AWS, Interview Prep):
- **Streaks** — current + best consecutive-day streaks; daily/weekly minutes; problems solved.
- **Weekly goals** — per-track targets with progress bars (defaults seeded).
- **Gentle reminders** — a `learning_check` automation action notifies when you haven't practiced in ≥ 3 days ("Boss, you haven't solved a DSA problem in 3 days").
- Voice: *"Friday, I solved two DSA problems today"* → `log_learning` function tool.

### 🧠 13. Life Memory — Knowledge-Graph-Lite (`services/life_memory.py`)

Memories are stored as **subject → relation → target** triples instead of isolated facts:

```
Boss  --loves-->             cold brew
Boss  --won't apply below--> 7 LPA
Mom   --birthday-->          15 September
```

- Token + prefix search (`GET /api/life-memory/search?q=...`) answers connected questions: *"what do I love?"* → cold brew.
- `remember_fact` now writes both the facts table and a life-memory triple; the `search_memories` function tool lets FRIDAY recall things mid-conversation.

### 🛠️ 14. Developer Mode (`routes/devtools.py` + HUD panel)

Owner-only HUD panel with five tabs:
- **Overview** — live counts (facts, life memories, automations, notifications, todos, applications) + uptime.
- **Memory** — facts, life-memory triples, recent conversations.
- **Logs** — tail of backend logs (file + ring-buffer fallback).
- **API Tester** — run any request in-process against the app and see the JSON.
- **Config** — which env keys are set (booleans only — values never exposed) + permission modes.

---

### 🧠 15. Second Brain — Knowledge OS (`services/knowledge.py`)

Automatically stores meeting notes, ideas, research, code snippets, interview
experiences, project decisions, book notes and YouTube summaries — everything
searchable:

- **Idea capture** — "Friday, remember this idea…" auto-categorizes the note type from the text.
- **Search** — token + prefix search over title/content/tags/project; *"where did I save that Kafka architecture idea?"* → answered.
- **Project Intelligence** — every project gets its own memory (architecture, tasks, bugs, roadmap, ideas, completed, docs, GitHub, dependencies).

### 🕰️ 16. AI Memory Timeline (`services/timeline.py`)

A chronological timeline of meaningful events instead of isolated memories:

```
2026  ✓ Finished AI Attendance System    ✓ Got internship    ✓ AWS Certified
```

- "Friday, what changed last month?" → `GET /api/timeline/summary?query=last month`.
- "Show me my progress this year." → year-period grouping by category.
- `snapshot_from_existing()` auto-derives events from applications + learning sessions, so it's useful immediately.

### 🎯 17. Goal Manager (`services/goals.py`)

Set goals like *"Get 8 LPA job"* → tasks, progress %, deadlines, skill gaps
(optionally auto-suggested from job-match data), and resources. Track by voice:
*"Friday, I made 25% progress on my job goal"* → `update_goal` function tool.

### 💡 18. Explainable AI

Every Career OS recommendation now carries a `reasons` array — "why I
suggested this": matched skills %, salary meets target, previously preferred
roles, missing skills. Transparent instead of mysterious.

---

## 🛠️ Technology Stack

| Domain | Technologies |
|---|---|
| **Frontend UI** | React 19, Vite 8, Tailwind CSS, Framer Motion, Inter (Google Fonts), TradingView Lightweight Charts, Web Speech API, WebGL GLSL Shaders |
| **Backend API** | Python 3.11+, FastAPI, Uvicorn, SQLite (WAL mode, thread-safe), yfinance, numpy, psutil, asyncio |
| **AI Models** | Groq (Llama 3.3 70B Versatile — function calling), Google Gemini 2.5 |
| **Audio / Speech** | Web Speech API (STT), Microsoft Edge-TTS `en-IN-NeerjaNeural` / `hi-IN-SwaraNeural` (Neural TTS) |
| **Integrations** | Spotify Web Player API, Open-Meteo, Google Drive API, AppleScript (`osascript`), Telegram Bot API (`python-telegram-bot`) |
| **Career OS** | Groq Llama 3.3 70B (scoring, letters, skill gap), SQLite WAL (10 career tables) |

---

## 📁 Directory Structure

```
FRIDAY/
├── README.md                          # Main documentation (this file)
├── architecture.md                    # Technical architecture & system design
├── next_phase_architecture.md         # Phase 1 AI learning engine specification
├── start.sh                           # One-command launcher (backend + frontend)
├── stop.sh                            # Graceful shutdown script
│
├── backend/                           # Python FastAPI Backend (:8000)
│   ├── app.py                         # Thin wiring: app assembly + lifespan (~150 lines)
│   ├── requirements.txt               # Python dependencies
│   ├── data/                          # Persistent databases & JSON
│   │   ├── friday_brain.db            # Unified SQLite DB (AI memory + Career OS tables)
│   │   ├── friday_trading_db.sqlite   # Trading watchlist & chart state
│   │   └── .vault_key                 # Auto-generated Fernet key for the career vault
│   ├── routes/                        # v3 modular route split
│   │   ├── chat.py                    # /api/chat/text, memory, permission, proactive
│   │   ├── system.py                  # /api/system/*, open/close-app
│   │   ├── spotify.py                 # /api/spotify/* (current-track, seek, duck)
│   │   ├── todos.py                   # /api/todos CRUD
│   │   ├── utilities.py               # /api/tts, weather, search, reminders, gdrive
│   │   ├── watchlist.py               # /api/watchlist CRUD + default seed
│   │   └── trading.py                 # /api/trading/* (ohlcv, analysis, search…)
│   ├── routers/
│   │   └── career.py                  # Career OS REST endpoints (/api/career/*)
│   └── services/
│       ├── brain.py                   # Legacy Groq/Gemini regex brain (fallback)
│       ├── brain_v2.py                # v3 Function-Calling AI Brain (tools + failover)
│       ├── function_engine.py         # 18-tool function registry + dispatcher
│       ├── technical_analysis.py      # Real TA engine (RSI, MACD, BB, ATR, patterns)
│       ├── telegram_bot.py            # Telegram interface for phone access
│       ├── learning_engine.py         # Adaptive self-learning, habit tracking, RAG memory
│       ├── career_db.py               # Career OS DB layer (10 SQLite tables, encrypted vault)
│       ├── career_intelligence.py     # Career OS AI engine (Groq: scoring/letters/gaps)
│       ├── system_control.py          # macOS AppleScript & Spotify automation
│       ├── mac_controls.py            # Brightness, Dark Mode, volume hardware control
│       ├── market_data.py             # Live prices + background pollers (lifespan-managed)
│       ├── indian_market_data.py      # NSE/BSE market data adapter (lifespan-managed)
│       ├── chart_data.py              # Shared OHLCV fetch + symbol search
│       ├── todos.py / reminders.py    # Task & reminder services
│       ├── system_stats.py            # psutil system telemetry
│       ├── weather.py / web_search.py # Open-Meteo / DuckDuckGo wrappers
│       ├── memory.py                  # Long-term memory store
│       ├── tts.py                     # Edge-TTS neural text-to-speech + audio cleanup
│       ├── auth.py                    # Owner auth (loopback / FRIDAY_API_TOKEN)
│       ├── ratelimit.py               # Per-IP sliding-window rate limiter
│       ├── gdrive_api.py / gdrive_sync.py  # Google Drive integration
│       └── voice_auth.py              # Guest permission gate
│
└── friday-ui/                         # React 19 Frontend (Vite 8, :5173)
    ├── index.html                     # Inter font, SEO meta
    ├── package.json
    └── src/
        ├── api/
        │   └── careerApi.js           # Career OS typed API client (cache + invalidate)
        ├── components/                # LockScreen, Panels (SpotifyCard, TodoCard, etc.)
        ├── hooks/
        │   ├── useOrbState.jsx        # Global workspace state + voice command routing
        │   ├── useSpeech.js           # Web Speech API STT hook
        │   └── useProactiveSuggestions.js
        ├── services/
        │   └── ttsService.js          # Edge-TTS audio queue & female voice enforcement
        └── UI/
            ├── Workspace.jsx          # Workspace router (dashboard / trading / career)
            ├── Dashboard/
            │   └── Dashboard.jsx      # HUD dashboard with Career OS launch button
            ├── TradingWorkstation/    # Quantum Trading Workstation
            ├── Settings/
            ├── Buttons/
            └── Career/                # Career Intelligence Center (Career OS)
                ├── CareerOS.jsx       # Shell: sidebar nav + lazy-loaded module routing
                ├── components/        # 10 shared Career UI components
                └── modules/           # 12 fully functional Career OS modules
                    ├── Dashboard.jsx
                    ├── Opportunities.jsx
                    ├── Applications.jsx
                    ├── ResumeManager.jsx
                    ├── InterviewCenter.jsx
                    ├── Analytics.jsx
                    ├── LearningCenter.jsx
                    ├── Preferences.jsx
                    ├── PersonalVault.jsx
                    ├── Companies.jsx
                    ├── Recruiters.jsx
                    └── AccountManager.jsx
```

---

## 🚀 Quick Start Guide

### Prerequisites
- Node.js (v18+)
- Python (v3.11+)
- macOS (for AppleScript automation & system telemetry)

### One-Command Launch (Recommended)
```bash
cd FRIDAY
bash start.sh
```

Open `http://localhost:5173` in your browser.

### Manual Launch

**Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000 --no-proxy-headers
```

> `--no-proxy-headers` is important: it stops uvicorn from trusting
> client-supplied `X-Forwarded-For`, which would otherwise let anyone spoof
> `127.0.0.1` and bypass owner authentication.

**Frontend:**
```bash
cd friday-ui
npm install
npm run dev
```

### Accessing Career OS
1. Unlock F.R.I.D.A.Y. → go to Dashboard → click **"Career OS"** button in the HUD header, or
2. Say **"career"** via voice command.

### Telegram Bot (phone access)
```bash
cd backend
# set TELEGRAM_BOT_TOKEN + TELEGRAM_OWNER_ID in backend/.env
python -m services.telegram_bot
```
Message your bot from your phone: `/time`, `/weather`, `/market`, `/analyze OANDA:XAUUSD`, or just chat.

### Running Tests
```bash
cd backend
python -m pytest tests/ -q
```

---

## 🔒 Security Policy
- **Owner Authentication**: Requests from localhost are treated as the owner. Requests from any other machine are rejected with HTTP 401 unless they present the `FRIDAY_API_TOKEN` (from `backend/.env`) as the `X-FRIDAY-Token` header. The API never trusts a client-supplied "I am the boss" flag.
- **Machine-control gating**: chat, app open/close, display controls, memory, permission changes, and write endpoints all require owner authentication; the entire `/api/career/*` router is owner-only.
- **Rate limiting**: LLM-backed endpoints (chat + career AI) are rate-limited per IP to protect API credits.
- **Encrypted at rest**: sensitive Career OS profile fields (passwords, tokens, API keys) are encrypted with Fernet (AES + HMAC) before being written to SQLite. The key lives in `FRIDAY_VAULT_KEY` or an auto-generated `backend/data/.vault_key` (chmod 600).
- **Honest status reporting**: platform account verification returns `needs_login` until a real session exists — no fabricated "connected" responses.
- **CORS Isolation**: API restricted to `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`, `http://127.0.0.1:3000`.
- **Input Sanitization**: AppleScript triggers use strict regex sanitization to prevent injection.
- **No Blind Submissions**: Career OS never submits an application without explicit user confirmation.
- **Defensive Data Handling**: All DB & dictionary operations use safe fallback getters (`dict.get()`).

---

*Author / Lead Architect:* **Prem (Prathvi Sahu)** & **F.R.I.D.A.Y.**
*Last Updated:* August 2026
