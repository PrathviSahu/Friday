import { API_BASE_URL } from './config.js';

const BASE = `${API_BASE_URL}/api/whatsapp`;

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

/** Driver state: { enabled, connected, pairing, error, ... } */
export async function fetchWhatsAppStatus() {
  const res = await fetch(`${BASE}/status`);
  return jsonOrThrow(res);
}

/** Current pairing QR (PNG data URL) while pairing. */
export async function fetchWhatsAppQr() {
  const res = await fetch(`${BASE}/qr`);
  return jsonOrThrow(res);
}

/** Recent chats with unread counts. */
export async function fetchChats(limit = 20) {
  const res = await fetch(`${BASE}/chats?limit=${limit}`);
  const data = await jsonOrThrow(res);
  return data.chats || [];
}

/** Create a server-side draft; returns { draft_id, preview }. */
export async function createWhatsAppDraft({ phone, message }) {
  const res = await fetch(`${BASE}/draft`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone, message }),
  });
  return jsonOrThrow(res);
}

/** Approval-first send: grant one-time whatsapp.send, then send draft. */
export async function approveAndSendWhatsApp(draftId) {
  const approveRes = await fetch(`${API_BASE_URL}/api/permissions/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ capability: 'whatsapp.send', seconds: 180 }),
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
export async function cancelWhatsAppDraft(draftId) {
  await fetch(`${BASE}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ draft_id: draftId }),
  }).catch(() => {});
}

/**
 * Send a message via WhatsApp Desktop (native macOS app).
 * Approval-first: grant permission, then call the desktop-send endpoint.
 */
export async function approveAndSendWhatsAppDesktop({ phone, message }) {
  const approveRes = await fetch(`${API_BASE_URL}/api/permissions/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ capability: 'whatsapp.send', seconds: 180 }),
  });
  if (!approveRes.ok) {
    const body = await approveRes.json().catch(() => ({}));
    throw new Error(body.detail || 'Permission approval failed');
  }
  const res = await fetch(`${BASE}/desktop-send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone, message }),
  });
  return jsonOrThrow(res);
}
