import { API_BASE_URL } from './config.js';

const BASE = `${API_BASE_URL}/api/meetings`;

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

/** List recent meetings. */
export async function fetchMeetings(limit = 20) {
  const res = await fetch(`${BASE}?limit=${limit}`);
  const data = await jsonOrThrow(res);
  return data.meetings || [];
}

/** Search meetings by keyword. */
export async function searchMeetings(query) {
  const res = await fetch(`${BASE}/search?q=${encodeURIComponent(query)}`);
  const data = await jsonOrThrow(res);
  return data.meetings || [];
}

/** All action items across meetings. */
export async function fetchActionItems() {
  const res = await fetch(`${BASE}/action-items`);
  const data = await jsonOrThrow(res);
  return data.action_items || [];
}

/** Process a pasted transcript (extract summary/action items via LLM). */
export async function processTranscript(transcript) {
  const res = await fetch(`${BASE}/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transcript }),
  });
  const data = await jsonOrThrow(res);
  return data.meeting;
}

/** Upload an audio recording → Whisper transcription → structured meeting. */
export async function transcribeMeeting(blob, filename = 'meeting.ogg') {
  const form = new FormData();
  form.append('audio', blob, filename);
  const res = await fetch(`${BASE}/transcribe`, { method: 'POST', body: form });
  const data = await jsonOrThrow(res);
  return data.meeting;
}

/** Push a meeting's action items into Todos. */
export async function pushMeetingTodos(meetingId) {
  const res = await fetch(`${BASE}/${meetingId}/todos`, { method: 'POST' });
  return jsonOrThrow(res);
}
