/**
 * config.js — Centralized API configuration for F.R.I.D.A.Y. frontend.
 *
 * Default: relative URLs (''). In development the Vite dev server proxies
 * /api and /temp_audio to the FastAPI backend on 127.0.0.1:8000, so the app
 * works no matter which host/port the UI itself is served from (localhost,
 * LAN IP, the Arena preview, etc.).
 *
 * For production builds (e.g. the Tauri shell) point VITE_API_URL at the
 * backend, e.g. `VITE_API_URL=http://localhost:8000 npm run build`.
 */

export const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// API token for non-loopback deployments (Docker). Baked in at build time
// via VITE_FRIDAY_TOKEN (docker-compose passes FRIDAY_API_TOKEN). Empty in
// the native/dev setup, where loopback auth applies instead.
export const FRIDAY_TOKEN = (import.meta.env.VITE_FRIDAY_TOKEN || '').trim();

// When a token is configured, attach X-FRIDAY-Token to every fetch so the
// backend accepts requests that arrive from non-loopback addresses (e.g.
// Docker's bridge network). This wraps window.fetch once at import time and
// covers every API module automatically.
if (FRIDAY_TOKEN && typeof window !== 'undefined' && !window.fetch.__fridayAuthWrapped) {
  const originalFetch = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const headers = new Headers(init && init.headers);
    if (!headers.has('X-FRIDAY-Token')) {
      headers.set('X-FRIDAY-Token', FRIDAY_TOKEN);
    }
    return originalFetch(input, { ...init, headers });
  };
  window.fetch.__fridayAuthWrapped = true;
}

export const API_ENDPOINTS = {
  chatText: `${API_BASE_URL}/api/chat/text`,
  speechTranscribe: `${API_BASE_URL}/api/speech/transcribe`,
  tts: `${API_BASE_URL}/api/tts`,
  career: `${API_BASE_URL}/api/career`,
  trading: `${API_BASE_URL}/api/trading`,
  system: `${API_BASE_URL}/api/system`,
  todos: `${API_BASE_URL}/api/todos`,
  weather: `${API_BASE_URL}/api/weather`,
  spotify: `${API_BASE_URL}/api/spotify`,
  search: `${API_BASE_URL}/api/search`,
  proactive: `${API_BASE_URL}/api/proactive`,
  watchlist: `${API_BASE_URL}/api/watchlist`,
  openApp: `${API_BASE_URL}/api/open-app`,
  closeApp: `${API_BASE_URL}/api/close-app`,
  permissions: `${API_BASE_URL}/api/permissions`,
  automations: `${API_BASE_URL}/api/automations`,
  notifications: `${API_BASE_URL}/api/notifications`,
  briefing: `${API_BASE_URL}/api/briefing`,
  autonomy: `${API_BASE_URL}/api/autonomy`,
  macros: `${API_BASE_URL}/api/macros`,
  agents: `${API_BASE_URL}/api/agents`,
  learning: `${API_BASE_URL}/api/learning`,
  lifeMemory: `${API_BASE_URL}/api/life-memory`,
  dev: `${API_BASE_URL}/api/dev`,
  knowledge: `${API_BASE_URL}/api/knowledge`,
  timeline: `${API_BASE_URL}/api/timeline`,
  goals: `${API_BASE_URL}/api/goals`,
};

/**
 * Resolve a possibly-relative URL (e.g. `/temp_audio/x.mp3`) against the
 * configured API base, so audio works in dev (proxy) and production
 * (absolute VITE_API_URL) alike.
 */
export function resolveApiUrl(path) {
  if (!path) return path;
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE_URL}${path}`;
}
