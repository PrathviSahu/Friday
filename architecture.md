# Friday Project Architecture Overview

**Document purpose**  
This file describes the high-level architecture of the *Friday* desktop assistant project, covering its major components, data flows, technology choices, persistent services, draggable HUD widgets, active Spotify/System automation integrations, and the **F.R.I.D.A.Y. Personal Trading Station**.

---

## 1. Project Vision
Friday is a personal AI assistant built for **Prem** (Prathvi Sahu) that:
- **Global Wake-Word Gate & Voice Interruption**:
  - Listens continuously for voice wake-words (`"Friday"`, `"Hey Friday"`, `"Suno Friday"`) and enforces a strict gate ignoring ambient noise so queries are only sent to Groq when explicitly addressed.
  - **Instant Speech Interruption**: Saying `"Friday ..."` while FRIDAY is speaking immediately cancels current speech playback (`stopSpeaking()`) so she listens to the new command.
- **F.R.I.D.A.Y. Personal Trading Station**:
  - Full-viewport real-time TradingView charting engine (`tv.js`) with custom Cyber-Grid overlay and pane gridlines.
  - Dedicated **Custom Watchlist Panel** on the right featuring **Forex & Crypto** and **Indian Market 🇮🇳** tabs.
  - Full **`+ Add Symbol`** modal and hover **`🗑️ Delete`** icon with persistent `localStorage` saving.
  - Complete **Native Timeframe Toolbar** (`1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `D`, `W`), technical indicators, chart types, and drawing tools.
  - **Right-Click Context Menu**: Triggers Chart & Fib Customizer for candle body/wick colors and Fibonacci retracements.
  - **Trading Sleep Mode**: While in Trading Mode, background speech is ignored, and HUD widgets (CPU Monitor, AI Search, Weather Card) are hidden to maintain a distraction-free trading view.
- **Executes macOS Automation**:
  - App control (open/close Spotify, browsers, terminal), volume control, background Spotify track/playlist control, weather queries, and voice-to-todo.
- **Floating Draggable Widget Ecosystem (Minimized by Default)**:
  - 🎵 **Spotify Card**: Dark-glass UI, real album art, real-time playback position & duration, click-to-seek progress bar (`/api/spotify/seek`), volume slider, song search line, and background macOS `osascript` control.
  - 📋 **Todo Card**: Persistent task manager with priority tags (High/Normal/Low), status filter tabs, inline editing, progress tracking, and voice-to-todo.
  - ⚡ **System Monitor HUD**: Real-time macOS CPU %, RAM GB/%, SSD Disk %, and Battery/Power status telemetry via `psutil`.
  - 🌤️ **Weather Card**: Live real-time weather data via Open-Meteo API with IP auto-location and global city voice search.
- Dual-engine hybrid AI (Groq Llama 3.3 70B primary for ~150ms responses + Gemini 2.5 failover).

---

## 2. High-Level Diagram  

```
+---------------------+          HTTP / JSON          +-------------------------+
|  React 18 Frontend  | <---------------------------> |  FastAPI Python Backend |
|  (friday-ui)        |  POST /api/chat/text          |  (backend/app.py :8000) |
|  - useSpeech Hook   |  GET  /api/spotify/current-tr |                         |
|  - TradingStation   |  POST /api/spotify/seek       +-------------------------+
|  - Draggable Pills  |  GET/POST/DELETE /api/todos          /     |     \
|    * SpotifyCard    |  GET  /api/system/stats              /      |      \
|    * TodoCard       |  GET  /api/weather                  v       v       v
|    * SystemHUD      |  GET  /api/proactive               [ Fast-Path ] [ Services ] [ Dual-Engine LLM ]
|    * WeatherCard    |                               Shortcuts     - todos.py   - Groq 70B (150ms)
+---------------------+                               - Trading     - stats.py   - Gemini 2.5
                                                      - Spotify     - weather.py
                                                           |
                                                           v
                                                   [ system_control.py ]
                                                     (macOS AppleScript)
                                                     /                 \
                                           [ Spotify App ]        [ macOS System ]
                                           - Position / Duration  - Output Volume
                                           - Background Control   - App Management (Close)
                                           - Album Artwork URL    - Telemetry (psutil)
```

---

## 3. Technology Stack  

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **UI Framework** | React 18 + Vite + Tailwind CSS + Framer Motion | Fast dev experience, modular UI, draggable HUD widgets, and full-viewport Personal Trading Station. |
| **Trading Engine** | TradingView Widget (`tv.js`) | Native real-time market streams, drawing tools, timeframes (`1m` to `W`), and customizable theme properties. |
| **Voice STT & Gate** | Web Speech API + Wake-Word Gate | Continuous listening with mandatory wake-word gate (`"Friday"`) and instant speech interruption (`stopSpeaking()`). |
| **Backend API** | Python 3.11 + FastAPI + Uvicorn | Asynchronous high-performance API server running at `http://localhost:8000`. |
| **Primary LLM** | Groq (`llama-3.3-70b-versatile`) | Ultra-fast (~150ms) intent extraction, conversational replies, and voice shortcuts. |
| **Failover LLM** | Google Gemini 2.5 | Heavy reasoning and fallback handling if primary LLM fails. |
| **TTS Engine** | Edge-TTS (Microsoft Neural Voices) | Natural British female voice output with Web Speech API browser fallback. |
| **OS Automation** | Python `subprocess` + macOS AppleScript (`osascript`) | Native macOS control over Spotify, apps, browser URLs, volume, and playback seek. |

---

## 4. Directory Structure  

```
/FRIDAY
├── friday-ui/                         # React Frontend (Vite)
│   ├── src/
│   │   ├── api/                      # fetchChatText.ts API client
│   │   ├── components/               # LockScreen, Panels (SpotifyCard, TodoCard, SystemMonitorCard, WeatherCard)
│   │   ├── context/                  # FridayContext, FridaySync
│   │   ├── hooks/                    # useSpeech.js, useProactiveSuggestions.js, useOrbState.jsx, voiceCommands.js
│   │   ├── UI/
│   │   │   └── TradingWorkstation/   # F.R.I.D.A.Y. Personal Trading Station
│   │   │       ├── QuantumTradingWorkstation.jsx
│   │   │       └── components/       # ProfessionalChart.jsx, Watchlist.jsx (Forex & Indian Market 🇮🇳)
│   │   └── services/                 # ttsService.js
│   └── package.json
│
├── backend/                           # Python FastAPI Backend
│   ├── app.py                        # Main FastAPI server (:8000)
│   ├── data/                         # Persistent JSON storage (todos.json, memory.json)
│   ├── services/
│   │   ├── brain.py                  # Groq/Gemini LLM engine + Fast-path shortcuts + Proactive engine + Voice-to-todo
│   │   ├── system_control.py         # macOS AppleScript system & Spotify automation + Seek + Position/Duration
│   │   ├── todos.py                  # Persistent Todo CRUD service
│   │   ├── system_stats.py           # psutil telemetry service (CPU, RAM, Disk, Battery)
│   │   ├── weather.py                # Open-Meteo weather service + IP geolocation
│   │   ├── memory.py                 # Permanent memory & preference storage
│   │   └── voice_auth.py             # Boss / Guest permission gating
│   └── requirements.txt
│
└── architecture.md                    # <--- Updated Architecture Specification
```

---

## 5. Active API Endpoints  

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/text` | Main voice/text AI brain endpoint (supports `silence_tts`, voice-to-todo & weather intent) |
| GET | `/api/spotify/current-track` | Active track details (title, artist, album, state, artwork_url, position, duration) |
| POST | `/api/spotify/seek` | Seek to specific playback timestamp in seconds |
| GET | `/api/weather` | Live weather data (temp, condition, humidity, wind, city) |
| GET | `/api/todos` | Fetch all stored todo items |
| POST | `/api/todos` | Create a new todo item |
| PATCH | `/api/todos/{id}/toggle` | Toggle todo completion state |
| PATCH | `/api/todos/{id}/text` | Edit todo text |
| DELETE | `/api/todos/{id}` | Delete a single todo |
| DELETE | `/api/todos/done` | Clear all completed todos |
| GET | `/api/system/stats` | Fetch real-time CPU %, RAM %, Disk %, and Battery stats |
| GET | `/api/proactive` | Returns time-aware proactive announcement |
| POST | `/api/tts` | Edge-TTS neural speech audio generator |

---

## 6. Security & Identity

- **Owner / Boss**: **Prem** (addressed as Prem across all replies and UI status).
- **Boss Gating**: System commands (app launch, volume, media control, todo creation, weather, playlist additions) are restricted to Prem.
- **Phonetic Speech Correction & Trailing Wake Words**:
  - `useSpeech.js` automatically strips trailing wake-words and cleans phonetic misrecognitions.
  - Flexible voice shortcuts in `voiceCommands.js` match single keywords (e.g., `"trading"`, `"chart"`, `"vscode"`, `"dashboard"`).
- **TradingView Embed Stability**:
  - `ProfessionalChart.jsx` includes `'widget_bar'` in `disabled_features` to resolve `TypeError: Cannot read properties of undefined (reading 'list')`.
- **Guest Access**: Guests can speak only when Prem explicitly says `"allow guest"`. Refused via `"revoke guest"`.

---
*Updated:* July 2026  
*Lead Architect:* Prem (Prathvi Sahu) & F.R.I.D.A.Y.