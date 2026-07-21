# Friday Project Architecture Overview

**Document purpose**  
This file describes the high-level architecture of the *Friday* desktop assistant project, covering its major components, data flows, technology choices, and active Spotify automation integrations.

---

## 1. Project Vision
Friday is a personal AI assistant built for **Prem** (Prathvi Sahu) that:
- Listens continuously for voice wake-words (e.g., "Friday", "Hey Friday", "If Friday") and WebAuthn fingerprint authentication.
- Executes system automation on macOS (app control, smart volume routing, Spotify track/playlist control, YouTube & web search).
- Uses a dual-engine hybrid AI (Groq Llama 3.3 70B primary for ~150ms responses + Gemini 2.5 failover).
- Integrates Edge-TTS neural speech output with self-echo mic suppression and exponential backoff restart safety.

---

## 2. High-Level Diagram  

```
+---------------------+          HTTP / JSON          +-------------------------+
|  React 18 Frontend  | <---------------------------> |  FastAPI Python Backend |
|  (friday-ui)        |  POST /api/chat/text          |  (backend/app.py :8000) |
|  - useSpeech Hook   |  POST /api/tts                +-------------------------+
|  - WebAuthn Gate    |                                      /     |     \
+---------------------+                      +--------------+      |      +----------------+
                                             |                     |                       |
                                             v                     v                       v
                                  [ Fast-Path Shortcuts ]   [ Memory Engine ]    [ Dual-Engine LLM ]
                                             |               (JSON/SQLite)       - Groq 70B (150ms)
                                             v                                   - Gemini 2.5
                                 [ system_control.py ]
                                    (macOS AppleScript)
                                    /                 \
                          [ Spotify App ]        [ macOS System ]
                          - Direct URIs          - Output Volume
                          - Shuffle/Volume       - Open/Close Apps
```

---

## 3. Technology Stack  

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **UI** | React 18 + Vite + Tailwind CSS | Fast dev experience, modular UI, futuristic HUD styling. |
| **Voice STT** | Web Speech API (`en-US`) | Browser-native STT with exponential backoff on `no-speech` errors. |
| **Hooks** | `useSpeech.js`, `useOrbState.jsx` | Encapsulates speech lifecycle, mic mute state, and TTS echo guards. |
| **Backend API** | Python 3.11 + FastAPI + Uvicorn | High-performance asynchronous API server running at `http://localhost:8000`. |
| **Primary LLM** | Groq (`llama-3.3-70b-versatile`) | Ultra-fast (~150ms) intent extraction and natural conversational replies. |
| **Failover LLM** | Google Gemini 2.5 | Heavy reasoning and fallback handling if primary LLM fails. |
| **TTS Engine** | Edge-TTS (Microsoft Neural Voices) | Natural British female voice output with Web Speech API browser fallback. |
| **OS Automation** | Python `subprocess` + macOS AppleScript (`osascript`) | Native macOS control over Spotify, apps, browser URLs, and system volume. |
| **Security** | WebAuthn Platform Authenticator | Biometric fingerprint gate for LockScreen unlock. |

---

## 4. Directory Structure  

```
/FRIDAY
│
├── Friday-ui/                         # React Frontend (Vite)
│   ├── src/
│   │   ├── api/                      # fetchChatText.js API client
│   │   ├── components/               # LockScreen, BottomBar, Panels, Debug
│   │   ├── context/                  # FridayContext, FridaySync
│   │   ├── hooks/                    # useSpeech.js, useOrbState.jsx, voiceCommands.js
│   │   └── services/                 # ttsService.js
│   └── package.json
│
├── backend/                           # Python FastAPI Backend
│   ├── app.py                        # Main FastAPI server (:8000)
│   ├── services/
│   │   ├── brain.py                  # Groq/Gemini LLM engine + Fast-path shortcuts
│   │   ├── system_control.py         # macOS AppleScript system & Spotify automation
│   │   ├── memory.py                 # Permanent memory & preference storage
│   │   └── voice_auth.py             # Boss / Guest permission gating
│   └── requirements.txt
│
└── architecture.md                    # <--- This file (Updated Project Overview)
```

---

## 5. Active Spotify Automation & URIs

| Command | Action / URI | Trigger Phrases |
|---------|--------------|-----------------|
| **Hindi Playlist** | `spotify:playlist:4SuEAsJ6ulS62RYJk88Sap` | `"play my hindi playlist"`, `"hindi songs"`, `"apni playlist"` |
| **English Playlist** | `spotify:playlist:2CCKzQqgsc50gtJeYDonJh` | `"play my english playlist"`, `"english songs"` |
| **Radha Krishna Playlist** | `spotify:playlist:3Fd9z849SrTBEtHDTgQvXo` | `"play radha krishna playlist"`, `"krishna playlist"`, `"bhajan"` |
| **Shuffle Mode** | `set shuffling to true` | `"shuffle"`, `"play on shuffle"`, `"shuffel"` |
| **Pause / Resume** | Atomic AppleScript `play` / `pause` | `"pause music"`, `"stop music"`, `"resume music"` |
| **Smart Volume** | Spotify (if open) else macOS System Volume | `"volume 30%"`, `"set volume to 70"`, `"turn it down"` |

---

## 6. Security & Identity

- **Owner / Boss**: **Prem** (addressed as Prem across all replies and UI status).
- **Boss Gating**: System commands (app launch, volume, media control) are restricted to Prem.
- **Guest Access**: Guests can speak only when Prem explicitly says `"allow guest"`. Refused via `"revoke guest"`.

  - Prioritises longer phrases (e.g., “wake up”) before single‑word matches.  

### 5.2 LockScreen UI  
- Renders a fullscreen overlay when the OS is locked.  
- Handles fingerprint authentication via `useOrbState`.  
- Emits `runAuthSequence('wake', {speakImmediately:true})` on successful unlock.  

### 5.3 Backend API (`/api/chat/text`)  
- Receives JSON payload `{ text: string }`.  
- Forwards to the LLM (Claude / OpenAI) and returns `{ reply, action }`.  
- Errors are caught and re‑thrown as human‑readable messages.  

### 5.4 Voice Command Flow  
1. `useSpeech` captures audio → transcribes → extracts command.  
2. `handleCmd` checks for **local** commands via `matchVoiceCommand`.  
3. If none, sends request to backend (`fetchChatText`).  
4. Backend replies → `speak(reply)` (TTS) and updates conversation state.  

---  

## 6. Authentication & Security Flow  

1. **Fingerprint Prompt** – Triggered from the LockScreen component when the UI detects a locked state.  
2. **WebAuthn Call** – Browser asks OS for a biometric verification.  
3. **Successful Auth** – `runAuthSequence('wake', ...)` is dispatched, un‑locks the UI and enables voice listening.  
4. **Failed Auth** – Remains locked; voice listening stays disabled to avoid accidental commands.  

---  

## 7. API Contract (Backend)  

| Method | Endpoint | Request Body | Response |
|--------|----------|--------------|----------|
| POST   | `/api/chat/text` | `{ "text": "wake up" }` | `{ "reply": string, "action": string }` |
| (Optional) GET | `/status` | – | `{ "status":"ok" }` |

---  

## 8. Wake‑Word Detection – Current Issues & Fixes  

- **Symptom:** The voice pipeline sometimes hears “if Friday” or “stilll same error” instead of a clean wake‑word.  
- **Root cause:**  
  - The `WAKE_WORDS` list was incomplete (missing “wake”, “wake up”).  
  - `extractCommand` previously sliced after the *first* matched word without checking for trailing punctuation or longer multi‑word phrases.  
- **Fixes Implemented:**  
  1. Added explicit `"wake"` and `"wake up"` entries to `WAKE_WORDS`.  
  2. Refactored `extractCommand` to iterate over **all** known phrases, prioritising longer matches.  
  3. Trimmed and normalised the extracted command before returning.  

The recent `curl` test confirms that the backend correctly processes a raw wake‑up request:

```
{"reply":"I'm wide awake, Boss. Systems are green and waiting on your command.","action":"none"}
```

---  

## 9. Security Considerations  

- **Permission Model:** Microphone access requires a user gesture (click “Start Listening”). This prevents background eavesdropping.  
- **Biometric Data:** The project never stores raw fingerprint data; only a WebAuthn assertion is validated by the OS.  
- **Least‑Privilege API Calls:** The `/api/chat/text` endpoint only accepts plain text; no file uploads or privileged actions are exposed.  

---  

## 10. Deployment & Packaging  

1. **Development:** `npm run dev` – hot‑reload UI, backend auto‑restart (if separate).  
2. **Production Build:** `npm run build` – generates optimized static assets.  
3. **Packaging:**  
   - **Electron:** `electron-builder` config in `package.json`.  
   - **Tauri:** alternative lighter wrapper; requires Rust toolchain.  
4. **Distribution:** Signed installers for macOS, Windows, and Linux (AppImage/Snap).  

---  

## 11. Future Work  

| Area | Planned Enhancements |
|------|----------------------|
| **Wake‑Word Robustness** | Deploy a small on‑device keyword spotting model (e.g., Vosk) for offline detection. |
| **Command Parsing** | Introduce a full intent classifier (slot‑filling) to support complex commands (“open my calendar at 3pm”). |
| **Multi‑Modal Input** | Add image‑based UI commands (e.g., screenshot, draw). |
| **Persistent Memory** | Store conversation history in a local SQLite DB for context across sessions. |
| **Privacy Guard** | Add a “mute” toggle that disables microphone completely. |
| **Testing** | Expand unit tests for `useSpeech` and add integration tests for the API contract. |

---  

*Prepared by:*  
[Your Name] – Lead Architect, Friday Assistant  
Date: 2025‑11‑03  

---