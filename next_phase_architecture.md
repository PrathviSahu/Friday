# 📐 F.R.I.D.A.Y. Phase 1 & Adaptive Learning Engine — Complete Technical Specification

> **Document Purpose**: Authoritative architectural specification for AI models, developers, and system integration.
> **Target Modules**: **Adaptive Self-Learning AI Engine (FIRST PRIORITY)**, macOS System Controls, Brave YouTube Controller, Apple Calendar Engine, and WhatsApp & Mail Agent.
> **Primary Technology Stack**: Python 3.14, FastAPI, SQLite (`friday_brain.db`), macOS AppleScript (`osascript`), Quartz Display Services, Web Speech API, React 19.

> [!NOTE]
> **Career OS (Career Intelligence Center)** was added as a separate module and is fully operational as of August 2026.
> See `architecture.md` and `README.md` for Career OS documentation.

---

## 1. High-Level Architecture & Intent Execution Sequence

```
+---------------------------------------------------------------------------------------+
|                                  USER VOICE / TEXT INPUT                              |
|                                "Friday brightness 80%"                                |
|                                "Friday play lofi in Brave"                            |
|                            "Friday send WhatsApp to Rohan"                            |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                               FRONTEND SPEECH LAYER (React)                           |
|  - Web Speech API STT with continuous reconnect watchdog                              |
|  - Phonetic wake-word stripping ("Friday", "Hey Friday", "Suno Friday")              |
|  - Voice Fingerprint Verification (Prem vs. Guest)                                    |
+---------------------------------------------------------------------------------------+
                                           |  HTTP POST /api/chat/text
                                           v
+---------------------------------------------------------------------------------------+
|                       ★ FIRST PRIORITY: AI BRAIN & LEARNING ENGINE                    |
|                               (learning_engine.py)                                    |
|                                                                                       |
|  1. Fast-Path Regex & Shortcut Evaluator (0ms latency execution)                      |
|  2. LLM Engine (Groq Llama 3.3 70B Primary -> Gemini 2.5 Failover)                     |
|  3. Self-Learning Memory & Preference Injector                                        |
|     - Queries user_corrections & user_action_habits in friday_brain.db               |
|     - Proactive verbal habit suggestions (S_habit >= 0.70)                            |
|     - Soft penalty weight (-40.0) applied to candidate targets                        |
|     - RAG semantic vector memory search across past conversation turns                |
|     - Dynamic pace matching brevity controller                                        |
+---------------------------------------------------------------------------------------+
                                           |
                    +----------------------+----------------------+
                    |                                             |
                    v                                             v
+---------------------------------------+     +---------------------------------------+
|       SYSTEM & CONTROL SERVICES       |     |         PERSISTENCE & STORAGE         |
|  - mac_controls.py  (Brightness/Shift)|     |  - friday_brain.db (FIRST PRIORITY)   |
|  - brave_youtube.py (Brave YouTube)   |     |    (habits, corrections, memory,      |
|  - mac_calendar.py  (Apple Calendar)  |     |     career tables — all unified)      |
|  - mac_communications.py (WhatsApp)  |     |  - friday_trading_db.sqlite (Stocks)  |
+---------------------------------------+     |  - todos.json (Persistent Tasks)      |
                                              +---------------------------------------+
                    |
                    v
+---------------------------------------------------------------------------------------+
|                                 macOS SYSTEM AUTOMATION                               |
|  - AppleScript (osascript) IPC commands targeting Brave, Spotify, Mail, Calendar      |
|  - Quartz Display Services / CoreDisplay for hardware brightness adjustment           |
+---------------------------------------------------------------------------------------+
```

---

## 2. ★ FIRST PRIORITY: Adaptive Self-Learning AI Engine (`learning_engine.py`)

### 🧠 A. Selected User Design Preferences
1. **Habit Learning**: **Proactive Verbal Suggestion Mode**  
   FRIDAY tracks usage frequency across hourly time slots. When habit confidence $S_{habit} \ge 0.70$ and frequency $N \ge 3$, FRIDAY proactively speaks up (e.g., *"Prem, it is 9:14 AM. Shall I open your Trading Workstation?"*).
2. **User Corrections**: **Soft Weight Penalty Mode (-40.0)**  
   When Prem corrects a choice (e.g. *"not the remix"*), FRIDAY applies a **soft penalty score reduction (-40.0)**. This heavily downgrades the rejected target for repeat queries while preserving flexibility if search context changes.
3. **Voice Reply Length**: **Dynamic Pace Matching Mode**  
   Input length determines output style:
   - Short inputs ($\le 5$ words): **Ultra-Concise** (1 sentence reply).
   - Medium inputs ($6-12$ words): **Balanced** (1-2 friendly sentences).
   - Long queries ($> 12$ words or explicit "explain"): **Detailed Explanation**.
4. **Memory Architecture**: **Unified SQLite + RAG Vector Store (`friday_learning.db`)**  
   Combines fast structured SQLite tables for habit/correction tracking with keyword-vector semantic memory for cross-session conversation retrieval.

---

### 📐 B. Mathematical Scoring & Ranking Equations

#### 1. Predictive Habit Confidence Score ($S_{habit}$)
Calculates the probability that Prem desires a specific automated action at current time slot $t$:

$$S_{habit}(a, h, d) = \frac{N(a, h, d)}{N_{total}(h, d)} \times e^{-\lambda \Delta t}$$

*Where*:
- $a$: Action type (e.g. `trading_station`, `lofi_music`, `weather_check`)
- $h \in [0..23]$: Hour of day
- $d \in [0..6]$: Day of week (0 = Monday, 6 = Sunday)
- $N(a, h, d)$: Execution count of action $a$ during time slot $(h, d)$
- $N_{total}(h, d)$: Total recorded actions during time slot $(h, d)$
- $\lambda$: Time-decay factor ($0.05$/day)
- $\Delta t$: Days elapsed since last execution

*Proactive Trigger Rule*: If $S_{habit}(a, h, d) \ge 0.70$ and $N(a, h, d) \ge 3$, FRIDAY generates a proactive voice announcement.

---

#### 2. Candidate Selection & Correction Ranking Score ($R_{candidate}$)
Determines the final score of a candidate item (e.g. song, search result, app option):

$$R_{candidate} = S_{title} + S_{artist} + S_{pop} + B_{exact} - P_{derivative} - P_{correction}$$

*Formulas*:
- **Title Similarity Score**: $S_{title} = \text{ratio}(\text{query}, \text{clean\_title}) \times 70.0$
- **Artist Similarity Score**: $S_{artist} = \text{ratio}(\text{query\_artist}, \text{candidate\_artist}) \times 15.0$
- **Popularity Score**: $S_{pop} = \left(\frac{\text{popularity}}{100}\right) \times 15.0$
- **Exact Match Bonus**: $B_{exact} = 35.0$ if $\text{query} == \text{clean\_title}$ else ($20.0$ if $\text{query} \subset \text{clean\_t}$)
- **Derivative Penalty**: $P_{derivative} = 40.0$ if title contains derivative keywords (`remix`, `sped up`, `slowed`, `lofi`, `cover`, `nightcore`, `8d`) absent from query
- **Soft Correction Penalty**: $P_{correction} = 40.0$ if candidate matches a previously logged `rejected_target` in `user_corrections` table

---

## 🗄️ 3. Complete Database Schemas (SQLite DDL)

> **Implementation Note**: All tables below are stored in the unified `friday_brain.db` database (WAL mode). The filenames `friday_learning.db` and `friday_hub.sqlite` below are the original Phase 1 spec names; they are consolidated in the live implementation.

### A. ★ FIRST PRIORITY: Learning Tables (live in `friday_brain.db`)

```sql
-- 1. Action Habits Table
CREATE TABLE IF NOT EXISTS user_action_habits (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type     TEXT NOT NULL,          -- 'trading_station', 'spotify_lofi', 'weather_check'
    hour_of_day     INTEGER NOT NULL,       -- 0..23
    day_of_week     INTEGER NOT NULL,       -- 0..6 (0=Monday)
    frequency       INTEGER DEFAULT 1,      -- Total execution count
    last_executed   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(action_type, hour_of_day, day_of_week)
);

-- 2. Soft Penalty Correction Table
CREATE TABLE IF NOT EXISTS user_corrections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    query_pattern   TEXT NOT NULL,          -- Normalized query string e.g. 'atlantis'
    rejected_target TEXT NOT NULL,          -- Rejected title/URI e.g. 'Atlantis (Sped Up)'
    preferred_target TEXT,                  -- User's preferred choice e.g. 'Atlantis by Seafret'
    penalty_weight  REAL DEFAULT -40.0,     -- Soft penalty score reduction
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(query_pattern, rejected_target)
);

-- 3. RAG Semantic Conversation Memories Table
CREATE TABLE IF NOT EXISTS conversation_memories (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    role            TEXT NOT NULL,          -- 'user' | 'assistant'
    message         TEXT NOT NULL,          -- Full text message
    tokens_json     TEXT,                   -- JSON array of extracted keywords
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### B. Hub & System Tables (live in `friday_brain.db`)

```sql
-- 1. Calendar Events Table
CREATE TABLE IF NOT EXISTS calendar_events (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    description     TEXT,
    location        TEXT,
    start_time      TIMESTAMP NOT NULL,
    end_time        TIMESTAMP NOT NULL,
    is_all_day      INTEGER DEFAULT 0,
    attendees       TEXT,                   -- JSON string array e.g. '["alex@gmail.com"]'
    status          TEXT DEFAULT 'scheduled',-- 'scheduled' | 'completed' | 'cancelled'
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Communication Logs & Drafts Table
CREATE TABLE IF NOT EXISTS communication_logs (
    id              TEXT PRIMARY KEY,
    platform        TEXT NOT NULL,          -- 'whatsapp' | 'email'
    recipient       TEXT NOT NULL,          -- Contact name or email address
    subject         TEXT,                   -- Email subject (NULL for WhatsApp)
    body            TEXT NOT NULL,          -- Message body text
    status          TEXT DEFAULT 'sent',    -- 'draft' | 'queued' | 'sent' | 'failed'
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 💻 4. Subsystem Technical Implementations

### A. Display & Hardware Controls (`mac_controls.py`)
- **Brightness Control**: Invokes macOS Quartz display services via AppleScript:
  ```applescript
  do shell script "brightness 0.8" -- or osascript CoreDisplay API call
  ```
- **Night Shift & Dark Mode**:
  ```applescript
  tell application "System Events"
      tell appearance preferences
          set dark mode to true -- or false
      end tell
  end tell
  ```

---

### B. Brave Browser & YouTube Controller (`brave_youtube.py`)
- **Brave Tab Target**: AppleScript scans Brave window titles for `"YouTube"`:
  ```applescript
  tell application "Brave Browser"
      repeat with w in windows
          repeat with t in tabs of w
              if title of t contains "YouTube" then
                  set active tab of w to t
                  set index of w to 1
                  activate
                  return true
              end if
          end repeat
      end repeat
  end tell
  ```
- **Media Control Key Injection**: Sends Space bar / `k` (toggle play/pause), `j` (rewind 10s), `l` (fast-forward 10s), or `N` (next video) directly to active YouTube tab.

---

### C. Apple Calendar Engine (`mac_calendar.py`)
- **Query Schedule**: AppleScript retrieves events for date range:
  ```applescript
  tell application "Calendar"
      set startDay to (current date)
      set endDay to startDay + (1 * days)
      tell calendar "Work"
          get summary of (every event whose start date >= startDay and start date < endDay)
      end tell
  end tell
  ```
- **Event Creation**: Parses natural language dates via LLM and inserts event cleanly.

---

### D. WhatsApp & Apple Mail Agent (`mac_communications.py`)
- **WhatsApp Web / Desktop Dispatch**:
  1. Opens URL scheme: `whatsapp://send?phone=...&text=...` or opens WhatsApp Desktop.
  2. Uses AppleScript clipboard paste (`_paste_text_via_clipboard`) to preserve Unicode/Devanagari characters.
  3. Executes `keystroke return` to send.
- **Apple Mail Draft / Reading**:
  - Fetches unread email count, sender names, and subject lines using `tell application "Mail"`.
  - Creates structured drafts ready for Prem's review.

---

## 📡 5. API Endpoint Specifications (JSON Contracts)

### 1. ★ FIRST PRIORITY: Fetch Learning Engine Stats & Habits
- **`GET /api/learning/habits`**
- **Response `200 OK`**: `{ "status": "ok", "habits": [...], "corrections_count": 5 }`

### 2. Adjust Screen Brightness
- **`POST /api/system/brightness`**
- **Request**: `{ "level": 80 }`
- **Response `200 OK`**: `{ "status": "ok", "brightness": 80 }`

### 3. Brave YouTube Media Command
- **`POST /api/brave/youtube`**
- **Request**: `{ "action": "search", "query": "lofi hip hop beats" }`
- **Response `200 OK`**: `{ "status": "ok", "action": "search", "playing": true }`

### 4. Fetch Calendar Events
- **`GET /api/calendar/events?date=2026-07-23`**
- **Response `200 OK`**: `{ "status": "ok", "date": "2026-07-23", "events": [...] }`

### 5. Send WhatsApp Message
- **`POST /api/messages/whatsapp`**
- **Request**: `{ "recipient": "Rohan", "text": "I am on my way Prem" }`
- **Response `200 OK`**: `{ "status": "ok", "platform": "whatsapp", "sent": true }`

---

## 🎙️ 6. Voice Intent Dictionary & Trigger Patterns

| Category | Intent Key | Regex / Voice Patterns (English & Hinglish) | Targeted Action |
|---|---|---|---|
| **Learning** | `SHOW_LEARNED_HABITS`| `what\s+have\s+you\s+learned\s+about\s+me`, `tumne\s+kya\s+seekha\s+hai` | `learning_engine.get_summary()` |
| **Display** | `SET_BRIGHTNESS` | `(?:set\s+)?brightness\s+(?:to\s+)?(\d{1,3})%?`, `screen\s+(?:bright|dull)\s+karo` | `mac_controls.set_brightness(pct)` |
| **Display** | `TOGGLE_DARK_MODE` | `turn\s+on\s+dark\s+mode`, `dark\s+mode\s+karo`, `toggle\s+night\s+shift` | `mac_controls.toggle_dark_mode()` |
| **Brave** | `BRAVE_YOUTUBE_SEARCH` | `play\s+(.*)\s+in\s+brave`, `brave\s+me\s+(.*)\s+chalao`, `search\s+youtube\s+for\s+(.*)` | `brave_youtube.search_and_play(query)` |
| **Brave** | `BRAVE_MEDIA_TOGGLE` | `pause\s+youtube`, `resume\s+youtube`, `youtube\s+roko`, `next\s+video\s+in\s+brave` | `brave_youtube.media_control(cmd)` |
| **Calendar** | `GET_AGENDA` | `what(?:'s|\s+is)\s+on\s+my\s+schedule`, `aaj\s+ka\s+schedule\s+kya\s+hai`, `check\s+calendar` | `mac_calendar.get_agenda()` |
| **Calendar** | `CREATE_EVENT` | `schedule\s+a\s+meeting\s+called\s+(.*)\s+at\s+(.*)`, `event\s+create\s+karo` | `mac_calendar.create_event(...)` |
| **Messages** | `SEND_WHATSAPP` | `send\s+(?:a\s+)?whatsapp\s+(?:message\s+)?to\s+(\w+):\s*(.*)`, `(\w+)\s+ko\s+whatsapp\s+karo\s+(.*)` | `mac_communications.send_whatsapp(...)` |
| **Messages** | `READ_EMAILS` | `check\s+(?:my\s+)?emails`, `urgent\s+emails\s+batao`, `read\s+unread\s+mail` | `mac_communications.get_unread_emails()` |

---

## 🗓️ 7. Build Execution Order (PRIORITY RE-ORDERED)

```
[Phase 1.1: AI Brain & Learning Engine] ---> [Phase 1.2: Display Controls] ---> [Phase 1.3: Brave YouTube]
                                                                                        |
[Phase 1.5: WhatsApp/Email Automation] <--- [Phase 1.4: Calendar Engine] <--------------+
```

1. **★ Phase 1.1 (FIRST PRIORITY)**: `learning_engine.py` (Habit logging, soft penalty corrections, dynamic pace matching brevity, and RAG semantic memory in `friday_learning.db`).
2. **Phase 1.2**: `mac_controls.py` (Screen Brightness 0-100% & Dark Mode / Night Shift toggle).
3. **Phase 1.3**: `brave_youtube.py` (Brave Browser tab focus & YouTube media controls).
4. **Phase 1.4**: `mac_calendar.py` & Calendar HUD Card (Apple Calendar API + `friday_hub.sqlite`).
5. **Phase 1.5**: `mac_communications.py` & Messaging HUD Card (WhatsApp Web & Apple Mail).

---
*Document Version*: 3.1.0 (Phase 1 AI Brain + Career OS added August 2026)
*Target Environment*: macOS Desktop System
*Authors & Lead Architects*: **Prem (Prathvi Sahu)** & **F.R.I.D.A.Y.**
*DB Note*: `friday_learning.db` and `friday_hub.sqlite` referenced in earlier revisions are consolidated into the single unified `friday_brain.db` database.
