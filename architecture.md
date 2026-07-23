# Friday Project Architecture Overview

**Document Purpose**  
This document describes the technical architecture of the **F.R.I.D.A.Y.** personal AI desktop operating system and trading station, detailing component hierarchy, data flows, LLM orchestration, security policies, real-time market data pipelines, and the **Autonomous AI Job Portal** integration roadmap.

---

## 1. Core Architecture & System Vision

FRIDAY is built for **Prem** (Prathvi Sahu) as a voice-first personal operating system:

1. **Dual-Engine LLM Core**:
   - **Fast-Path Engine**: Groq (`llama-3.3-70b-versatile`) delivering sub-150ms voice responses and direct system action execution.
   - **Reasoning & Failover Engine**: Google Gemini 2.5 for complex multi-turn logic, fallback scenarios, and document analysis.

2. **Strict Female Voice Engine & Audio Queue**:
   - **Primary TTS**: Microsoft Edge-TTS neural voices (`en-IN-NeerjaNeural` / `hi-IN-SwaraNeural`).
   - **Browser Fallback Gating**: `ttsService.js` filters browser voices to strictly select female voices (Samantha, Victoria, Karen, Moira, Fiona, Zira) while explicitly excluding male voices (Daniel, Alex, Fred, Oliver).
   - **Audio Queue System**: Non-blocking audio queue prevents overlapping voice responses.

3. **Quantum Trading Workstation**:
   - **TradingView Lightweight Charts Engine**: High-performance canvas-rendered candlestick charts with Volume histograms.
   - **OHLCV Data Pipeline (`/api/trading/ohlcv`)**: Fetches historical and real-time candle data via Yahoo Finance (`yfinance`) supporting 7 resolutions (`1m`, `5m`, `15m`, `30m`, `1h`, `1D`, `1W`).
   - **Multi-Asset Watchlist & SQLite DB Persistence**: Supports 5000+ instruments across Indian Equities (NSE/BSE), Forex, Crypto, Indices, and US Equities. Reordering, additions, and deletions persist in SQLite (`friday_trading_db.sqlite`) and `localStorage`.
   - **Live Polling Loop**: Intraday charts update every 30 seconds with pulse animation and manual refresh trigger.

4. **Autonomous AI Job Portal Agent *(Architecture Roadmap)***:
   - **Scraper & Aggregator Module**: Periodic background agent fetching job postings matching Prem's profile across LinkedIn, Naukri, and Internshala.
   - **Match Scoring Engine**: LLM ranks jobs by skill relevance, salary, location, and company quality.
   - **Human-in-the-Loop Review Queue**: Surfaced in FRIDAY UI / Voice for Prem's explicit "Approve" or "Reject" decision.
   - **Auto-Application Agent**: Automated browser worker populating resume details and submitting applications upon voice authorization.

5. **Zero-Config Spotify Automation**:
   - Web Player token resolver bypassing OAuth requirement for playback control, track search, volume adjustment, and seek (`/api/spotify/seek`).

6. **macOS System Controller & Security Policy**:
   - AppleScript (`osascript`) app control, volume management, and process lifecycle with strict regex character sanitization to prevent command injection.
   - Restricted local CORS policy (`localhost:5173`, `127.0.0.1:5173`).

---

## 2. System Component Diagram

```
+-----------------------------------------------------------------------+
|                         React 18 Frontend                             |
|                        (friday-ui :5173)                              |
|                                                                       |
|  [useSpeech STT] -----> [Orb & Workspace Manager] -----> [Dashboard] |
|                                                                 |     |
|  [TradingWorkstation] <---> [Lightweight Charts] <--> [Watchlist]      |
+-----------------------------------------------------------------------+
                                   |  HTTP / JSON (REST)
                                   v
+-----------------------------------------------------------------------+
|                      FastAPI Python Backend                           |
|                         (backend :8000)                               |
|                                                                       |
|  [App Entry / CORS] ----> [Services Layer] ----> [Databases]          |
|   - Restricted Origins     - brain.py (LLM)       - SQLite Watchlist  |
|   - Input Sanitization     - market_data.py       - SQLite Memory     |
|                            - system_control.py    - JSON Todos        |
|                            - gdrive_sync.py       - JSON Reminders    |
+-----------------------------------------------------------------------+
          |                        |                        |
          v                        v                        v
  [Groq Llama 70B]         [Google Gemini 2.5]       [macOS System / Spotify]
```

---

## 3. Technology Stack Specification

| Component | Technology | Role / Function |
|---|---|---|
| **Frontend Core** | React 18, Vite, Framer Motion | Dynamic HUD dashboard, panel routing, animations |
| **Charting Engine** | Lightweight Charts (TradingView) | Canvas rendering, OHLCV candles, Volume histogram |
| **Voice & Audio** | Web Speech API + Edge TTS | STT input, Neural TTS output queue |
| **Backend Framework**| FastAPI + Uvicorn | Async ASGI REST backend (:8000) |
| **Market Data** | yfinance + TradingView Scanner API | Multi-exchange market quotes & candle history |
| **AI LLMs** | Groq Llama 3.3 70B + Gemini 2.5 | Intent extraction, system control, natural dialogue |
| **Database Layer** | SQLite + JSON | Watchlist, Memory, Todos, Reminders persistence |
| **System Automation**| Python `subprocess` + AppleScript | macOS application management, system volume |

---

## 4. Active API Endpoint Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat/text` | Main voice/text AI brain entrypoint |
| `GET` | `/api/trading/ohlcv` | Historical & intraday candle data for Lightweight Charts |
| `GET` | `/api/trading/live-prices` | Real-time watchlist prices |
| `GET` | `/api/watchlist` | Retrieve stored watchlist from SQLite DB |
| `POST` | `/api/watchlist` | Add item to SQLite watchlist |
| `DELETE` | `/api/watchlist/{symbol}` | Delete item from SQLite watchlist |
| `PUT` | `/api/watchlist/reorder` | Update watchlist sorting order |
| `GET` | `/api/spotify/current-track` | Active Spotify playback telemetry |
| `POST` | `/api/spotify/seek` | Seek playback position in seconds |
| `GET` / `POST` | `/api/todos` | Fetch / create persistent todo tasks |
| `PATCH` | `/api/todos/{id}/toggle` | Toggle todo completion state |
| `DELETE` | `/api/todos/{id}` | Delete todo item |
| `GET` | `/api/system/stats` | Telemetry for CPU, RAM, Disk, Power |
| `GET` | `/api/weather` | Open-Meteo weather with IP geolocation |

---

## 5. Security & Protection Guidelines

1. **CORS Isolation**: Restricts API calls to authorized local frontend origins (`http://localhost:5173`, `http://127.0.0.1:5173`).
2. **AppleScript & Shell Sanitization**: App names and user inputs are filtered via strict regex (`re.sub(r'[^a-zA-Z0-9\s._\-]', '', app_name)`) prior to subprocess execution.
3. **Defensive Data Handling**: All database and dictionary operations use safe fallback getters (`dict.get()`) to prevent unexpected runtime crashes.
4. **Adaptive Polling Backoff**: Background pollers scale back polling frequency during network interruptions to eliminate resource thrashing.

---
*Last Updated:* July 2026  
*Lead Architect:* Prem (Prathvi Sahu) & F.R.I.D.A.Y.