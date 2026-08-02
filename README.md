# ⚡ F.R.I.D.A.Y. — Voice-Controlled AI Operating System & Career Intelligence Center

> **F.R.I.D.A.Y.** is a full-stack, voice-controlled AI desktop operating system inspired by Iron Man's J.A.R.V.I.S., built using **React 19**, **Vite 8**, **Python FastAPI**, **Groq (Llama 3.3 70B)**, and **Google Gemini 2.5**.

---

## 📖 Overview

**F.R.I.D.A.Y.** is a comprehensive personal AI assistant designed to streamline career management, trading, daily productivity, media control, and macOS system automation.

Key architectural pillars:
- **Dual-Engine Hybrid AI Brain**: Sub-150ms voice interactions via Groq Llama 3.3 70B + complex reasoning & fallbacks via Google Gemini 2.5.
- **Strict Female Voice Engine**: Microsoft Edge-TTS neural voice (`en-GB-SoniaNeural`) with a browser fallback filter that strictly enforces female voice selection (e.g. Samantha, Victoria, Karen, Zira) while excluding male voices.
- **Career Intelligence Center (Career OS)**: A fully operational AI-powered career operating system — not a job portal. Analyzes opportunities, drafts cover letters, tracks interviews, manages resumes, and learns your preferences. Never submits without your final approval.
- **Quantum Trading Workstation**: TradingView Lightweight Charts with live OHLCV candle streaming across 7 timeframes (`1m` to `1W`) for 5000+ symbols (NSE/BSE Indian Equities, Forex, Crypto, US Stocks), 30-second live auto-polling, and a drag-and-drop watchlist backed by SQLite persistence.
- **Zero-Config Spotify Automation**: Control music playback, track search, volume, and progress seek bar via an anonymous web player token without manual OAuth setup.
- **macOS Automation & Hardware Telemetry**: Voice-driven application management, system volume control, and real-time CPU, RAM, Disk, and Power monitoring.

---

## ✨ Full Feature Breakdown

### 🧠 1. Adaptive Self-Learning AI Brain & Memory Core (`learning_engine.py`)
- **Sub-150ms Dual-Engine LLM**: Groq Llama 3.3 70B primary (~150ms) + Google Gemini 2.5 failover.
- **Unified SQLite Brain Database (`friday_brain.db`)**:
  - `memories`: Permanent facts & user preferences.
  - `conversation_history`: Short-term context & RAG keyword-token semantic memory.
  - `user_action_habits`: Habit tracking with proactive suggestions when confidence ≥ 0.70.
  - `user_corrections`: Voice correction detection with -40.0 soft penalty weights.
  - 10 Career OS tables — see §6 below.
- **Dynamic Brevity Controller**: Auto-adjusts response length based on query complexity.
- **Voice Fingerprint & Security**: Owner authorization ("Prem") with guest permission gating.

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

**Backend**: `career_db.py` (10 SQLite tables in `friday_brain.db`) + `career_intelligence.py` (AI engine) + `routers/career.py` (37 REST endpoints at `/api/career/*`).

**Voice**: Say `"career"` → F.R.I.D.A.Y. navigates to Career OS.

---

## 🛠️ Technology Stack

| Domain | Technologies |
|---|---|
| **Frontend UI** | React 19, Vite 8, Tailwind CSS, Framer Motion, Inter (Google Fonts), TradingView Lightweight Charts, Web Speech API, WebGL GLSL Shaders |
| **Backend API** | Python 3.14, FastAPI, Uvicorn, SQLite (WAL mode), yfinance, psutil, asyncio |
| **AI Models** | Groq (Llama 3.3 70B Versatile), Google Gemini 2.5 |
| **Audio / Speech** | Web Speech API (STT), Microsoft Edge-TTS `en-GB-SoniaNeural` (Neural TTS) |
| **Integrations** | Spotify Web Player API, Open-Meteo, Google Drive API, AppleScript (`osascript`) |
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
│   ├── app.py                         # Main FastAPI server + router registration
│   ├── requirements.txt               # Python dependencies
│   ├── data/                          # Persistent databases & JSON
│   │   ├── friday_brain.db            # Unified SQLite DB (AI memory + Career OS tables)
│   │   ├── friday_trading_db.sqlite   # Trading watchlist & chart state
│   │   ├── todos.json                 # Persistent task list
│   │   └── reminders.json            # Persistent reminders
│   ├── routers/
│   │   └── career.py                  # 37 Career OS REST endpoints (/api/career/*)
│   └── services/
│       ├── brain.py                   # Groq/Gemini LLM dual-engine + intent routing
│       ├── learning_engine.py         # Adaptive self-learning, habit tracking, RAG memory
│       ├── career_db.py               # Career OS DB layer (10 SQLite tables)
│       ├── career_intelligence.py     # Career OS AI engine (Groq: scoring/letters/gaps)
│       ├── system_control.py          # macOS AppleScript & Spotify automation
│       ├── mac_controls.py            # Brightness, Dark Mode, volume hardware control
│       ├── market_data.py             # Live prices & Yahoo Finance OHLCV generator
│       ├── indian_market_data.py      # NSE/BSE market data adapter
│       ├── todos.py                   # Task CRUD service
│       ├── reminders.py               # Reminders service
│       ├── system_stats.py            # psutil system telemetry
│       ├── weather.py                 # Open-Meteo API wrapper
│       ├── web_search.py              # Web search service
│       ├── memory.py                  # Long-term memory store
│       ├── tts.py                     # Edge-TTS en-GB-SoniaNeural text-to-speech
│       ├── stt.py                     # Speech-to-text service
│       ├── voice_auth.py              # Voice fingerprint & owner authentication
│       ├── formatter.py               # Response formatting utilities
│       ├── gdrive_api.py              # Google Drive API integration
│       └── gdrive_sync.py             # Google Drive sync service
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
uvicorn app:app --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd friday-ui
npm install
npm run dev
```

### Accessing Career OS
1. Unlock F.R.I.D.A.Y. → go to Dashboard → click **"Career OS"** button in the HUD header, or
2. Say **"career"** via voice command.

---

## 🔒 Security Policy
- **CORS Isolation**: API restricted to `http://localhost:5173`, `http://127.0.0.1:5173`.
- **Input Sanitization**: AppleScript triggers use strict regex sanitization to prevent injection.
- **Career Vault**: Credentials stored in local `friday_brain.db` — never sent externally.
- **No Blind Submissions**: Career OS never submits an application without explicit user confirmation.
- **Defensive Data Handling**: All DB & dictionary operations use safe fallback getters (`dict.get()`).

---

*Author / Lead Architect:* **Prem (Prathvi Sahu)** & **F.R.I.D.A.Y.**
*Last Updated:* August 2026
