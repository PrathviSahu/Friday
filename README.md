# ⚡ F.R.I.D.A.Y. — Voice-Controlled AI Operating System

> **F.R.I.D.A.Y.** is a full-stack, voice-controlled personal AI operating system inspired by Iron Man's J.A.R.V.I.S. — built with **React 19 + Vite 8** on the frontend and **Python FastAPI** on the backend, powered by **Groq (Llama 3.3 70B)** with **Google Gemini 2.5** failover.

**What it does in one line:** talk to it, and it manages your career, trading, tasks, notes, memory, documents, email, calendar, meetings, media and machine — through a holographic HUD that runs in any browser (desktop, mobile, PWA) or as a Tauri desktop shell.

| | |
|---|---|
| 🧪 Backend tests | **323 passing** (`pytest`) |
| 🧪 Frontend tests | **16 passing** (`vitest`) |
| 🔌 API surface | **195 REST operations across 168 `/api/*` paths** (from the running app's OpenAPI schema) |
| 🛠️ Function-calling tools | **47 JSON-schema tools** with a 4-step agentic loop |
| 🔐 Permission capabilities | **24** gated capabilities with audit log |
| 🧩 HUD capsules | **17** in the sliding dashboard |

---

## 🎬 90-Second Recruiter Demo

1. **Run it** (2 commands — Docker, no Python/Node setup):
   ```bash
   cp .env.example .env        # add GROQ_API_KEY + FRIDAY_API_TOKEN
   docker compose up -d --build
   # open http://localhost:8080
   ```
2. **Unlock** with any password (first password becomes the vault key).
3. **Say (or type):**
   - *"open career"* → AI Career OS (resumes, jobs, applications, interviews)
   - *"open trading"* → live markets workstation with real technical analysis
   - *"remember that I prefer cold brew"* → memory + life-memory graph
   - *"review this code"* → paste code → AI review/bugs/tests/docs/refactor
   - *"summarize my documents"* → upload PDF/DOCX → ask questions (RAG)

> ⚠️ System control (brightness, volume, open/close apps, Spotify) controls the **machine the backend runs on** — macOS when run natively via `./start.sh`, and auto-disabled (graceful no-op) inside Linux Docker/Render containers.

---

## 🗂️ What's Inside

### 🧠 AI Core — dual-engine, tool-calling, self-learning
- **Dual-LLM brain**: Groq `llama-3.3-70b-versatile` (low-latency primary) → Gemini 2.5 flash (failover pool) → deterministic fast-path handlers (<15 ms) → regex fallback. Model configurable via `GROQ_MODEL`.
- **47-tool function-calling engine** (`function_engine.py`): the LLM receives tool schemas and can chain **up to 4 tool calls per request**, feeding each result back ("check my email, then draft a reply" works in one shot).
- **Semantic memory (RAG)**: facts, notes and meetings are embedded with Gemini `text-embedding-004`; the top-3 relevant memories are injected per request — recall in your own words.
- **Conversation context**: the last 6 turns are included in every LLM call, so follow-ups work.
- **Self-learning**: voice correction detection ("No, I meant X") writes permanent corrections; action habits drive proactive suggestions (confidence ≥ 0.70); memory consolidation prunes + ranks facts.
- **Voice**: browser Web Speech API (instant) → **Groq Whisper `whisper-large-v3-turbo`** fallback → Gemini audio; **Edge-TTS** neural voices (`en-IN-NeerjaNeural` / `hi-IN-SwaraNeural`, auto Devanagari detection); barge-in; push-to-talk (Spacebar / mobile hold-to-talk); single-audio mutex guarantees zero overlapping voices.

### 💼 Career OS — an AI career operating system (12 modules)
Resume manager (multi-version, AI parsing of PDF/DOCX, ATS scoring), job board with **real LinkedIn scraping** (date filters, auto-refresh, dedupe), AI job-match scoring with reasoning, cover-letter generation, interview prep, application kanban, recruiter CRM, company tracker + blacklist, analytics, learning center with skill-gap roadmaps, encrypted personal vault, and natural-language preference learning. **Nothing is ever submitted without explicit approval.**

### 📈 Quantum Trading Workstation
TradingView Lightweight Charts with live OHLCV across 7 resolutions, a 5,000+-instrument universe (NSE/BSE, Forex, Crypto, US equities), a drag-and-drop SQLite-persisted watchlist, live 24/5 market pollers (lifespan-managed background threads), a **real technical-analysis engine** (SMA/EMA/RSI-Wilder/MACD/Bollinger/ATR/Stochastic/VWAP + candlestick patterns + trend confidence + S/R), and paper trading gated behind the `trades.execute` permission.

### 🧠 Knowledge OS & Memory
- **Second Brain** — auto-categorized notes (idea/meeting/research/code/interview/...), token + prefix search, project intelligence per project.
- **AI Memory Timeline** — chronological milestones ("what changed last month?") with auto-derived events.
- **Life Memory** — `subject → relation → target` triples answering connected questions ("what do I love?").
- **Goal Manager** — goals with progress %, deadlines, auto-suggested skill gaps.

### 🤖 Communication Center (approval-first, always)
Email agent (Gmail/Outlook IMAP+SMTP), Calendar agent (Google OAuth), Meeting assistant (Whisper → summary + action items → todos), WhatsApp agent (own Playwright driver, opt-in). Every agent only **creates a server-side draft**; the lock screen shows a preview and you confirm by voice or button — **nothing is ever sent without approval**.

### 📄📝📊 Document & Coding AI
- **Document AI**: upload PDF/DOCX/PPTX/XLSX/TXT → ask questions, summarize, compare (Groq RAG).
- **Coding AI**: paste code → review (bugs/security/style), explain, generate tests, generate docs, refactor.
- **Company Intelligence**: "Tell me about Goldman Sachs" → overview, hiring signals, your application history, interview-prep checklist.

### 🎓 Learning Coach · 🛠️ Developer Mode · ⏰ Automation
- **Learning Coach**: DSA/Java/System Design/AWS/Interview tracks — streaks, weekly goals, gentle reminders.
- **Automation Engine**: persisted scheduled workflows (`briefing`, `job_scan`, `market_summary`, `learning_check`) → Notification Center.
- **Smart Daily Briefing**: weather, tasks, calendar, career pipeline, markets, inbox → greeting + spoken summary.
- **Developer Mode**: in-app API tester, metrics (per-operation LLM/STT/TTS latency), memory browser, log tail, config checker (values never exposed).
- **Telegram bot**: reach FRIDAY from any phone (`/time`, `/weather`, `/market`, `/analyze`, free-form chat), gated by `TELEGRAM_OWNER_ID`.

### 🛡️ Security & Permission Center
- **Owner auth**: loopback is the owner; every other caller needs `FRIDAY_API_TOKEN` as `X-FRIDAY-Token` (constant-time compare). The API never trusts a client-supplied "I am the boss" flag, and uvicorn runs with `--no-proxy-headers` so `X-Forwarded-For` can't be spoofed.
- **Permission Center**: 24 capabilities with `enabled / ask / disabled` modes, persisted + audit-logged. High-stakes actions (send email, execute trades, apply to jobs, WhatsApp) default to `ask`; one-time approvals expire after 5 minutes.
- **Rate limiting**: per-IP sliding window on every LLM-costing endpoint.
- **Encryption at rest**: career credentials Fernet-encrypted (key from `FRIDAY_VAULT_KEY` or auto-generated `.vault_key`); the browser vault uses PBKDF2-250k + AES-GCM-256.
- **Honest status**: account verification returns `needs_login` until a real session exists — never fabricated "connected" responses.

---

## 🛠️ Technology Stack

| Domain | Technologies |
|---|---|
| **Frontend** | React 19, Vite 8, Tailwind CSS 4, Framer Motion, GSAP, React Three Fiber / Three.js (GLSL orb), TradingView Lightweight Charts, Web Speech API, WebAuthn (fingerprint), PWA |
| **Backend** | Python 3.11+, FastAPI, Uvicorn, SQLite (WAL, thread-safe), yfinance, numpy, psutil, asyncio, Playwright (career scraping + WhatsApp driver) |
| **AI** | Groq (Llama 3.3 70B Versatile), Google Gemini 2.5 flash, Gemini `text-embedding-004`, Groq Whisper `whisper-large-v3-turbo` (free-tier STT) |
| **Speech** | Web Speech API → Groq Whisper → Gemini audio; Edge-TTS `en-IN-NeerjaNeural` / `hi-IN-SwaraNeural`; barge-in; push-to-talk; single-audio mutex |
| **Integrations** | Spotify, Open-Meteo, Google Drive / Calendar APIs, Gmail/Outlook IMAP+SMTP, AppleScript, Telegram Bot API, WhatsApp Web (opt-in) |
| **Documents** | pypdf, python-docx, python-pptx, openpyxl |
| **Deployment** | Docker Compose (nginx frontend + FastAPI backend), Render, Vercel, Tauri 2 desktop shell |

---

## 📁 Directory Structure

```
FRIDAY/
├── README.md                       # This file
├── architecture.md                 # Technical architecture & system design
├── FRIDAY_CAPABILITIES.md          # Full capability reference (machine-accurate counts)
├── docker-compose.yml              # Backend + frontend containers
├── render.yaml                     # Render backend deployment blueprint
├── start.sh / stop.sh              # One-command native launcher / shutdown
│
├── backend/                        # Python FastAPI backend (:8000)
│   ├── app.py                      # Thin wiring: app assembly + lifespan lifecycle
│   ├── auth.py                     # Owner auth (loopback / FRIDAY_API_TOKEN)
│   ├── ratelimit.py                # Per-IP sliding-window rate limiter
│   ├── requirements.txt            # Python dependencies
│   ├── Dockerfile                  # Backend container (optional Playwright)
│   ├── data/                       # Persistent SQLite DBs + JSON (gitignored)
│   ├── routes/                     # 25 modular route modules (195 operations)
│   │   ├── chat.py  agents.py  automation.py  autonomy.py
│   │   ├── calendar.py  coding.py  company.py  context.py
│   │   ├── devtools.py  documents.py  email.py  knowledge.py
│   │   ├── learning.py  life_memory.py  macros.py  meetings.py
│   │   ├── presence.py  spotify.py  system.py  todos.py
│   │   ├── trading.py  utilities.py  watchlist.py  whatsapp.py
│   │   └── macros.py
│   ├── routers/
│   │   └── career.py               # Career OS REST API (32 paths, 43 operations)
│   ├── services/                   # Business logic layer
│   │   ├── brain/                  # Modular brain package + fast-path handlers
│   │   ├── brain_v2.py             # v4 agentic tool-loop brain (4 steps)
│   │   ├── function_engine.py      # 47-tool registry + dispatcher
│   │   ├── embeddings.py           # Gemini semantic-memory RAG
│   │   ├── technical_analysis.py   # Real TA engine
│   │   ├── career_db.py            # Career OS DB layer (encrypted vault)
│   │   ├── career_intelligence.py  # Career AI engine
│   │   ├── job_scraper.py          # LinkedIn scraper (Playwright)
│   │   ├── market_data.py / indian_market_data.py  # Live price pollers
│   │   ├── automation.py  briefing.py  notifications.py
│   │   ├── permissions.py          # 24-capability permission center
│   │   ├── autonomy_engine.py  presence.py  macros.py
│   │   ├── knowledge.py  timeline.py  goals.py  learning.py  life_memory.py
│   │   ├── memory.py  memory_consolidator.py  reminders.py  todos.py
│   │   ├── email_agent.py  calendar_agent.py  meeting_agent.py
│   │   ├── document_agent.py  coding_agent.py  company_intelligence.py
│   │   ├── whatsapp_agent.py  telegram_bot.py
│   │   ├── system_control.py  mac_controls.py  system_stats.py
│   │   ├── stt.py  tts.py  weather.py  web_search.py
│   │   ├── gdrive_api.py  gdrive_sync.py  platform_session.py
│   │   ├── metrics.py  voice_auth.py  context_engine.py  agents.py
│   │   └── learning_engine.py  chart_data.py  platform_session.py
│   ├── database/                   # SQLite access layer (WAL, thread-safe)
│   │   ├── connection.py  chart_db.py  watchlist_db.py
│   │   └── repositories/song_memory_repo.py
│   ├── speech/personal_vocabulary.py  # Permanent speech corrections
│   └── tests/                      # 323 pytest tests
│
└── friday-ui/                      # React 19 + Vite 8 frontend (:5173 / :8080)
    ├── index.html  vite.config.js  nginx.conf  Dockerfile
    ├── public/                     # favicon, sw.js (presence push), icons
    ├── src/
    │   ├── main.jsx  App.jsx  index.css
    │   ├── api/                    # Typed API clients + token injection
    │   ├── context/                # FridayContext, FridaySync
    │   ├── hooks/                  # useOrbState, useSpeech, useAudioQueue,
    │   │                           # useFingerprint (WebAuthn), useVault, ...
    │   ├── services/               # ttsService (audio mutex), secureVault, ...
    │   ├── components/             # LockScreen, HUD orb, Panels (17 capsules)
    │   └── UI/
    │       ├── Workspace.jsx       # Workspace router (dashboard / trading / career)
    │       ├── Dashboard/
    │       ├── TradingWorkstation/ # Quantum Trading Workstation
    │       └── Career/             # Career OS (12 modules)
    └── src-tauri/                  # Tauri 2 desktop shell
```

---

## 🚀 Quick Start

### Option A — Docker (recommended — Windows / macOS / Linux)

```bash
git clone <your-fork-url> && cd Friday
cp .env.example .env        # fill GROQ_API_KEY, GEMINI_API_KEY, FRIDAY_API_TOKEN
docker compose up -d --build
# open http://localhost:8080
```

Notes:
- **Auth**: every request in Docker is non-loopback, so all API access is gated by `FRIDAY_API_TOKEN` — the same value is baked into the frontend build automatically.
- **Data persists** in `./backend/data` (volume) — back it up.
- **Enable job scraping / WhatsApp** with `INSTALL_BROWSERS=1` in `.env` (~400 MB larger image).
- **macOS-only** automation (brightness, volume, open/close apps, Spotify) auto-disables inside containers (graceful no-op).

### Option B — Native macOS (full system automation)

```bash
# One command:
bash start.sh          # launches backend (:8000) + frontend (:5173)

# Or manually:
cd backend && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000 --no-proxy-headers

cd ../friday-ui && npm install && npm run dev
```

> `--no-proxy-headers` is mandatory: it stops uvicorn from trusting client-supplied `X-Forwarded-For`, which would otherwise let anyone spoof `127.0.0.1` and bypass owner authentication.

### Accessing Career OS
1. Unlock FRIDAY → Dashboard → **Career OS** button, **or**
2. Say **"open career"**.

### Telegram (phone access)
```bash
cd backend   # set TELEGRAM_BOT_TOKEN + TELEGRAM_OWNER_ID in backend/.env
python -m services.telegram_bot
```

### Running the tests
```bash
cd backend && python -m pytest tests/ -q      # 323 passing
cd friday-ui && npm test                       # 16 passing
cd friday-ui && npm run lint                   # oxlint, 0 errors
```

---

## 🌐 Deployment

| Target | How |
|---|---|
| **Docker Compose** | `docker compose up -d --build` (nginx frontend → FastAPI backend, same-origin) |
| **Render (backend)** | `render.yaml` blueprint; set `GROQ_API_KEY`, `GEMINI_API_KEY`, `FRIDAY_API_TOKEN`. **Do not** set `FRIDAY_MODE=demo` unless you want a public unauthenticated demo. Data is ephemeral on Render free — attach a persistent disk at `/app/data` or run the backend on your own machine for persistent storage. |
| **Vercel / static (frontend)** | build with standard `npm run build` (zero master secrets in bundle); SPA & API rewrites are handled server-side in `vercel.json`. |
| **Desktop** | `npm run tauri dev` / `npm run tauri build` (Tauri 2 shell with scoped CSP) |

---

## 🔒 Security Policy (implemented, not aspirational)

- **Owner authentication** — loopback = owner; all other callers require `FRIDAY_API_TOKEN` via `X-FRIDAY-Token` (constant-time comparison). No client-supplied identity is trusted.
- **Proxy-header spoofing is blocked** — uvicorn runs with `--no-proxy-headers` (Dockerfile, start.sh, app.py), so `X-Forwarded-For: 127.0.0.1` cannot impersonate the owner. Verified with a live remote-client test.
- **Every personal-data endpoint is gated** — todos, reminders, notes, timeline, goals, learning, life-memory, notifications, briefing, watchlist, saved chart drawings, system telemetry, TTS and web search all require auth (regression-tested).
- **Permission Center** — 24 capabilities, `enabled / ask / disabled`, audit-logged; high-stakes capabilities default to `ask`.
- **Rate limiting** — per-IP sliding window on all LLM-costing endpoints (chat, STT, career AI).
- **Encryption at rest** — Fernet for career credentials; PBKDF2-250k + AES-GCM-256 for the browser vault.
- **Honest status reporting** — no fabricated "connected"/"verified" responses.
- **Input sanitization** — AppleScript/system commands are whitelist-routed with strict regex sanitization.
- **Upload limits** — resume 5 MB, STT clips 10 MB; oversized uploads rejected with 413.
- **CORS** — explicit origin allowlist via `ALLOWED_ORIGINS`, explicit methods/headers, no wildcard credentials.

---

*Author / Lead Architect:* **Prem (Prathvi Sahu)** & **F.R.I.D.A.Y.**
*Last updated:* August 2026
