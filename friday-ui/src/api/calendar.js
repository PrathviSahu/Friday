import { API_BASE_URL } from './config.js';

const BASE = `${API_BASE_URL}/api/calendar`;

async function jsonOrThrow(res) {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = typeof body.detail === 'string' ? body.detail
        : (body.detail?.message || JSON.stringify(body.detail));
    } catch (_) { /* keep default */ }
    throw new Error(detail);
  }
  return res.json();
}

/** Connection status of the Google Calendar integration. */
export async function fetchCalendarStatus() {
  const res = await fetch(`${BASE}/status`);
  return jsonOrThrow(res);
}

/** Today's events. */
export async function fetchTodayEvents() {
  const res = await fetch(`${BASE}/today`);
  const data = await jsonOrThrow(res);
  return data.events || [];
}

/** Upcoming events for the next `days` days. */
export async function fetchUpcomingEvents(days = 7) {
  const res = await fetch(`${BASE}/upcoming?days=${days}`);
  const data = await jsonOrThrow(res);
  return data.events || [];
}

/** Search events by keyword. */
export async function searchCalendarEvents(query) {
  const res = await fetch(`${BASE}/search?q=${encodeURIComponent(query)}`);
  const data = await jsonOrThrow(res);
  return data.events || [];
}

/** Create a server-side event draft; returns { draft_id, preview }. */
export async function createEventDraft({ summary, start, end, description }) {
  const res = await fetch(`${BASE}/draft`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ summary, start, end, description }),
  });
  return jsonOrThrow(res);
}

/** Approval-first create: grant one-time calendar.write, then insert. */
export async function approveAndCreateEvent(draftId) {
  const approveRes = await fetch(`${API_BASE_URL}/api/permissions/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ capability: 'calendar.write', seconds: 180 }),
  });
  if (!approveRes.ok) {
    const body = await approveRes.json().catch(() => ({}));
    throw new Error(body.detail || 'Permission approval failed');
  }
  const res = await fetch(`${BASE}/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ draft_id: draftId }),
  });
  return jsonOrThrow(res);
}

/** Discard a pending event draft. */
export async function cancelEventDraft(draftId) {
  await fetch(`${BASE}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ draft_id: draftId }),
  }).catch(() => {});
}
