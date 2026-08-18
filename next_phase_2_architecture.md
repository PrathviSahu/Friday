# 📐 F.R.I.D.A.Y. Phase 2 — Proactive Autonomy & Ambient Intelligence — Complete Technical Specification

> **Document Purpose**: Authoritative architectural specification for AI models, developers, and system integration.
> **Predecessor**: `next_phase_architecture.md` (Phase 1 & Adaptive Learning Engine) — **fully shipped** as of August 2026.
> **Target Modules**: **Autonomy & Trust Engine (FIRST PRIORITY)**, Memory Consolidation & Forgetting, Ambient Context Engine, Voice Macro & Workflow Composer, and Cross-Device Presence.
> **Primary Technology Stack**: Python 3.14, FastAPI, SQLite (`friday_brain.db`), Groq (Llama 3.3 70B), Gemini 2.5 + `text-embedding-004`, React 19, Telegram Bot API, Web Push (PWA).

> [!NOTE]
> **Status: SHIPPED (August 2026).** This is the historical Phase-2 specification —
> all modules (Autonomy & Trust, Memory Consolidation, Context Engine, Voice
> Macros, Cross-Device Presence) are implemented and tested. For the current
> accurate architecture see [`README.md`](./README.md) and [`architecture.md`](./architecture.md).


> [!NOTE]
> **Design thesis** — Phase 1 → v4 taught FRIDAY to *respond* and *suggest*: 43 tools, an agentic loop, semantic memory, and scheduled automations. Phase 2 teaches her to **anticipate and act safely**: graduate proven habits from "Shall I…?" to silent execution under an explicit trust model, consolidate raw memory into durable knowledge, sense the user's situation before speaking, chain tools into user-defined voice macros, and keep every autonomous action approval-first on any device.

> [!IMPORTANT]
> **Implementation status (August 2026)**:
> - ✅ **Phase 2.1 — Autonomy & Trust Engine**: **BUILT & TESTED** — `services/autonomy_engine.py` (trust math `T = (A+1)/(A+R+2)·e^(−0.10·Δt)`, tier hysteresis 0.85/0.82, budget 4/h/class, quiet hours 22:00–07:00, 300s undo window, `action_trust` + `autonomy_journal` tables), routes `routes/autonomy.py` (`/api/autonomy/{status,journal,undo,revoke}`), HUD **Autonomy & Trust** panel (`friday-ui/.../AutonomyCard.jsx`), and 35 tests in `tests/test_autonomy.py`. One spec refinement shipped: `rejected` outcomes no longer clear `last_undo_at`, and failed dispatches are journaled with `outcome='failed'`.
> - ✅ **Phase 2.2 — Memory Consolidation & Forgetting**: **BUILT & TESTED** — `services/memory_consolidator.py` (LLM extract → semantic/Jaccard merge at 0.92/0.75 → Ebbinghaus decay k = ln2/60 with 30-day grace → prune < 0.20 to `archived`), `memory_digest` table, `memories` migration (+`access_count`, `last_accessed`, `last_decayed_at`, `archived`), access tracking + digest injection in `get_memory_context_string()`, nightly `consolidate_memory` automation action, routes `POST /api/memory/consolidate` + `GET /api/memory/digest`, 17 tests in `tests/test_memory_consolidation.py`. Refinements shipped: `last_decayed_at` on `memories` too (idempotent decay), consolidator touches `memories` only through learning_engine's connection.
> - ✅ **Phase 2.3 — Ambient Context Engine**: **BUILT & TESTED** — `services/context_engine.py` (on-demand Context Vector with 30s TTL cache, per-source graceful degradation, focus mode, calendar pressure `min(1, Σ1/(t/30))`, NSE market window in IST), wired into **autonomy** (meeting shield + focus force `confirm` — via the Phase 2.1 guard, zero engine changes), **brain.py** (brevity cap) and **brain_v2** ("🧭 CURRENT SITUATION" system-prompt line), 2 new Tool Router tools (`get_context`, `set_focus_mode` → 45 tools), routes `GET /api/context` + `POST /api/context/{focus,clear}`, 28 tests in `tests/test_context_engine.py`.
> - ✅ **Phase 2.4 — Voice Macro & Workflow Composer**: **BUILT & TESTED** — `services/macros.py` (`voice_macros` + `macro_runs` tables, registry-validated steps, min-tier inheritance, failing step halts the chain), **0ms exact-trigger fast path** in `brain.respond()` before any LLM call, voice creation/deletion via 2 new tools (`create_macro`, `delete_macro` → 47 tools), routes `POST/GET/DELETE /api/macros` + `POST /api/macros/{id}/run` (owner-gated), HUD **Voice Macros** panel, 27 tests in `tests/test_macros.py`. Refinements: macros are first-class `action_trust` rows (`macro:<trigger>`) so accepted runs feed the trust model; forced (HUD) runs dispatch directly — the owner's click is the approval — while organic runs route each step through `autonomy_engine.run` (journaled + undoable).
> - ✅ **Phase 2.5 — Cross-Device Presence**: **BUILT & TESTED** — `services/presence.py` (`presence_tokens` registry, one-time approval tokens TTL 300s, action resolvers `email_send_draft` / `macro_run`), **Telegram inline [ ✅ Approve ] [ ❌ Deny ]** keyboards riding the existing bot (auto device registration on `/start`, cross-thread sender via `post_init` loop capture, callback → `resolve_decision`), **PWA payload-free "tickle" Web Push** (zero-dependency VAPID ES256 JWT; service worker pulls pending + Approve/Deny actions), email-draft hook (`presence_prompt_sent`), routes `/api/presence/{register,devices,pending,ask,decision,vapid-key}` — devices only RESOLVE approvals via the standard Permission Center mechanism. 26 tests in `tests/test_presence.py`. Refinements: payload-free pushes avoid RFC 8291 encryption entirely (SW pulls instead of receives); approvals are consumed single-use, invalid decisions don't consume.

> [!IMPORTANT]
> **Relationship to existing code** — nothing in Phase 2 replaces shipped modules; every new engine *plugs into* them:
> - `learning_engine.py` (habits, corrections, pace matching) → consumed by the **Autonomy & Trust Engine** and **Memory Consolidator**.
> - `permissions.py` (enabled / ask / disabled + one-time approvals + `permission_audit`) → the Autonomy Engine **cannot** execute a capability whose policy blocks or requires interactive approval; trust is layered *under* permissions, never over them.
> - `automation.py` (lifespan-managed scheduled workflows) → hosts the Memory Consolidator as a nightly `consolidate_memory` action.
> - `brain_v2.py` (agentic tool loop, `max_steps`) → Voice Macros execute through the same Tool Router dispatch, so every macro step inherits permission checks, rate limits, and latency metrics.
> - `telegram_bot.py` → upgraded to two-way presence (approve / deny inline actions).

> [!WARNING]
> **Phase 1 erratum (fixed, August 2026)** — the escalating soft correction penalty in `learning_engine.detect_and_log_correction` used `MIN(penalty_weight - 10.0, -80.0)`; because penalties are negative, `MIN` selected the *more negative* value and jumped −40 → −80 on the second correction. Correct behavior (`MAX(...)`, −40 → −50 → … floored at −80) is restored and covered by `tests/test_learning_engine.py`. The equations in §2 below assume the corrected semantics.

---

## 1. High-Level Architecture & Sense-Decide-Act Sequence

```
+---------------------------------------------------------------------------------------+
|                              AMBIENT SIGNALS (always-on inference)                    |
|   clock   calendar pressure   unread mail   market open   focus mode   practice gap   |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                     ★ PHASE 2.1: AUTONOMY & TRUST ENGINE (autonomy_engine.py)         |
|                                                                                       |
|   SENSE  → learning_engine.get_proactive_habit_suggestion() (S_habit >= 0.70, N >= 3) |
|   DECIDE → Trust Score T(a) per action  ×  Permission Center policy  ×  autonomy      |
|            budget  ×  quiet hours  → tier: silent | announce | confirm                |
|   ACT    → Tool Router dispatch (43 tools) → journal entry + optional undo payload    |
|   LEARN  → acceptance / rejection feeds back into T(a) and user_action_habits         |
+---------------------------------------------------------------------------------------+
        |                    |                        |                        |
        v                    v                        v                        v
+----------------+  +---------------------+  +---------------------+  +--------------------+
| PHASE 2.2      |  | PHASE 2.3           |  | PHASE 2.4           |  | PHASE 2.5          |
| Memory         |  | Ambient Context     |  | Voice Macro &       |  | Cross-Device       |
| Consolidator   |  | Engine              |  | Workflow Composer   |  | Presence           |
| (nightly via   |  | (context_engine.py) |  | (macros.py)         |  | (PWA + Telegram    |
| automation.py) |  | fuses signals into  |  | multi-step routines |  | approve anywhere)  |
| distill +      |  | a Context Vector    |  | over the 43 tools   |  |                    |
| decay + dedupe |  | for the brain       |  |                     |  |                    |
+----------------+  +---------------------+  +---------------------+  +--------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                              PERSISTENCE & STORAGE                                    |
|   friday_brain.db  →  + action_trust, autonomy_journal, memory_digest,               |
|                        voice_macros, macro_runs, presence_tokens                      |
|   data/embeddings.db (unchanged — consolidated items re-indexed by Consolidator)      |
+---------------------------------------------------------------------------------------+
```

---

## 2. ★ FIRST PRIORITY: Autonomy & Trust Engine (`autonomy_engine.py`)

### 🧠 A. Design Decisions
1. **Graduated autonomy, not a switch**: each *action type* (e.g. `open_trading`, `play_hindi_playlist`, `weather`) earns autonomy independently. FRIDAY never becomes globally "hands-free".
2. **Approval-first is preserved end-to-end**: real-world-consequence capabilities stay governed by the Permission Center. Trust can only *reduce friction* on reversible, low-risk actions; it can never self-authorize a `disabled` capability or consume an `ask` approval.
3. **Every autonomous act is journaled and undoable** where a compensate operation exists (close trading window, pause music, dismiss notification). The HUD shows *"What FRIDAY did for you today"* from the journal.
4. **Anti-annoyance invariants** — hard limits regardless of trust:
   - **Autonomy budget**: ≤ 4 autonomous actions / hour / action class.
   - **Quiet hours**: 22:00–07:00 local → every action forced to `confirm` tier.
   - **Meeting shield**: if `context_engine` reports a meeting in progress or focus mode on → proactive output suppressed to the Notification Center.

---

### 📐 B. Mathematical Trust Model

#### 1. Bayesian Trust Score (per action type $a$)

$$T(a) = \frac{A(a) + 1}{A(a) + R(a) + 2} \times e^{-\lambda_T \, \Delta t_{act}}$$

*Where*:
- $A(a)$: accepted suggestions + un-undone silent executions of $a$ (successes)
- $R(a)$: rejected suggestions + **undo events** (undo counts as a strong rejection: weight ×2 into $R$)
- The $+1/+2$ Laplace prior keeps a brand-new action at $T = 0.50$ (neutral — `confirm` tier)
- $\lambda_T = 0.10$/day: trust decays 2× faster than habit memory ($\lambda = 0.05$) — stale confidence must be re-earned
- $\Delta t_{act}$: days since the last execution (accepted or auto)

#### 2. Tier Assignment with Hysteresis

$$
\text{tier}(a) =
\begin{cases}
\text{silent}   & T(a) \ge 0.85 \ \land\ N(a) \ge 10 \ \land\ \text{reversible}(a) \\
\text{announce} & 0.60 \le T(a) < 0.85 \ \land\ N(a) \ge 3 \\
\text{confirm}  & \text{otherwise}
\end{cases}
$$

- **Hysteresis band ±0.03**: an action must fall to $T < 0.82$ to *lose* `silent`, and rise to $T \ge 0.85$ to *gain* it — prevents tier flapping around the boundary.
- $N(a)$ = total executions from `user_action_habits`. The $N \ge 10$ gate for `silent` is hard: no amount of acceptance rate substitutes for sample size.
- **Safety class floor**: actions whose tool is tagged `irreversible` or `external_comm` (send email, send WhatsApp, create calendar event with attendees, job apply) are capped at `confirm` *forever* — trust only affects presentation, never gating, per the Phase 1 approval-first doctrine.

#### 3. Outcome Update Rule

After each suggestion/execution:

| Event | Update |
|---|---|
| User says "yes" / lets announce-tier run | $A \mathrel{+}= 1$ |
| User says "no" / dismisses | $R \mathrel{+}= 1$ |
| User invokes **undo** within 300s | $R \mathrel{+}= 2$, `last_undo_at` recorded, immediate recompute |
| Silent execution, no undo, no complaint in 300s | $A \mathrel{+}= 1$ |

Updates are written inside `_db_lock` with the same WAL / busy-timeout discipline as `learning_engine`.

---

## 🗄️ 3. Complete Database Schemas (SQLite DDL)

> All Phase 2 tables live in the unified `friday_brain.db` (WAL mode), alongside the Phase 1 tables. New columns on Phase 1 tables are added via guarded `ALTER TABLE` (``PRAGMA table_info`` check first) so existing databases migrate in place on boot.

### A. ★ Autonomy & Trust Tables

```sql
-- 1. Per-action trust ledger
CREATE TABLE IF NOT EXISTS action_trust (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type     TEXT NOT NULL UNIQUE,   -- matches learning_engine action names / tool names
    accepts         INTEGER DEFAULT 0,
    rejects         INTEGER DEFAULT 0,      -- rejections (undo adds +2)
    tier            TEXT DEFAULT 'confirm', -- 'silent' | 'announce' | 'confirm'
    last_acted_at   TIMESTAMP,
    last_undo_at    TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Autonomy journal (audit + undo)
CREATE TABLE IF NOT EXISTS autonomy_journal (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type     TEXT NOT NULL,
    tool_name       TEXT,                   -- Tool Router tool invoked
    tier            TEXT NOT NULL,          -- tier at time of execution
    params_json     TEXT,
    result_summary  TEXT,
    undo_payload    TEXT,                   -- JSON: {"tool": "close_trading", "params": {...}} or NULL
    undone          INTEGER DEFAULT 0,
    executed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### B. Memory Consolidation Tables

```sql
-- 3. Consolidated long-term knowledge digest
CREATE TABLE IF NOT EXISTS memory_digest (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    kind            TEXT NOT NULL,          -- 'fact' | 'pattern' | 'summary'
    content         TEXT NOT NULL UNIQUE,
    source_ids      TEXT,                   -- JSON array of conversation_history/memory ids
    confidence      REAL DEFAULT 1.0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_decayed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Schema migration (applied once, guarded):
--    ALTER TABLE memories ADD COLUMN access_count INTEGER DEFAULT 0;
--    ALTER TABLE memories ADD COLUMN last_accessed TIMESTAMP;
```

### C. Macro & Presence Tables

```sql
-- 5. Voice macros
CREATE TABLE IF NOT EXISTS voice_macros (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_phrase  TEXT NOT NULL UNIQUE,   -- normalized, e.g. 'start my morning'
    steps_json      TEXT NOT NULL,          -- [{"tool": "get_weather", "params": {}}, ...]
    enabled         INTEGER DEFAULT 1,
    created_by      TEXT DEFAULT 'voice',   -- 'voice' | 'hud'
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Macro run history (feeds trust + journal like any action)
CREATE TABLE IF NOT EXISTS macro_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    macro_id        INTEGER NOT NULL REFERENCES voice_macros(id),
    steps_ok        INTEGER DEFAULT 0,
    steps_failed    INTEGER DEFAULT 0,
    ran_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Presence device registry (PWA push + Telegram chat ids)
CREATE TABLE IF NOT EXISTS presence_tokens (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    device_kind     TEXT NOT NULL,          -- 'pwa' | 'telegram'
    token           TEXT NOT NULL UNIQUE,   -- Web Push subscription JSON or telegram chat_id
    label           TEXT,                   -- 'Prem's phone'
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 💻 4. Subsystem Technical Implementations

### A. ★ Autonomy & Trust Engine (`autonomy_engine.py`)
- **Decision entry point**: `decide(action_type) -> {'tier', 'trust', 'blocked_reason'}` — pure, side-effect-free, unit-testable. Called by the chat path (voice suggestion), the automation runner, and macro steps.
- **Execution flow**: `decide` → Permission Center `enforce(capability)` → dispatch via `function_engine.dispatch(tool, params)` → insert `autonomy_journal` row → schedule 300-second undo window → `record_outcome` on user response / timeout.
- **Undo dispatch**: undo payloads are ordinary Tool Router calls (e.g. `open_trading` ↔ `close_trading`, `play_spotify` ↔ `control_spotify:pause`) — no parallel machinery.
- **HUD**: new **Autonomy Panel** — today's journal, per-action trust bars, tier badges, one-tap "revoke autonomy for this action" (sets tier `confirm`, zeroes decays).

### B. Memory Consolidation & Forgetting (`memory_consolidator.py`)
- Registered as a nightly automation action: `consolidate_memory` (cron `03:30` local) through the existing `automation.py` lifespan runner — zero new daemons.
- **Pipeline** (each step graceful like `embeddings.py` — a broken LLM never breaks the night job):
  1. **Extract**: LLM pass over yesterday's `conversation_history` + new notes → candidate facts/patterns.
  2. **Cluster & merge**: cosine-match candidates against `memories` / `memory_digest` via the existing embeddings store; similarity ≥ 0.92 merges (confidence boosted +0.05, capped 1.0); otherwise insert new.
  3. **Decay (Ebbinghaus)**: for every memory with `last_accessed` older than 30 days: $c \leftarrow c \times e^{-k\,\Delta d}$, $k = \ln 2 / 60$ (half-life 60 days). Access (`search_semantic_memories`, brain injection) resets `last_accessed` and bumps `access_count`.
  4. **Prune**: confidence < 0.20 → archived out of brain context (kept in DB, excluded from prompts).
  5. **Report**: summary → Notification Center ("Consolidated 14 new facts, decayed 32, pruned 3").
- **Effect on the brain**: `get_memory_context_string()` reads consolidated high-confidence items first — shorter, denser prompts, lower token spend.

### C. Ambient Context Engine (`context_engine.py`)
- Computes a **Context Vector** on demand (no background polling; each source already has a fresh accessor):

```json
{
  "time_of_day": "morning",
  "day_type": "trading_weekday",
  "market_open": true,
  "next_meeting_in_min": 42,
  "meeting_now": false,
  "unread_email": 7,
  "calendar_pressure": 0.35,
  "practice_gap_days": 3,
  "focus_mode": false,
  "quiet_hours": false
}
```

- `calendar_pressure = min(1, Σ 1/(minutes_until_event_i / 30))` over today's remaining events — the brain uses it to shorten replies (interacts with `compute_response_brevity`), to order briefing sections, and to *suppress* proactive suggestions (meeting shield).
- **Focus mode**: `POST /api/context/focus {"minutes": 90}` or voice *"focus mode 90 minutes"* — mutes proactive tiers to `confirm`-only and routes notifications silently until expiry.

### D. Voice Macro & Workflow Composer (`macros.py`)
- **Voice creation**: *"Friday, when I say 'start my morning', open my trading station, give me the weather, and play lofi."* — the brain (function-calling) emits `create_macro(trigger_phrase, steps[])`; each step validated against the 43-tool registry before save.
- **Execution**: matched at chat entry (exact normalized trigger, before the LLM round-trip — 0ms fast path, same doctrine as Phase 1's fast-path evaluator, now layered *above* it for user-defined phrases) → steps dispatched sequentially through the Tool Router. A failing step halts the chain and reports which step failed.
- **Trust interplay**: each macro inherits the *minimum* tier of its steps; a macro containing a `confirm`-tier action is itself `confirm`. Macros appear as first-class rows in `action_trust` (`action_type = 'macro:start my morning'`).
- **HUD builder**: Macro panel — drag-order steps, per-step params, test-run button, run history from `macro_runs`.

### E. Cross-Device Presence (`presence/`)
- **Telegram upgrade** (extends `telegram_bot.py`, no new bot): pending approvals pushed with inline `[ ✅ Approve ] [ ❌ Deny ]` buttons → callback hits `POST /api/presence/decision` → resolves the pending `ask` token in the Permission Center (same one-time-approval mechanism, no parallel auth).
- **PWA push**: `friday-ui` registers a service worker; VAPID subscription stored in `presence_tokens`. Proactive `confirm`-tier suggestions and meeting reminders land as push notifications with Approve/Undo action buttons.
- **Security**: presence endpoints reuse the existing token auth (`X-FRIDAY-Token`) + owner-gating; a presence device can only *resolve* approvals, never mint new capabilities. Rate-limited like chat.

---

## 📡 5. API Endpoint Specifications (JSON Contracts)

### Autonomy & Trust
1. **`GET /api/autonomy/status`** → `{ "status": "ok", "actions": [{ "action_type": "open_trading", "trust": 0.91, "tier": "silent" }], "budget_remaining": 3 }`
2. **`GET /api/autonomy/journal?date=2026-08-08`** → `{ "status": "ok", "entries": [ { "action_type": "...", "tier": "...", "undone": 0 } ] }`
3. **`POST /api/autonomy/undo`** — `{ "journal_id": 12 }` → executes the stored undo payload → `{ "status": "ok", "undone": true }`
4. **`POST /api/autonomy/revoke`** — `{ "action_type": "open_trading" }` → forces `confirm` tier.

### Memory Consolidation
5. **`POST /api/memory/consolidate`** — manual trigger (owner-gated) → `{ "status": "ok", "new_facts": 14, "decayed": 32, "pruned": 3 }`
6. **`GET /api/memory/digest`** → `{ "status": "ok", "facts": [...], "pruned_count": 3 }`

### Ambient Context
7. **`GET /api/context`** → the Context Vector JSON above.
8. **`POST /api/context/focus`** — `{ "minutes": 90 }` → `{ "status": "ok", "focus_until": "2026-08-08T15:30:00" }`

### Macros
9. **`POST /api/macros`** — `{ "trigger_phrase": "start my morning", "steps": [ {"tool": "open_trading"}, {"tool": "get_weather"} ] }` → `201 Created`.
10. **`GET /api/macros`** / **`DELETE /api/macros/{id}`** — list / remove.
11. **`POST /api/macros/{id}/run`** → `{ "status": "ok", "steps_ok": 2, "steps_failed": 0 }`

### Presence
12. **`POST /api/presence/register`** — `{ "device_kind": "pwa", "token": "<subscription json>" }`
13. **`POST /api/presence/decision`** — `{ "approval_token": "...", "decision": "approve" }` → resolves pending Permission Center approval.

---

## 🎙️ 6. Voice Intent Dictionary & Trigger Patterns

| Category | Intent Key | Regex / Voice Patterns (English & Hinglish) | Targeted Action |
|---|---|---|---|
| **Autonomy** | `UNDO_LAST` | `undo\s+that`, `undo\s+karo`, `that\s+was\s+wrong\s+revert` | `autonomy_engine.undo_last()` |
| **Autonomy** | `SHOW_AUTONOMY` | `what\s+did\s+you\s+do\s+(for\s+me\s+)?today`, `aaj\s+tumne\s+kya\s+kiya` | `autonomy_engine.journal_today()` |
| **Autonomy** | `REVOKE_AUTONOMY` | `stop\s+doing\s+(.*)\s+automatically`, `(.*)\s+apne\s+aap\s+mat\s+karo` | `autonomy_engine.revoke(action)` |
| **Memory** | `CONSOLIDATE_NOW` | `consolidate\s+your\s+memories`, `memory\s+saaf\s+karo` | `memory_consolidator.run()` |
| **Context** | `FOCUS_MODE` | `focus\s+mode\s+(\d+)?\s*(minutes)?`, `disturb\s+mat\s+karo` | `context_engine.set_focus(min)` |
| **Context** | `READ_CONTEXT` | `what\s+do\s+you\s+know\s+right\s+now`, `situation\s+batao` | `context_engine.describe()` |
| **Macros** | `CREATE_MACRO` | `when\s+i\s+say\s+(.+?)\s*[,:]?\s*(.+)`, `jab\s+main\s+bolun\s+(.+?)\s+to\s+(.+)` | `macros.create(trigger, steps)` |
| **Macros** | `DELETE_MACRO` | `forget\s+the\s+(.+)\s+macro`, `(.+)\s+macro\s+delete\s+karo` | `macros.delete(trigger)` |
| **Macros** | *(any saved trigger phrase)* | matched exactly, 0ms fast path before LLM | `macros.run(trigger)` |
| **Presence** | `SEND_TO_PHONE` | `send\s+(?:this|it)\s+to\s+my\s+phone`, `phone\s+pe\s+bhejo` | `presence.push_last_result()` |

---

## 🗓️ 7. Build Execution Order (PRIORITY RE-ORDERED)

```
[Phase 2.1: Autonomy & Trust Engine] ---> [Phase 2.2: Memory Consolidator] ---> [Phase 2.3: Ambient Context]
                                                                                        |
[Phase 2.5: Cross-Device Presence] <--- [Phase 2.4: Voice Macro Composer] <------------+
```

1. **★ Phase 2.1 (FIRST PRIORITY)**: `autonomy_engine.py` + `action_trust` / `autonomy_journal` tables + Undo + Autonomy HUD panel. Everything else assumes trust-gated acting exists. ✅ **Built** (see status note above). **Acceptance**: unit tests for `decide()` tier math (incl. hysteresis and the 300s undo window) on a temp DB; journal round-trip via API — **34/34 passing** in `tests/test_autonomy.py`.
2. **Phase 2.2**: `memory_consolidator.py` as a nightly `automation.py` action + decay columns. ✅ **Built** — **Acceptance**: seeded conversations consolidate into `memory_digest`; confidence decays per §4-B; brain context shrinks on repeat runs (idempotent).
3. **Phase 2.3**: `context_engine.py` + `GET /api/context` + focus mode wired into brevity + proactive suppression. ✅ **Built** — **Acceptance**: meeting shield suppresses suggestions during a calendar event; focus mode forces `confirm` tier.
4. **Phase 2.4**: `macros.py` + voice creation + 0ms trigger match + Macro HUD panel. ✅ **Built** — **Acceptance**: create-run-delete a 3-step macro by voice; failing step halts the chain and reports.
5. **Phase 2.5**: Telegram inline approvals + PWA push (`presence_tokens`). ✅ **Built** — **Acceptance**: an `ask`-mode capability (e.g. send_email draft) can be approved from Telegram and executes; PWA receives proactive push with Undo.

---

*Document Version*: 5.1.0 (**Phase 2 FULLY IMPLEMENTED** — all five modules shipped and tested: 2.1 Autonomy & Trust, 2.2 Memory Consolidation, 2.3 Ambient Context, 2.4 Voice Macros, 2.5 Cross-Device Presence · August 2026)
*Target Environment*: macOS Desktop + Docker (all modules cross-platform; macOS-specific controls remain `IS_MAC`-guarded)
*Authors & Lead Architects*: **Prem (Prathvi Sahu)** & **F.R.I.D.A.Y.**
*DB Note*: All Phase 2 tables are added to the single unified `friday_brain.db`; the embeddings store (`data/embeddings.db`) remains a separate vector index, refreshed — never migrated — by the Memory Consolidator.
