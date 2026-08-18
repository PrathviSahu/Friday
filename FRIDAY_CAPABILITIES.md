# ⚡ F.R.I.D.A.Y. — Complete Capability Reference

**Version:** v5.0 · **API surface:** 195 REST operations across 168 `/api/*` paths · **Function tools:** 47 · **Dashboard capsules:** 17 · **Permissions:** 24 · **Backend tests:** 323 passing · **Frontend tests:** 16 passing
**Stack:** React 19 + Vite 8 frontend · FastAPI backend · SQLite (WAL, thread-safe) · Groq (Llama 3.3 70B) / Gemini 2.5 LLM · Gemini `text-embedding-004` embeddings · Groq Whisper STT (`whisper-large-v3-turbo`) · Edge-TTS · Playwright (scraping / WhatsApp driver) · Docker / Render / Vercel / Tauri

> This document is the machine-accurate list of everything F.R.I.D.A.Y. can do.
> Every capability below is implemented and tested — none are placeholders.
> Counts are derived from the running app's OpenAPI schema, the tool registry,
> and the test suites (`pytest tests/` → 323 passed, `vitest` → 16 passed).

---

## 1. The Big Picture

F.R.I.D.A.Y. is a **voice-controlled Personal Operating System** built from seven
layers. Anything you can do in the UI you can also do by voice, and everything
remembers you over time.

| Layer | What it does | Where |
|---|---|---|
| **AI Core** | Conversation, intent routing, tool calling (47 tools), modular handler plugins, memory, agentic loop | `services/brain/`, `brain_v2.py`, `function_engine.py` |
| **Voice & Audio** | Wake word, single-audio mutex, STT (browser + Groq Whisper fallback), neural TTS, push-to-talk (Space / touch), barge-in | `ttsService.js`, `useSpeech.js`, `services/stt.py`, `tts.py` |
| **Career OS** | Resumes, jobs, LinkedIn ingestion, applications, interviews, recruiters, analytics | `routers/career.py` (32 paths, 43 operations), `services/job_scraper.py`, `CareerOS.jsx` |
| **Developer OS** | Quantum Trading workstation, real technical analysis, devtools | `routes/trading.py`, `routes/devtools.py`, `QuantumTradingWorkstation.jsx` |
| **Knowledge OS** | Second brain, memory timeline, life memory, goals, learning coach | `routes/knowledge.py`, `routes/learning.py`, `routes/life_memory.py` |
| **Stark HUD & Dashboard** | 17-in-1 holographic sliding capsule center with real-time search, category filters, live arming telemetry | `SlidingDashboard.jsx` |
| **Security & Access** | Owner auth, permission center (24 capabilities), encryption, audit log, presence push | `auth.py`, `permissions.py`, `routes/presence.py` |

> **Platform note:** machine-control capabilities (brightness, volume, lock,
> open/close apps, local Spotify) control **the host the backend runs on**.
> They are macOS-only and degrade gracefully (no-op) inside Linux Docker /
> Render containers. Everything else works identically everywhere.

---

## 2. Voice & Speech

| Capability | Detail |
|---|---|
| Single-Audio Mutex | **Guaranteed zero double-speaking.** Every utterance is tracked via a monotonically increasing sequence ID; any new command, interruption, or speech instantly interrupts and purges the previous audio pipeline |
| Wake word | "Hey Friday", "OK Friday", "Friday…" (stripped before processing) |
| Barge-in | Start talking while F.R.I.D.A.Y. is speaking → she stops instantly and listens |
| Push-to-Talk | Desktop **Spacebar hold** & mobile **thumb hold-to-talk**: mic activates only while held; releasing flushes the buffer instantly. Smart guard prevents Spacebar hijacking in text fields |
| Android Mic Release | `visibilitychange` listener tears down mic hardware when switching apps/minimizing — prevents Android "cannot record" conflicts |
| Speech-to-text | Browser Web Speech API (instant); auto-fallback to **Groq Whisper `whisper-large-v3-turbo`** (free tier) → Gemini audio. Hinglish-aware |
| Text-to-speech | Microsoft Edge-TTS — `en-IN-NeerjaNeural` (English), `hi-IN-SwaraNeural` (Hindi); auto-detects Devanagari; relative `/temp_audio/...` URLs |
| Spotify ducking | Music dips to 20% while speaking, restores after |
| Speech corrections | "No, I meant X" → permanently stored in personal vocabulary, applied to future STT |

### Brain intelligence (server-side)

1. **Context builder** — last 6 conversation turns + permanent facts + top-3
   semantic memories (Gemini embeddings RAG) injected into the prompt.
2. **Groq (Llama 3.3 70B) agentic loop** — LLM receives **47 tool schemas** and
   can chain **up to 4 tool-call rounds** per request (each result fed back)
   before answering. `send_*` / `create_*` tools only draft → approval action.
3. **Gemini failover** — structured JSON if Groq fails (also receives history +
   semantic context).
4. **Fast-path handlers** — deterministic sub-15 ms handlers for time, weather,
   volume, Spotify, navigation, macros, security/permissions.
5. **Legacy regex fallback** — always-works final fallback.

---

## 3. The 47 Function Tools

Every tool is a JSON-schema-registered capability the LLM can call, and the
brain can chain up to 4 tool-call rounds per request. You can also invoke the
brain directly via `POST /api/agent/chat` or `POST /api/chat/text`.

### 🕐 Time & Weather
| Tool | What it does | Parameters |
|---|---|---|
| `get_time` | Current local date & time | — |
| `get_weather` | Live weather (Open-Meteo + IP geolocation) | — |

### 🎵 Music & Media
| Tool | What it does | Parameters |
|---|---|---|
| `play_spotify` | Search + play a specific song | `query` |
| `control_spotify` | Play / pause / next / previous / volume / shuffle / repeat | `action` |
| `get_spotify_info` | Now-playing track + artist | — |
| `play_song_alias` | Resolve saved aliases ("gym song", "coding music") | `alias` |
| `add_song_alias` | Teach a new alias ("gym song = Believer") | `alias`, `song` |
| `get_music_player_state` / `seek_music` / `set_music_volume` | Liquid Player state / seek / volume | — |

### ✅ Tasks & Reminders
| Tool | What it does | Parameters |
|---|---|---|
| `add_todo` | Add a task with priority | `text`, `priority` |
| `get_todos` | List pending tasks | — |
| `set_reminder` | Set a timer/reminder in N seconds | `message`, `seconds` |

### 💻 Computer Control (macOS host)
| Tool | What it does | Parameters |
|---|---|---|
| `open_app` | Open a macOS app (whitelist-routed, sanitized) | `app` |
| `system_control` | Brightness, dark mode, system volume, mute, lock display | `action`, `value` |
| `take_screenshot` | Screenshot the screen (permission: `screen.capture`) | — |
| `navigate_to` | Navigate UI: dashboard / trading / career | `destination` |
| `run_macro` | Execute a saved macro | `macro_id` or name |

### 🌐 Web
| Tool | What it does | Parameters |
|---|---|---|
| `search_web` | DuckDuckGo instant-answer search | `query` |

### 📈 Trading
| Tool | What it does | Parameters |
|---|---|---|
| `technical_analysis` | Real TA (RSI, MACD, Bollinger, ATR, Stochastic, VWAP, patterns, S/R) | `symbol`, `interval` |
| `get_live_prices` | Cached global market prices | `symbols` |
| `open_trading` / `close_trading` | Open / close the Trading Workstation | — |

### 🧠 Memory & Knowledge
| Tool | What it does | Parameters |
|---|---|---|
| `remember_fact` | Save a permanent fact (also as life-memory triple + embedded) | `key`, `value` |
| `search_memories` | Recall from life memory ("what's my salary preference?") | `query` |
| `remember_idea` | Capture a note, auto-categorized + embedded | `title`, `content`, `note_type?`, `tags?` |
| `search_notes` | Search the second brain ("where did I save that Kafka idea?") | `query` |
| `log_milestone` | Add a memory-timeline event | `event`, `category`, `date?` |
| `update_goal` | Create or +progress a goal ("8 LPA job") | `title`, `amount`, `target?`, `category?` |
| `log_learning` | Log a practice session for the Learning Coach | `title`, `category`, `minutes`, `solved` |
| `search_timeline` | Period summaries ("what changed last month?") | `query` |

### ✉️ Email / 📅 Calendar / 🎙️ Meetings / 💬 WhatsApp / 📄 Documents
| Tool | What it does | Parameters |
|---|---|---|
| `check_email` / `search_email` / `send_email` | IMAP inbox, search, **draft-only → confirm before send** | `to`, `subject`, `body` |
| `check_calendar` / `search_calendar` / `create_calendar_event` | Today's events, search, **draft-only → confirm before create** | `summary`, `start`, `end?` |
| `meeting_action_items` / `search_meetings` / `last_meeting` | Action items, search, most-recent summary | `query` |
| `check_whatsapp` / `search_whatsapp` / `send_whatsapp` | Unread chats, search, **draft-only → confirm before send** | `phone`, `message` |
| `search_documents` / `ask_document` / `summarize_document` | Document RAG | `query` / `document` |

### 🏢 Company & Coding & Access
| Tool | What it does | Parameters |
|---|---|---|
| `company_intel` | Overview + hiring signals + your applications + interview prep | `company` |
| `review_code` | Review pasted code (bugs, security, style) | `code`, `language?` |
| `guest_permission` | Grant/revoke guest voice access (owner only) | `allow` |

*(The registry also includes the remaining automation / agent / reminder tools
— 47 total, all registered in `services/function_engine.py`.)*

---

## 4. All 195 API Operations (168 paths) — by module

> 🔒 = owner-gated (`X-FRIDAY-Token` or loopback). **Every personal-data read
> is gated** — verified by regression tests. Public-market-data GETs are gated
> too for defense-in-depth (the UI always sends the token).

### 🧠 Chat & Brain
| Method | Endpoint | Description |
|---|---|---|
| POST 🔒 | `/api/chat/text` | Full brain (fast-path → Groq → Gemini → fallback), 30 req/min rate limit |
| GET 🔒 | `/api/proactive` | Time-aware proactive suggestion FRIDAY can speak |
| GET/POST 🔒 | `/api/memory` | Long-term memory store |
| POST 🔒 | `/api/memory/consolidate` · GET 🔒 `/api/memory/digest` | Consolidation pass / digest |
| POST 🔒 | `/api/speech/correct` · `/api/speech/transcribe` | Permanent corrections / STT (10 MB cap) |

### ✉️ Email Agent
| Method | Endpoint | Description |
|---|---|---|
| GET 🔒 | `/api/email/unread` · `/summary` · `/search?q=` | Read inbox (never marks read) — `email.read` |
| POST 🔒 | `/api/email/draft` · `/send` · `/cancel` | Draft → preview → **confirm before send** |

### 📅 Calendar Agent
| Method | Endpoint | Description |
|---|---|---|
| GET 🔒 | `/api/calendar/status` · `/today` · `/upcoming` · `/search?q=` | OAuth status + events |
| POST 🔒 | `/api/calendar/draft` · `/create` · `/cancel` | Draft → preview → **confirm before create** |

### 🎙️ Meeting Assistant
| Method | Endpoint | Description |
|---|---|---|
| POST 🔒 | `/api/meetings/process` · `/transcribe` | Transcript/audio → summary + action items |
| GET 🔒 | `/api/meetings` · `/search?q=` · `/action-items` · `/{id}` | List / search / action items / full meeting |
| POST 🔒 | `/api/meetings/{id}/todos` | Push action items into Todos |

### 💬 WhatsApp Agent (experimental, opt-in)
| Method | Endpoint | Description |
|---|---|---|
| GET 🔒 | `/api/whatsapp/status` · `/qr` · `/chats` · `/search?q=` | Driver state / QR pairing / chats |
| POST 🔒 | `/api/whatsapp/draft` · `/send` · `/cancel` · `/desktop-send` | Draft → preview → **confirm before send** |

### 📄 Document AI
| Method | Endpoint | Description |
|---|---|---|
| POST 🔒 | `/api/documents/upload` (5 MB cap) | PDF/DOCX/PPTX/XLSX/TXT → text stored |
| GET 🔒 | `/api/documents` · `/search?q=` · `/{id}` | List / search / full text |
| POST 🔒 | `/api/documents/{id}/ask` · `/summarize` · `/compare` | RAG Q&A / summary / comparison |
| DELETE 🔒 | `/api/documents/{id}` | Remove a document |

### 🏢 Company / 👨💻 Coding
| Method | Endpoint | Description |
|---|---|---|
| GET 🔒 | `/api/company/intel?name=` | Company brief |
| POST 🔒 | `/api/coding/review` · `/bugs` · `/explain` · `/tests` · `/docs` · `/refactor` | Coding AI suite |

### 🎵 Spotify
| Method | Endpoint | Description |
|---|---|---|
| GET 🔒 | `/api/spotify/current-track` | Now-playing telemetry |
| POST 🔒 | `/api/spotify/seek` · `/duck` · `/unduck` | Seek / duck while speaking (macOS host) |

### 💻 System Control (macOS host)
| Method | Endpoint | Description |
|---|---|---|
| GET 🔒 | `/api/system/display` · `/stats` | Display status / live telemetry |
| POST 🔒 | `/api/system/display/brightness` · `/dark-mode` · `/volume` · `/mute` · `/lock` | Control the host machine |
| POST 🔒 | `/api/open-app` · `/close-app` | Launch / quit apps (regex-sanitized) |

### ✅ Tasks & Reminders
| Method | Endpoint | Description |
|---|---|---|
| GET 🔒 | `/api/todos` · `/api/reminders` | List tasks / timers |
| POST 🔒 | `/api/todos` · `/api/reminders` | Create |
| PATCH 🔒 | `/api/todos/{id}/toggle` · `/text` | Update |
| DELETE 🔒 | `/api/todos/{id}` · `/done` | Delete |

### 🌐 Utilities
| Method | Endpoint | Description |
|---|---|---|
| POST 🔒 | `/api/tts` | Neural TTS → relative `/temp_audio/...` URL |
| GET 🔒 | `/api/weather` | Live weather (Open-Meteo) |
| POST 🔒 | `/api/search` | DuckDuckGo instant-answer search |
| GET 🔒 | `/api/gdrive/status` · POST 🔒 `/api/gdrive/sync-now` | Drive backup status / trigger |

### 📈 Trading Workstation
| Method | Endpoint | Description |
|---|---|---|
| GET 🔒 | `/api/trading/ohlcv` | OHLCV candles (1/5/15/30/60/240/D/W; FX/Crypto/Indices/US/Indian) |
| GET 🔒 | `/api/trading/analysis` | **Real technical analysis** with spoken summary |
| GET 🔒 | `/api/trading/live-prices` · `/indian-prices` | Cached global + NSE/BSE prices |
| GET 🔒 | `/api/trading/search` | Symbol search |
| GET/POST 🔒 | `/api/trading/chart-db` | Persist chart drawings per symbol |
| POST 🔒 | `/api/trading/order` | **Paper order only** — gated by `trades.execute` (default ask) |

### 📋 Watchlist · 🛡️ Permission Center
| Method | Endpoint | Description |
|---|---|---|
| GET 🔒 | `/api/watchlist` · POST/DELETE 🔒 | Watchlist CRUD (11 default symbols seeded) |
| GET 🔒 | `/api/permissions` + audit log | All 24 capabilities |
| PUT 🔒 | `/api/permissions` · POST 🔒 `/approve` · `/revoke` | Modes + 5-min one-time approvals |
| POST 🔒 | `/api/permission` | Guest voice-permission toggle |

### 🤖 Agents · ⏰ Automations · 🔔 Notifications
| Method | Endpoint | Description |
|---|---|---|
| GET 🔒 | `/api/agents` · `/agent/route` | Agent list / routing debug |
| POST 🔒 | `/api/agent/chat` | Route to best agent with filtered tools |
| GET/POST/PUT/DELETE 🔒 | `/api/automations…` | Scheduled workflow CRUD + run-now |
| GET 🔒 | `/api/notifications` · POST 🔒 `/{id}/read` | Notification inbox |
| GET 🔒 | `/api/briefing` | Smart daily briefing |

### 🧠 Knowledge OS · 🕰️ Timeline · 🎯 Goals · 🎓 Learning · 💬 Life Memory
| Method | Endpoint | Description |
|---|---|---|
| GET/POST 🔒 | `/api/knowledge` · `/search` · `/projects…` | Second brain notes + project memory |
| GET/POST/DELETE 🔒 | `/api/timeline` · `/summary` | Memory timeline |
| GET/POST/PATCH/DELETE 🔒 | `/api/goals` · `/{id}/progress` | Goal manager |
| GET 🔒 | `/api/learning` · `/streak` · POST 🔒 `/log` | Learning coach |
| GET/POST/DELETE 🔒 | `/api/life-memory` · `/search` | Subject→relation→target triples |

### 🛠️ Developer Mode
| Method | Endpoint | Description |
|---|---|---|
| GET 🔒 | `/api/dev/overview` | Live counts + uptime |
| GET 🔒 | `/api/dev/metrics` | **Latency dashboard**: LLM/STT/TTS/tool averages |
| GET 🔒 | `/api/dev/memory` · `/logs` · `/config` | Memory browser / log tail / env booleans (values never exposed) |
| POST 🔒 | `/api/dev/test` | In-process API tester |

### 📱 Presence (cross-device push approvals)
| Method | Endpoint | Description |
|---|---|---|
| POST 🔒 | `/api/presence/register` · `/ask` · `/decision` | Device registration / approval create / resolve |
| GET 🔒 | `/api/presence/pending` · `/devices` · `/vapid-key` | Pending approvals / devices / push key |

### 💼 Career OS (32 paths, 43 operations)
| Group | Endpoints | Capabilities |
|---|---|---|
| **Dashboard** | `GET /dashboard` | Stats + AI briefing + recommendations (with `reasons[]`) + activity |
| **Preferences** | `GET/PUT /preferences`, `POST /learn` | Tag-based prefs + natural-language learning |
| **Profile** | `GET/PUT /profile` | Profile with Fernet-encrypted sensitive fields |
| **Resumes** | `GET/POST /resumes`, `GET/PUT/DELETE /resumes/{id}`, `POST /upload` (5 MB cap), `/duplicate`, `/recommend`, `/delete` | Multi-version resumes, AI section parsing, duplication, recommended-version |
| **Candidate Intelligence** | `GET /candidate-intelligence/{resume_id}` | SWOT, strengths, weaknesses, skill gaps, roadmap |
| **Jobs** | `GET/POST /jobs`, `GET/PUT /jobs/{id}`, `POST /jobs/analyze`, `/fetch-linkedin`, `DELETE /jobs/purge` | Job CRUD, AI match scoring, live LinkedIn ingestion, stale purge |
| **Applications** | `GET/POST /applications`, `PUT /applications/{id}` | Pipeline: saved → applied → interview → offer |
| **Cover Letters** | `POST /cover-letter`, `GET /cover-letters` | AI-generated per job + resume |
| **Interviews** | `GET/POST /interviews`, `PUT /interviews/{id}`, `POST /interviews/questions` | Schedule + track + AI prep questions |
| **Recruiters** | `GET/POST /recruiters`, `PUT /recruiters/{id}` | Recruiter CRM |
| **Companies** | `GET/POST /companies`, `POST /companies/blacklist` | Company tracker + blacklist |
| **Analytics / Skill Gap** | `GET /analytics`, `GET /skill-gap` | SVG charts + AI skill-gap analysis |
| **Accounts** | `POST /accounts/connect/{key}`, `POST /accounts/verify/{key}` | Real-browser session capture; honest `needs_login` status |
| **Activity** | `GET /activity` | Full action log |

---

## 5. Permission Center (24 capabilities)

Every sensitive action is gated. Mode meanings:
- **Enabled** — allowed (still owner-auth'd)
- **Ask** — needs a one-time approval (default 5 min) via `POST /api/permissions/approve`
- **Disabled** — always blocked

| Capability | Default | Capability | Default |
|---|---|---|---|
| `system.control` | enabled | `email.read` / `email.send` | ask |
| `music.control` | enabled | `calendar.read` / `calendar.write` | ask |
| `tasks.write` | enabled | `whatsapp.read` / `whatsapp.send` | ask |
| `web.search` | enabled | `phone.call` | ask |
| `screen.capture` | ask | `jobs.apply` | ask |
| `gdrive.write` | enabled | `trades.execute` | ask |
| `vault.access` | enabled | `files.delete` | **disabled** |
| `meetings.read` / `meetings.create` | enabled | `plugins.install` / `agent.autonomy` | ask |
| `documents.read` / `documents.upload` | enabled | `coding.analyze` | enabled |

**Enforced on:** `POST /api/trading/order` (trades.execute), all machine-control
writes (system.control), email/calendar/WhatsApp read & send routes, and every
agent module. Every decision is audit-logged.

---

## 6. The 6 Agents

| Agent | Capabilities | Routes to |
|---|---|---|
| **Career** | time, todos, reminders, search, navigate, TA, company_intel, … | "apply for java jobs", "resume", "interview", "salary", "tell me about Goldman Sachs" |
| **Coding** | open_app, time, search, screenshot, todos, reminders, review_code, … | "debug", "github", "vscode", "review my code" |
| **Research** | search, time, weather, todos, navigate, document tools, … | "research", "explain", "compare", "ask my documents about X" |
| **Finance** | TA, time, search, todos, reminders, navigate, live prices | "market", "trend on gold", "crypto", "nifty" |
| **Communication** | email ×3, calendar ×3, meetings ×3, whatsapp ×3, time, weather, … | "email", "message", "calendar", "meeting", "check whatsapp" |
| **Automation** | time, todos, reminders, search, navigate, … | "automate", "schedule", "every morning", "briefing" |

Each agent runs the same brain but with a **capability-filtered tool set** — it
can only call its own tools. Autonomy is gated by `agent.autonomy` (default ask).

---

## 7. Smart Brain (v4) — verification-backed

| Capability | How it works |
|---|---|
| **Conversation memory** | Last 6 turns injected into every LLM call — follow-ups work |
| **Semantic memory (RAG)** | Gemini `text-embedding-004` indexes facts, notes & meetings; top-3 relevant memories injected per request (keyword-search fallback without a key) |
| **Agentic tool loop** | Up to 4 tool-call rounds per request, each result fed back (`max_steps = 4` in `brain_v2.py`) |
| **Approval-first guard** | `send_*` / `create_*` tools only draft; the reply surfaces `email_confirm` / `calendar_confirm` / `whatsapp_confirm`, never auto-sends |
| **Honesty rules** | Prompt instructs "say you don't know" and "never claim a message was sent when you only previewed it" |
| **Configurable model** | `GROQ_MODEL` env var (default `llama-3.3-70b-versatile`) |

**Latency telemetry:** every LLM/STT/TTS/tool call is timed into a ring buffer —
see the **Latency tab** in DevTools or `GET /api/dev/metrics`.

---

## 8. Automation Engine (4 actions)

| Action | What it does | Example |
|---|---|---|
| `briefing` | Generates smart daily briefing → Notification Center | every morning at 09:00 |
| `job_scan` | Scans tracked jobs; notifies high-match / high-salary | every 12 hours |
| `market_summary` | Summarizes watchlist prices → notification | daily at 18:00 |
| `learning_check` | Nudges when idle ≥ 3 days | daily at 20:00 |

Triggers: `interval` (≥ 60 s) or `daily` (HH:MM). Runner is lifespan-managed.

---

## 9. Memory Systems (6 layers)

| System | Storage | Example |
|---|---|---|
| **Facts** | `memories` table (auto-embedded) | "boss_name = Prathvi Sahu" |
| **Conversation** | `conversation_history` (last 20 turns) | last 6 injected into every LLM call |
| **Semantic index** | `embeddings.db` (Gemini `text-embedding-004`) | "any big meetings coming up?" finds the interview fact |
| **Life Memory** | `life_memories` triples | Boss → loves → cold brew |
| **Second Brain** | `kb_notes` + `project_memory` (auto-embedded) | Kafka idea, project decisions |
| **Timeline** | `timeline_events` | "Got internship" (2026-07-15) |

Learning Coach streaks, goal progress, job applications, meetings, documents,
habits (`user_action_habits`, confidence ≥ 0.70 gating) round out the
persistent state — all in thread-safe SQLite (WAL).

---

## 10. The HUD — 17 Dashboard Capsules + Lock Screen

| Panel | What it shows |
|---|---|
| **SpotifyCard** | Now playing, artwork, seek bar, play/pause/next/prev (+ web "Liquid Player" previews) |
| **TodoCard** | Tasks with priority, filters, inline edit, voice creation |
| **WeatherCard** | Live weather + animated icon |
| **SystemMonitorCard** | CPU/RAM/Disk/Battery live charts |
| **WebSearchCard** | Inline DuckDuckGo search |
| **PermissionCenterCard** | All 24 permissions, mode cycling, 5-min approvals, audit feed |
| **NotificationCenterCard** | Inbox with unread badge, mark-read, run-briefing |
| **LearningCoachCard** | Streak, weekly goals, log-session form, 7-day chart |
| **KnowledgeCard** | Notes (add/search/delete), Timeline, Goals |
| **EmailCard** | Unread inbox, search, compose → preview → **confirm send** |
| **CalendarCard** | Today/upcoming/search, new event → preview → **confirm create** |
| **MeetingsCard** | Meeting list + search, Action Items, transcript → summary + push-to-todos |
| **WhatsAppCard** | QR pairing, unread chats, message → preview → **confirm send** |
| **DocumentsCard** | Upload, list, search, Ask & Summarize, compare |
| **CodingCard** | Paste code → Review / Bugs / Explain / Tests / Docs / Refactor |
| **DevToolsCard** | Overview counts, **Latency tab**, memory viewer, log tail, API tester, config inspector |
| **AutonomyCard** | Autonomous-action journal, undo, revoke |
| **LockScreen** | Glassmorphism + GLSL orb, WebAuthn fingerprint / typed-password unlock, now-playing |

---

## 11. Example Conversations (all real)

| You say | What happens |
|---|---|
| "Friday, play Kesariya" | `play_spotify` → plays on the host's Spotify; volume ducks while she speaks |
| "What's the trend on gold?" | Finance agent → `technical_analysis` on OANDA:XAUUSD → RSI/MACD/patterns spoken |
| "I solved 2 DSA problems today" | `log_learning` → streak updated |
| "Remember this idea: build a plugin system" | `remember_idea` → auto-categorized note in second brain |
| "Where did I save that Kafka idea?" | `search_notes` → found in general notes |
| "What changed last month?" | Timeline summary → grouped by category |
| "Add goal: get 8 LPA job" | `update_goal` → goal with progress tracking |
| "Apply for Java jobs above 8 LPA in Bangalore matching 90%" | Career agent prepares candidates; **approval required before any submission** |
| "Email rahul@x.com that I'll reach in 20 minutes" | `send_email` → **draft + approval card** — say "yes" to send |
| "Schedule a standup tomorrow at 10" | `create_calendar_event` → **draft + approval card** |
| "What were the action items?" | `meeting_action_items` → outstanding items |
| "Ask my documents about Java" | Document AI → answers from uploaded docs |
| "Tell me about Goldman Sachs" | `company_intel` → overview + hiring signals + your applications |
| "Open VS Code" | `open_app` → sanitized macOS launch (host machine) |
| "Play my gym song" | `play_song_alias` → saved alias resolves to Believer |

---

## 12. Security Model

1. **Owner auth** — localhost = owner; non-localhost needs `FRIDAY_API_TOKEN`
   (401 otherwise, constant-time compare). `is_boss` is never client-supplied.
2. **Proxy-header hardening** — uvicorn runs with `--no-proxy-headers` in every
   deployment path (Dockerfile, start.sh, app.py) so `X-Forwarded-For` cannot
   be spoofed into impersonating the owner. Verified live.
3. **Full read-path gating** — every personal-data read endpoint requires auth
   (regression-tested: 28 endpoints).
4. **Permission Center** — 24 capabilities; ask/disabled for high-stakes actions.
5. **Encryption at rest** — career vault fields Fernet-encrypted; browser vault
   PBKDF2-250k + AES-GCM-256; passphrase never persisted.
6. **Honest status** — no fabricated "connected/verified" account states.
7. **Rate limiting** — chat, speech, meetings, career AI endpoints limited per IP.
8. **Trade safety** — `trades.execute` default ask; paper orders only.
9. **No blind submissions** — Career OS requires human approval.
10. **Approval-first everywhere** — email/WhatsApp send + calendar create only
    act on server-side previewed drafts; the LLM can never auto-send.
11. **Upload caps** — resumes 5 MB, STT clips 10 MB, meetings 25 MB (413 on overage).
12. **Data integrity** — SQLite WAL + busy_timeout; thread-locked JSON stores.

---

## 13. Test Suite (323 backend + 16 frontend)

```bash
cd backend && python -m pytest tests/ -q          # 323 passed
cd friday-ui && npm test                           # 16 passed
cd friday-ui && npm run lint                       # oxlint: 0 errors
```

Coverage highlights: auth gates (loopback / token / remote rejection incl. all
read paths), honest account verification, TTS relative URLs, upload caps,
sliding-window rate limiter, Fernet vault round-trip, function-engine dispatch
+ Gemini fallback, TA math + candlestick patterns, permission enforcement,
automation CRUD + run-now, briefing structure, agent routing + tool filtering,
presence API, macros, learning streaks, life-memory save/search/recall, dev
tools, WhatsApp + email + calendar + meetings + documents API contracts.

---

## 14. Extending F.R.I.D.A.Y.

- **New capability** → register a function in `function_engine.py` (name, schema, handler) + optionally a permission in `permissions.py`.
- **New send/create capability** → follow the approval-first pattern: draft store with TTL + `POST /{module}/draft` → `/{module}/send` gated by permission; surface `*_confirm` from `brain_v2`; reuse `PendingApprovalCard`.
- **New automation** → add an action to `automation.run_action()`.
- **New agent** → add to `agents.AGENTS` with its capability list + keywords.
- **New route module** → drop a file in `backend/routes/`, include in `app.py`.
- **New HUD panel** → copy any `Panels/*Card.jsx`, mount in `App.jsx`.
- **New knowledge source** → index it via `embeddings.index_text()`.
- **Instrument a call** → wrap with `metrics.timed("op_name")` to see it in the Latency tab.

---

*Generated from the live codebase — v5.0. All 195 API operations (168 paths),
47 tools, 24 permissions, 17 capsules, and 323 tests verified present in the
running application.*
