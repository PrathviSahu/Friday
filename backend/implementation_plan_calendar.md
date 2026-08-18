# Phase 5.5C — Calendar Integration Implementation Plan

## 1. Current Architecture Audit
* **Existing Primitives**: `services/calendar_agent.py` contains low-level Google Calendar v3 API bindings, draft JSON persistence (`data/calendar_drafts.json`), and basic date parsing.
* **Reusable Assets**: Token file paths (`calendar_token.json`, `credentials.json`, `service_account.json`), Personal Vault integration (`career_db.py`), permission tiers, audit logger, and idempotency store.
* **Gap Identified**: No unified `CalendarProvider` ABC, no deterministic in-memory `MockCalendarProvider`, no cryptographic `content_hash` binding on draft events, no single-use approval token invalidation, no independent event verification.

---

## 2. Calendar Provider Boundary (`services/agent/integrations/calendar/`)
* **`provider.py`**:
  * `CalendarConnectionStatus`: `NOT_CONFIGURED`, `CREDENTIALS_STORED`, `CONNECTED`, `PARTIALLY_CONNECTED`, `AUTHENTICATION_FAILED`, `TEMPORARILY_UNAVAILABLE`.
  * `CalendarEvent`: Structured event with start/end datetimes, timezone, attendees, location, reminders, and recurrence.
  * `CalendarEventDraft`: Server-side draft with `draft_id`, `title`, `start_time`, `end_time`, `timezone`, `attendees`, `reminders`, 15-minute TTL, and SHA-256 `content_hash`.
  * `CalendarProvider` (ABC):
    * `check_connection() -> CalendarConnectionStatus`
    * `list_events(time_min, time_max, limit) -> List[CalendarEvent]`
    * `search_events(query, limit) -> List[CalendarEvent]`
    * `get_event(event_id) -> Optional[CalendarEvent]`
    * `create_draft_event(...) -> CalendarEventDraft`
    * `update_draft_event(...) -> Optional[CalendarEventDraft]`
    * `cancel_draft_event(draft_id) -> bool`
    * `create_event(...) -> CalendarCreateResult`
    * `verify_event(provider_event_id) -> CalendarVerificationResult`
    * `delete_event(event_id) -> bool` (Blocked / Non-autonomous)
* **`mock_provider.py`**: Deterministic in-memory provider seeded with mock interviews for offline testing & dry-run execution.
* **`google_provider.py`**: Live Google Calendar API provider controlled by `CALENDAR_LIVE_EXECUTION=false` (default: false).
* **`__init__.py`**: Provider factory `get_calendar_provider()` with test override support.

---

## 3. Security & Permission Model
* `get_calendar_events`, `search_calendar_events`, `get_calendar_event`: **Level 0 (READ_ONLY)**.
* `draft_calendar_event`, `update_calendar_event_draft`: **Level 1 (PREPARATION)**.
* `create_calendar_event`: **Level 2 (USER_APPROVAL)** requiring single-use scoped `PendingApproval` token.
* `delete_calendar_event`: **RiskLevel.BLOCKED** (no autonomous event deletion).
* **Draft $\neq$ Create**: Creating a draft never creates an event in the calendar.
* **Approval Invalidation**: Any draft modification (*"Make it 4 PM"*, *"Add reminder"*, *"Invite Sarah"*) generates a new content hash and invalidates prior approval tokens.
* **Prompt Injection Defense**: Event titles and descriptions are treated as UNTRUSTED DATA; system override tags (`[SYSTEM]`, `<|im_start|>`) are stripped and neutralized.
* **Timezone Safety**: Explicitly resolves timezone (`Asia/Kolkata` / `America/New_York` / system local) and never assumes silent UTC.

---

## 4. Test & Verification Strategy
* `tests/test_calendar_integration.py` covering:
  1. Connection states (NOT_CONFIGURED, CONNECTED)
  2. List & search read-only operations
  3. Draft creation & input validations (missing title, invalid times, invalid emails)
  4. Multi-turn edit flow with single-use approval invalidation
  5. User approval gating (Level 2)
  6. Independent provider verification (`provider_event_id`)
  7. Idempotency (preventing duplicate event creation)
  8. Sanitized audit logging (redacting OAuth tokens/secrets)
  9. Malicious prompt injection neutralization
  10. Real Google API isolation (`CALENDAR_LIVE_EXECUTION=false`)
