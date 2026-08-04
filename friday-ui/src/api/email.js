import { API_BASE_URL } from './config.js';

const BASE = `${API_BASE_URL}/api/email`;

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

/** Recent unread emails (server never marks them read). */
export async function fetchUnread(limit = 15) {
  const res = await fetch(`${BASE}/unread?limit=${limit}`);
  const data = await jsonOrThrow(res);
  return data.unread || [];
}

/** Aggregated inbox summary. */
export async function fetchEmailSummary() {
  const res = await fetch(`${BASE}/summary`);
  const data = await jsonOrThrow(res);
  return data.summary || null;
}

/** Search inbox by subject/from. */
export async function searchEmails(query) {
  const res = await fetch(`${BASE}/search?q=${encodeURIComponent(query)}`);
  const data = await jsonOrThrow(res);
  return data.results || [];
}

/** Create a server-side draft; returns { draft_id, preview, expires_in_seconds }. */
export async function createEmailDraft({ to, subject, body }) {
  const res = await fetch(`${BASE}/draft`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ to, subject, body }),
  });
  return jsonOrThrow(res);
}

/**
 * Approval-first send: grants a short-lived one-time approval for email.send
 * (the user just confirmed in the UI), then sends the server-side draft.
 */
export async function approveAndSendEmail(draftId) {
  const approveRes = await fetch(`${API_BASE_URL}/api/permissions/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ capability: 'email.send', seconds: 180 }),
  });
  if (!approveRes.ok) {
    const body = await approveRes.json().catch(() => ({}));
    throw new Error(body.detail || 'Permission approval failed');
  }

  const res = await fetch(`${BASE}/send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ draft_id: draftId }),
  });
  return jsonOrThrow(res);
}

/** Discard a pending draft. */
export async function cancelEmailDraft(draftId) {
  await fetch(`${BASE}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ draft_id: draftId }),
  }).catch(() => {});
}
