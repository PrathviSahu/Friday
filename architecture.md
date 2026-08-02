# F.R.I.D.A.Y. Technical Architecture

**Document Purpose**
This document describes the technical architecture of the **F.R.I.D.A.Y.** personal AI desktop operating system, detailing component hierarchy, data flows, LLM orchestration, security policies, real-time market data pipelines, and the **Career Intelligence Center (Career OS)** — fully operational as of August 2026.

---

## 1. Core Architecture & System Vision

FRIDAY is built for **Prem** (Prathvi Sahu) as a voice-first personal operating system:

1. **Dual-Engine LLM Core**:
   - **Fast-Path Engine**: Groq (`llama-3.3-70b-versatile`) delivering sub-150ms voice responses and direct system action execution.
   - **Reasoning & Failover Engine**: Google Gemini 2.5 for complex multi-turn logic, fallback scenarios, and document analysis.

2. **Strict Female Voice Engine & Audio Queue**:
   - **Primary TTS**: Microsoft Edge-TTS neural voice `en-GB-SoniaNeural` (British, calm, professional).
   - **Browser Fallback Gating**: `ttsService.js` filters browser voices to strictly select female voices (Samantha, Victoria, Karen, Moira, Fiona, Zira) while explicitly excluding male voices (Daniel, Alex, Fred, Oliver).
   - **Audio Queue System**: Non-blocking audio queue prevents overlapping voice responses.

3. **Quantum Trading Workstation**:
   - **TradingView Lightweight Charts Engine**: High-performance canvas-rendered candlestick charts with Volume histograms.
   - **OHLCV Data Pipeline (`/api/trading/ohlcv`)**: Yahoo Finance (`yfinance`) supporting 7 resolutions (`1m`, `5m`, `15m`, `30m`, `1h`, `1D`, `1W`).
   - **Multi-Asset Watchlist & SQLite Persistence**: 5000+ instruments across NSE/BSE, Forex, Crypto, US Equities. Stored in `friday_trading_db.sqlite`.
   - **Live Polling Loop**: Intraday charts update every 30 seconds.

4. **Career Intelligence Center (Career OS)** — ✅ **Fully Operational**:
   - **AI Engine** (`career_intelligence.py`): Groq Llama 3.3 70B for job match scoring, cover letter generation, interview questions, skill gap analysis, daily briefing, and preference learning.
   - **Database Layer** (`career_db.py`): 10 SQLite tables in `friday_brain.db` (WAL mode).
   - **REST API** (`routers/career.py`): 37 endpoints at `/api/career/*`.
   - **React Frontend**: 12 fully functional modules, lazy-loaded, no placeholder components.
   - **Voice Integration**: `"career"` command routes to Career OS via `useOrbState.jsx`.

5. **Zero-Config Spotify Automation**:
   - Web Player token resolver bypassing OAuth for playback control, track search, volume, and seek (`/api/spotify/seek`).

6. **macOS System Controller & Security Policy**:
   - AppleScript (`osascript`) app control, volume management, and process lifecycle.
   - Strict regex sanitization on all shell inputs.
   - Restricted local CORS policy (`localhost:5173`, `127.0.0.1:5173`).

---

## 2. System Component Diagram

```
+-----------------------------------------------------------------------+
|                    React 19 Frontend (friday-ui :5173)                |
|                                                                       |
|  [useSpeech STT] --> [useOrbState: workspace router]                  |
|        |                    |              |              |            |
|  [LockScreen]        [Dashboard]    [TradingWS]    [Career OS]        |
|                       + HUD cards    Lightweight    CareerOS.jsx       |
|                                      Charts         12 modules         |
+-----------------------------------------------------------------------+
                               | HTTP / JSON (REST)
                               v
+-----------------------------------------------------------------------+
|                 FastAPI Python Backend (:8000)                        |
|                                                                       |
|  [app.py: CORS + router registration]                                 |
|                                                                       |
|  Services Layer:                                                       |
|  ├── brain.py           (Groq/Gemini LLM dual-engine)                |
|  ├── learning_engine.py (habits, corrections, RAG memory)             |
|  ├── career_db.py       (10 career SQLite tables)                    |
|  ├── career_intelligence.py (AI: scoring/letters/gaps)                |
|  ├── market_data.py     (yfinance OHLCV)                             |
|  ├── system_control.py  (macOS AppleScript + Spotify)                |
|  └── tts.py             (Edge-TTS en-GB-SoniaNeural)                 |
|                                                                       |
|  Databases:                                                           |
|  ├── friday_brain.db        (AI memory + Career OS, WAL mode)        |
|  └── friday_trading_db.sqlite (Trading watchlist & chart state)      |
+-----------------------------------------------------------------------+
        |                    |                        |
        v                    v                        v
[Groq Llama 70B]   [Google Gemini 2.5]      [macOS / Spotify / Open-Meteo]
```

---

## 3. Technology Stack Specification

| Component | Technology | Role / Function |
|---|---|---|
| **Frontend Core** | React 19, Vite 8, Framer Motion | Dynamic HUD dashboard, panel routing, animations |
| **Charting Engine** | Lightweight Charts (TradingView) | Canvas rendering, OHLCV candles, Volume histogram |
| **Voice & Audio** | Web Speech API + Edge-TTS `en-GB-SoniaNeural` | STT input, Neural TTS output queue |
| **Backend Framework** | FastAPI + Uvicorn | Async ASGI REST backend (:8000) |
| **Market Data** | yfinance + TradingView Scanner API | Multi-exchange market quotes & candle history |
| **AI LLMs** | Groq Llama 3.3 70B + Gemini 2.5 | Intent extraction, career intelligence, natural dialogue |
| **Database Layer** | SQLite (WAL) + JSON | `friday_brain.db`, `friday_trading_db.sqlite`, todos, reminders |
| **System Automation** | Python `subprocess` + AppleScript | macOS application management, system volume |
| **Career AI** | Groq Llama 3.3 70B (JSON mode) | Job scoring, cover letters, skill gap, briefing |
| **Typography** | Inter (Google Fonts) | Career OS UI — professional, clean typography |

---

## 4. Database Schema — Career OS Tables (in `friday_brain.db`)

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

## 5. Active API Endpoint Reference

### Core Endpoints
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat/text` | Main voice/text AI brain entrypoint |
| `GET` | `/api/trading/ohlcv` | Historical & intraday candle data |
| `GET` | `/api/trading/live-prices` | Real-time watchlist prices |
| `GET/POST` | `/api/watchlist` | Retrieve/add watchlist items |
| `DELETE` | `/api/watchlist/{symbol}` | Delete watchlist item |
| `PUT` | `/api/watchlist/reorder` | Update watchlist sort order |
| `GET` | `/api/spotify/current-track` | Active Spotify playback telemetry |
| `POST` | `/api/spotify/seek` | Seek playback position in seconds |
| `GET/POST` | `/api/todos` | Fetch / create persistent todo tasks |
| `PATCH` | `/api/todos/{id}/toggle` | Toggle todo completion state |
| `DELETE` | `/api/todos/{id}` | Delete todo item |
| `GET` | `/api/system/stats` | Telemetry: CPU, RAM, Disk, Power |
| `GET` | `/api/weather` | Open-Meteo weather with IP geolocation |

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

## 6. Voice Command Routing

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

## 7. Security & Protection Guidelines

1. **CORS Isolation**: Restricts API calls to authorized local frontend origins (`http://localhost:5173`, `http://127.0.0.1:5173`).
2. **AppleScript & Shell Sanitization**: App names and user inputs filtered via strict regex (`re.sub(r'[^a-zA-Z0-9\s._\-]', '', app_name)`).
3. **Defensive Data Handling**: All database and dictionary operations use safe fallback getters (`dict.get()`).
4. **Adaptive Polling Backoff**: Background pollers scale back during network interruptions.
5. **Career Data Privacy**: All career data (credentials, profile, applications) stored exclusively in local `friday_brain.db` — never transmitted externally.
6. **No Blind Career Submissions**: Career OS enforces a mandatory human confirmation step before any application submission.

---

*Last Updated:* August 2026
*Lead Architect:* Prem (Prathvi Sahu) & F.R.I.D.A.Y.
