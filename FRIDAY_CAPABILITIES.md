# ⚡ F.R.I.D.A.Y. — Complete Capability Reference

**Version:** v3.3.0 · **API surface:** 128 endpoints · **Function tools:** 24 · **HUD panels:** 13
**Stack:** React 19 + Vite frontend · FastAPI backend · SQLite (WAL) · Groq/Gemini LLM · Edge-TTS · Vitest (frontend tests)

> This document is the definitive, machine-accurate list of everything F.R.I.D.A.Y.
> can do. Every capability below is implemented and tested — none are placeholders.
> Version numbers and counts reflect the code at commit `f1d37ee`.

---

## 1. The Big Picture

F.R.I.D.A.Y. is a **voice-controlled Personal Operating System** built from seven
layers. Anything you can do in the UI you can also do by voice, and everything
remembers you over time.

| Layer | What it does | Where |
|---|---|---|
| **AI Core** | Conversation, intent routing, tool calling, memory | `brain.py`, `brain_v2.py`, `function_engine.py` |
| **Voice** | Wake word, STT (browser + Groq Whisper free tier fallback), neural TTS, audio queue | `useSpeech.js`, `services/stt.py`, `tts.py` |
| **Career OS** | Resumes, jobs, applications, interviews, recruiters | `routers/career.py` (42 endpoints) |
| **Developer OS** | Trading workstation, technical analysis, devtools | `routes/trading.py`, `routes/devtools.py` |
| **Knowledge OS** | Second brain, memory timeline, life memory, goals | `routes/knowledge.py`, `services/*` |
| **Personal OS** | Tasks, reminders, weather, briefing, automations, notifications | `routes/*` |
| **Security** | Owner auth, permission center, encryption, audit log | `auth.py`, `permissions.py` |

---

## 2. Voice & Speech

| Capability | Detail |
|---|---|
| Wake word | "Hey Friday", "OK Friday", "Friday…" (stripped before processing) |
| Barge-in | Start talking while F.R.I.D.A.Y. is speaking → she stops instantly and listens. Browser engine: transcript-based (her echo is blocked, your command wins). Whisper engine: TTS volume ducks + fresh voice-onset detection |
| Push-to-talk | Optional hold-**Space** mode — mic opens only while held (barge-in stops speech instantly); toggle in the bottom bar, remembered across reloads |
| Speech-to-text | Browser Web Speech API (instant path); auto-fallback to **Groq Whisper `whisper-large-v3-turbo`** (free tier) → Gemini `gemini-2.5-flash` audio when the browser engine is unsupported or flaky. Whisper is Hinglish-aware, so Hindi commands transcribe correctly |
| Text-to-speech | Microsoft Edge-TTS — `en-IN-NeerjaNeural` (English), `hi-IN-SwaraNeural` (Hindi); auto-detects Devanagari |
| Audio queue | Non-blocking queue; `stopSpeaking()` interrupts instantly |
| Spotify ducking | Music dips to 20% while F.R.I.D.A.Y. speaks, restores after |
| Speech corrections | "No, I meant X" → permanently stored in personal vocabulary |
| Email Agent | Gmail/Outlook via IMAP+SMTP (app password): unread inbox, search, priority detection, summary, drafts — **approval-first send**: nothing is sent until you confirm (voice "yes"/"no" or the on-screen preview) |
| Calendar Agent | Google Calendar: today/upcoming/search, **approval-first create** (preview → confirm → insert), Calendar section in the Daily Briefing; OAuth via `credentials.json` (own `calendar_token.json`) |
| Meeting Assistant | Upload a recording (Groq Whisper, free tier) or paste a transcript → LLM extracts summary, key points, decisions & **action items** → saved to SQLite + mirrored to Knowledge OS; action items can be pushed to Todos; voice: "what were the action items?", "summarize my last meeting" |
| WhatsApp Agent (experimental) | Opt-in (`FRIDAY_WHATSAPP_ENABLED=1`); FRIDAY's own Playwright driver for WhatsApp Web (no third-party libs — the PyPI package is a typosquat, the original is dead). QR pairing in the UI, unread chats, **approval-first send** ("message 91XXXXXXXXXX that …" → preview → confirm) |

### Voice command patterns (frontend fast-path)

| You say | F.R.I.D.A.Y. does |
|---|---|
| "open trading" / "trading workstation" | Opens Quantum Trading Workstation |
| "exit trading mode" / "go back" | Exits to the dashboard |
| "open dashboard" / "home" | Returns to the dashboard (never hijacked by Career) |
| "open career" / "job portal" | Opens Career OS |
| "open engineering console" / "open vscode" | Opens VS Code |
| "open browser" / "open chrome" | Opens the browser |
| "close <app>" / "quit <app>" | Closes the app (canonical names, incl. vs code/chrome) |
| "lock yourself" / "lock" | Locks the display |
| "what time is it" / "what's the date" | Answers time / date |
| "what's playing" / "kaun sa gaana" | Reports current Spotify track |
| "open Chrome/Spotify/VS Code…" | Launches the app |
| "close <app>" | Quits the app |
| "stop" / "shut up" | Interrupts speech |
| "exit trading mode" / "go back" | Returns to dashboard |

### Brain engine (server-side routing)

Anything not matched client-side is sent to the **dual-engine brain**:

1. **Groq (Llama 3.3 70B) function calling** — LLM receives all 24 tool schemas,
   decides which to call, engine dispatches → handler reply → spoken.
2. **Gemini failover** — structured JSON `{reply, function, args}` if Groq fails.
3. **Legacy regex brain** — always-works fallback for shortcuts.

---

## 3. The 24 Function Tools (in detail)

Every tool is a JSON-schema-registered capability the LLM can call. You can also
invoke them directly via `POST /api/agent/chat`.

### 🕐 Time & Weather
| Tool | What it does | Parameters |
|---|---|---|
| `get_time` | Current local date & time | — |
| `get_weather` | Live weather for your location (Open-Meteo + IP geolocation) | — |

### 🎵 Music
| Tool | What it does | Parameters |
|---|---|---|
| `play_spotify` | Search + play a specific song | `query` (song/artist) |
| `control_spotify` | Play / pause / next / previous / volume up / volume down / shuffle / repeat | `action` |
| `get_spotify_info` | Now-playing track + artist | — |

### ✅ Tasks & Reminders
| Tool | What it does | Parameters |
|---|---|---|
| `add_todo` | Add a task with priority | `text`, `priority` (high/normal/low) |
| `get_todos` | List pending tasks | — |
| `set_reminder` | Set a timer/reminder in N seconds | `message`, `seconds` |

### 💻 Computer Control
| Tool | What it does | Parameters |
|---|---|---|
| `open_app` | Open any macOS app (sanitized) | `app` |
| `system_control` | Brightness, dark mode, system volume, mute, lock display | `action`, `value` |
| `take_screenshot` | Screenshot the screen (permission: `screen.capture`) | — |
| `navigate_to` | Navigate UI: dashboard / trading / career | `destination` |

### 🌐 Web
| Tool | What it does | Parameters |
|---|---|---|
| `search_web` | DuckDuckGo instant-answer search | `query` |

### 📈 Trading
| Tool | What it does | Parameters |
|---|---|---|
| `technical_analysis` | Real TA on a symbol (RSI, MACD, Bollinger, ATR, Stochastic, VWAP, patterns, S/R) | `symbol` (e.g. `FX:EURUSD`, `OANDA:XAUUSD`), `interval` |
| `open_trading` / `close_trading` | Open / close the Trading Workstation | — |

### 🧠 Memory & Knowledge
| Tool | What it does | Parameters |
|---|---|---|
| `remember_fact` | Save a permanent fact (also as life-memory triple) | `key`, `value` |
| `search_memories` | Recall from life memory ("what's my salary preference?") | `query` |
| `remember_idea` | Capture a note, **auto-categorized** (idea/meeting/research/…) | `title`, `content`, `note_type?`, `tags?` |
| `search_notes` | Search the second brain ("where did I save that Kafka idea?") | `query` |
| `log_milestone` | Add a memory-timeline event ("Finished AI Attendance System") | `event`, `category`, `date?` |
| `update_goal` | Create or +progress a goal ("8 LPA job") | `title`, `amount`, `target?`, `category?` |

### 🎓 Learning
| Tool | What it does | Parameters |
|---|---|---|
| `log_learning` | Log a practice session for the Learning Coach | `title`, `category` (dsa/java/system_design/aws/interview_prep), `minutes`, `solved` |

### 👥 Access
| Tool | What it does | Parameters |
|---|---|---|
| `guest_permission` | Grant/revoke guest voice access (owner only) | `allow` |

---

## 4. All 128 API Endpoints (by module)

> Owner-only endpoints are marked 🔒. Everything under `/api/career/*`, `/api/dev/*`,
> and all write endpoints are owner-gated.

### 🧠 Chat & Brain
| Method | Endpoint | Description |
|---|---|---|
| POST 🔒 | `/api/chat/text` | Full brain (tool calling + failovers), 30 req/min rate limit |
| POST 🔒 | `/api/speech/correct` | Record a permanent speech correction |

### 🎵 Spotify
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/spotify/current-track` | Now-playing telemetry (title, artist, artwork, position) |
| POST 🔒 | `/api/spotify/seek` | Seek to position (seconds) |
| POST 🔒 | `/api/spotify/duck` · `/unduck` | Lower/restore volume while speaking |

### 💻 System Control
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/system/display` | Brightness, dark mode, volume, mute status |
| GET | `/api/system/stats` | Live CPU / RAM / Disk / Battery telemetry |
| POST 🔒 | `/api/system/display/brightness` | Set brightness 0–100 |
| POST 🔒 | `/api/system/display/dark-mode` | Toggle dark/light mode |
| POST 🔒 | `/api/system/display/volume` · `/mute` | System volume / mute |
| POST 🔒 | `/api/system/display/lock` | Lock the display |
| POST 🔒 | `/api/open-app` · `/close-app` | Launch / quit macOS apps (regex-sanitized) |

### ✅ Tasks & Reminders
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/todos` | List todos (sorted newest first) |
| POST 🔒 | `/api/todos` | Create todo (priority: high/normal/low) |
| PATCH 🔒 | `/api/todos/{id}/toggle` · `/text` | Toggle done / edit text |
| DELETE 🔒 | `/api/todos/{id}` · `/done` | Delete one / clear all done |
| GET | `/api/reminders` | Active timers |
| POST 🔒 | `/api/reminders` | Set a timer |

### 🌐 Utilities
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/tts` | Generate neural TTS → relative `/temp_audio/...` URL |
| GET | `/api/weather` | Live weather (Open-Meteo + IP geolocation) |
| POST | `/api/search` | DuckDuckGo instant-answer search |
| GET | `/api/gdrive/status` | Drive backup status |
| POST 🔒 | `/api/gdrive/sync-now` | Trigger DB snapshot backup now |

### 📈 Trading Workstation
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/trading/ohlcv` | OHLCV candles (intervals 1/5/15/30/60/240/D/W; FX/Crypto/Indices/US/Indian symbols) |
| GET | `/api/trading/analysis` | **Real technical analysis** with spoken summary |
| GET | `/api/trading/live-prices` | Cached global market prices (pollers run in background) |
| GET | `/api/trading/indian-prices` | NSE/BSE prices + market-open flag |
| GET | `/api/trading/search` | Search 5000+ symbols (Yahoo, with direct fallback) |
| GET/POST 🔒 | `/api/trading/chart-db` | Persist chart drawings per symbol |
| POST 🔒 | `/api/trading/order` | **Paper order only** — gated by `trades.execute` (default: ask) |

### 📋 Watchlist
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/watchlist` | Watchlist items (11 default symbols seeded) |
| POST 🔒 | `/api/watchlist` | Add/update symbol |
| DELETE 🔒 | `/api/watchlist/{symbol}` | Remove symbol |

### 🛡️ Permission Center
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/permissions` | All 18 capabilities + audit log |
| PUT 🔒 | `/api/permissions` | Set mode: enabled / ask / disabled |
| POST 🔒 | `/api/permissions/approve` | Grant 5-min one-time approval |
| POST 🔒 | `/api/permissions/revoke` | Revoke approval |
| POST 🔒 | `/api/permission` | Legacy guest-permission toggle |

### 🤖 Agents & Automations
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/agents` | List 6 agents + tool counts |
| POST 🔒 | `/api/agent/chat` | Route to best agent, run filtered brain |
| GET | `/api/agent/route` | Debug: which agent would handle this text |
| GET/POST/PUT/DELETE 🔒 | `/api/automations…` | CRUD scheduled workflows |
| POST 🔒 | `/api/automations/{id}/run` | Run an automation now |

### 🔔 Notifications & Briefing
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/notifications` | Inbox + unread count |
| POST 🔒 | `/api/notifications/{id}/read` | Mark read |
| GET | `/api/briefing` | Smart daily briefing (weather, tasks, reminders, career, markets, inbox) |

### 🧠 Knowledge OS
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/knowledge` | List notes (filter by type/project) |
| POST 🔒 | `/api/knowledge` | Add note (auto-categorized) |
| GET | `/api/knowledge/search` | Search second brain + natural recall answer |
| DELETE 🔒 | `/api/knowledge/{id}` | Delete note |
| GET | `/api/knowledge/projects…` | Project memory (9 sections per project) |
| PUT 🔒 | `/api/knowledge/projects/{p}/{section}` | Write a project section |

### 🕰️ Memory Timeline
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/timeline` | Timeline events + auto-derived events |
| POST 🔒 | `/api/timeline` | Log a milestone |
| GET | `/api/timeline/summary` | "last month" / "this year" period summary |
| DELETE 🔒 | `/api/timeline/{id}` | Remove event |

### 🎯 Goals
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/goals` | Goals + suggested skill gaps |
| POST 🔒 | `/api/goals` | Create goal (target, unit, deadline, skill gaps, resources) |
| PATCH 🔒 | `/api/goals/{id}` | Update goal |
| POST 🔒 | `/api/goals/{id}/progress` | +progress (auto-done at 100%) |
| DELETE 🔒 | `/api/goals/{id}` | Delete goal |

### 🎓 Learning Coach
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/learning` | Dashboard: streak, today, weekly goals, last-7-days |
| GET | `/api/learning/streak` | Current + best streak |
| POST 🔒 | `/api/learning/log` | Log a practice session |

### 💬 Life Memory
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/life-memory` | List (subject→relation→target) triples |
| POST 🔒 | `/api/life-memory` | Store a triple |
| GET | `/api/life-memory/search` | Search + natural answer ("what do I love?" → cold brew) |
| DELETE 🔒 | `/api/life-memory/{id}` | Delete memory |

### 🛠️ Developer Mode
| Method | Endpoint | Description |
|---|---|---|
| GET 🔒 | `/api/dev/overview` | Live counts (facts, notes, automations, notifications…) + uptime |
| GET 🔒 | `/api/dev/memory` | Facts + life memories + recent conversations |
| GET 🔒 | `/api/dev/logs` | Backend log tail (file + ring buffer) |
| GET 🔒 | `/api/dev/config` | Env keys set? (booleans only) + permission modes |
| POST 🔒 | `/api/dev/test` | In-process API tester (any method/path/body) |

### 💼 Career OS (42 endpoints)
| Group | Endpoints | Capabilities |
|---|---|---|
| **Dashboard** | `GET /dashboard` | Stats + AI briefing + recommendations (now with `reasons[]`) + activity |
| **Preferences** | `GET/PUT /preferences`, `POST /learn` | Tag-based prefs + natural-language learning ("tell FRIDAY…") |
| **Profile/Vault** | `GET/PUT /profile` | Encrypted personal vault (Fernet at rest) |
| **Resumes** | `GET/POST /resumes`, `GET/PUT/DELETE /resumes/{id}`, `POST /upload`, `/duplicate`, `/recommend`, `/delete` | Multi-version resumes, PDF/DOCX parsing with AI section extraction, ATS scoring, duplication, recommended-version |
| **Candidate Intelligence** | `GET /candidate-intelligence/{resume_id}` | SWOT, strengths, weaknesses, skill gaps, career roadmap |
| **Jobs** | `GET/POST /jobs`, `GET/PUT /jobs/{id}`, `POST /jobs/analyze`, `POST /jobs/fetch-linkedin` | Job CRUD, AI match scoring (Groq), live LinkedIn ingestion |
| **Applications** | `GET/POST /applications`, `PUT /applications/{id}` | Pipeline tracking: saved → applied → interview → offer |
| **Cover Letters** | `POST /cover-letter`, `GET /cover-letters` | AI-generated per job + resume, saved per job |
| **Interviews** | `GET/POST /interviews`, `PUT /interviews/{id}`, `POST /interviews/questions` | Schedule + track + AI prep questions |
| **Recruiters** | `GET/POST /recruiters`, `PUT /recruiters/{id}` | Recruiter CRM with contact history |
| **Companies** | `GET/POST /companies`, `POST /companies/blacklist` | Company tracker + blacklist |
| **Analytics** | `GET /analytics` | SVG charts: monthly apps, pipeline funnel, resume performance |
| **Skill Gap** | `GET /skill-gap` | AI skill-gap analysis vs. tracked jobs |
| **Accounts** | `POST /accounts/connect/{key}`, `POST /accounts/verify/{key}` | Real-browser session capture (Playwright); honest `needs_login` status |
| **Activity** | `GET /activity` | Full action log |

---

## 5. Permission Center (18 capabilities)

Every sensitive action is gated. Mode meanings:
- **Enabled** — allowed (still owner-auth'd)
- **Ask** — needs a one-time approval (default 5 min) via `POST /api/permissions/approve`
- **Disabled** — always blocked

| Capability | Default | Capability | Default |
|---|---|---|---|
| `system.control` | enabled | `email.send` | ask |
| `music.control` | enabled | `whatsapp.read` / `whatsapp.send` | ask |
| `tasks.write` | enabled | `phone.call` | ask |
| `web.search` | enabled | `calendar.write` | ask |
| `screen.capture` | ask | `jobs.apply` | ask |
| `gdrive.write` | enabled | `trades.execute` | ask |
| `vault.access` | enabled | `files.delete` | **disabled** |
| `email.read` | ask | `plugins.install` / `agent.autonomy` | ask |

**Enforced right now on:** `POST /api/trading/order` (trades.execute) and all
machine-control writes (system.control). Every decision is written to the audit log.

---

## 6. The 6 Agents

| Agent | Tools | Routes to |
|---|---|---|
| **Career** | time, todos, reminders, search, navigate, TA | "apply for java jobs", "resume", "interview", "salary" |
| **Coding** | open_app, time, search, screenshot, todos, reminders | "debug", "github", "vscode", "refactor" |
| **Research** | search, time, weather, todos, navigate | "research", "explain", "compare", "summarize" |
| **Finance** | TA, time, search, todos, reminders, navigate | "market", "trend on gold", "crypto", "nifty" |
| **Communication** | time, weather, todos, reminders, search | "email", "message", "calendar", "meeting" |
| **Automation** | time, todos, reminders, search, navigate | "automate", "schedule", "every morning", "briefing" |

Each agent runs the same brain but with a **filtered tool set** — it can only call
its own capabilities. Autonomy gated by `agent.autonomy` (default ask).

---

## 7. Automation Engine (4 actions)

| Action | What it does | Example |
|---|---|---|
| `briefing` | Generates smart daily briefing → Notification Center | every morning at 09:00 |
| `job_scan` | Scans tracked jobs; notifies high-match / high-salary | every 12 hours |
| `market_summary` | Summarizes watchlist prices → notification | daily at 18:00 |
| `learning_check` | Nudges when you've been idle ≥ 3 days | daily at 20:00 |

Triggers: `interval` (seconds ≥ 60) or `daily` (HH:MM). Runner is lifespan-managed.

---

## 8. Memory Systems (5 layers)

| System | Storage | Example |
|---|---|---|
| **Facts** | `memories` table | "boss_name = Prathvi Sahu" |
| **Conversation** | `conversation_history` (last 20 turns) | context for replies |
| **Life Memory** | `life_memories` triples | Boss → loves → cold brew |
| **Second Brain** | `kb_notes` + `project_memory` | Kafka idea, project decisions |
| **Timeline** | `timeline_events` | "Got internship" (2026-07-15) |

Learning Coach streaks, goal progress, job applications, and habits
(`user_action_habits`) round out the persistent state.

---

## 9. The 13 HUD Panels

| Panel | What it shows |
|---|---|
| **SpotifyCard** | Now playing, artwork, seek bar, play/pause/next/prev |
| **TodoCard** | Tasks with priority, filters, inline edit, voice creation |
| **WeatherCard** | Live weather + animated icon |
| **SystemMonitorCard** | CPU/RAM/Disk/Battery live charts |
| **WebSearchCard** | Inline DuckDuckGo search |
| **PermissionCenterCard** | All 18 permissions, mode cycling, 5-min approvals, audit feed |
| **NotificationCenterCard** | Inbox with unread badge, mark-read, run-briefing button |
| **LearningCoachCard** | Streak, today/week stats, weekly goals, log-session form, 7-day chart |
| **KnowledgeCard** | Notes (add/search/delete), Timeline (log + period summaries), Goals (create/progress) |
| **DevToolsCard** | Overview counts, memory viewer, log tail, API tester, config inspector |
| **LockScreen** | Glassmorphism + GLSL orb, fingerprint/passphrase unlock |
| **AccessCard / BottomBar / Corners** | HUD chrome |

---

## 10. Example Conversations (all real)

| You say | What happens |
|---|---|
| "Friday, play Kesariya" | `play_spotify` → Spotify plays the song, volume ducks while she speaks |
| "What's the trend on gold?" | Finance agent → `technical_analysis` on OANDA:XAUUSD → RSI/MACD/patterns spoken |
| "I solved 2 DSA problems today" | `log_learning` → streak updated, coach dashboard |
| "Remember this idea: build a plugin system" | `remember_idea` → auto-categorized note in second brain |
| "Where did I save that Kafka idea?" | `search_notes` → "Found: 'Kafka architecture idea' — in general notes" |
| "What changed last month?" | Timeline summary → grouped by category |
| "Add goal: get 8 LPA job" | `update_goal` → creates goal; track with "I'm 50% there" |
| "Apply for Java jobs above 8 LPA in Bangalore matching 90%" | Career agent prepares candidates; **approval required before any submission** (jobs.apply = ask) |
| "Check my emails every morning at 9" | Automation `briefing` scheduled → notifications inbox |
| "Open VS Code" | `open_app` → sanitized macOS launch |

---

## 11. Security Model

1. **Owner auth** — localhost = owner; non-localhost needs `FRIDAY_API_TOKEN` (401 otherwise). `is_boss` is never client-supplied.
2. **Proxy-header hardening** — uvicorn `--no-proxy-headers` blocks `X-Forwarded-For` spoofing.
3. **Permission Center** — 18 capabilities, ask/disabled for high-stakes actions.
4. **Encryption at rest** — career vault fields Fernet-encrypted (`FRIDAY_VAULT_KEY` or `.vault_key`).
5. **Honest status** — no fabricated "connected/verified" account states.
6. **Rate limiting** — chat + all career AI endpoints limited per IP.
7. **Trade safety** — `trades.execute` default ask; paper orders only.
8. **No blind submissions** — Career OS requires human approval.

---

## 12. Extending F.R.I.D.A.Y.

- **New capability** → register a function in `function_engine.py` (name, schema, handler) + optionally a permission in `permissions.py`.
- **New automation** → add an action to `automation.run_action()`.
- **New agent** → add to `agents.AGENTS` with its tool list + keywords.
- **New route module** → drop a file in `backend/routes/`, include in `app.py`.
- **New HUD panel** → copy any `Panels/*Card.jsx`, mount in `App.jsx`.

---

*Generated from the live codebase — commit `f1d37ee` (v3.3.0). All 128 endpoints,
24 tools, and 13 panels verified present in the running application.*
