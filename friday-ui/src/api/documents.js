import { API_BASE_URL } from './config.js';

const BASE = `${API_BASE_URL}/api/documents`;

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

/** Upload a document (PDF/DOCX/PPTX/XLSX/TXT) → extracted text stored. */
export async function uploadDocument(file) {
  const form = new FormData();
  form.append('file', file, file.name);
  const res = await fetch(`${BASE}/upload`, { method: 'POST', body: form });
  const data = await jsonOrThrow(res);
  return data.document;
}

/** List documents (snippet only). */
export async function fetchDocuments(limit = 50) {
  const res = await fetch(`${BASE}?limit=${limit}`);
  const data = await jsonOrThrow(res);
  return data.documents || [];
}

/** Full document (includes extracted text). */
export async function fetchDocument(id) {
  const res = await fetch(`${BASE}/${id}`);
  const data = await jsonOrThrow(res);
  return data.document;
}

/** Search documents by keyword. */
export async function searchDocuments(query) {
  const res = await fetch(`${BASE}/search?q=${encodeURIComponent(query)}`);
  const data = await jsonOrThrow(res);
  return data.documents || [];
}

/** Ask a question about a document (Groq RAG). */
export async function askDocument(id, question) {
  const res = await fetch(`${BASE}/${id}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });
  const data = await jsonOrThrow(res);
  return data.answer;
}

/** Summarize a document. */
export async function summarizeDocument(id) {
  const res = await fetch(`${BASE}/${id}/summarize`, { method: 'POST' });
  const data = await jsonOrThrow(res);
  return data.summary;
}

/** Compare two documents. */
export async function compareDocuments(ids) {
  const res = await fetch(`${BASE}/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids }),
  });
  const data = await jsonOrThrow(res);
  return data.comparison;
}

/** Delete a document. */
export async function deleteDocument(id) {
  const res = await fetch(`${BASE}/${id}`, { method: 'DELETE' });
  await jsonOrThrow(res);
}
