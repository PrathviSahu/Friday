/**
 * config.js — Centralized API configuration for F.R.I.D.A.Y. frontend.
 *
 * Resolution order:
 *   1. VITE_API_BASE_URL  (recommended for production: absolute backend URL)
 *   2. VITE_API_URL       (legacy alias)
 *   3. relative '' — the Vite dev server / Docker nginx proxy /api and
 *      /temp_audio to the FastAPI backend, so relative URLs work in every
 *      hosted setup (localhost, LAN, preview, Docker).
 *
 * IMPORTANT: there is intentionally NO hardcoded backend URL fallback. A
 * previous version defaulted non-localhost hosts to a fixed Render URL
 * (https://friday-api-wy2b.onrender.com) which silently broke any deployment
 * whose backend lives at a different address. Set VITE_API_BASE_URL at build
 * time instead, e.g. `VITE_API_BASE_URL=https://your-backend.example.com npm run build`.
 */

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  ''
).replace(/\/$/, '');

// Runtime session token: stored in memory / sessionStorage ONLY when explicitly
// unlocked by the owner. The static public production build NEVER contains hardcoded master secrets.
export function getMasterSessionToken() {
  if (typeof window === 'undefined') return '';
  try {
    return (window.sessionStorage?.getItem('FRIDAY_SESSION_TOKEN') || '').trim();
  } catch (_) {
    return '';
  }
}

export function setMasterSessionToken(token) {
  if (typeof window === 'undefined') return;
  try {
    if (token) {
      window.sessionStorage?.setItem('FRIDAY_SESSION_TOKEN', token.trim());
    } else {
      window.sessionStorage?.removeItem('FRIDAY_SESSION_TOKEN');
    }
  } catch (_) {}
}

export const FRIDAY_TOKEN = getMasterSessionToken();

// Wrap window.fetch to dynamically attach X-FRIDAY-Token whenever an active master token exists
if (typeof window !== 'undefined' && !window.fetch.__fridayAuthWrapped) {
  const originalFetch = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const token = getMasterSessionToken();
    if (token) {
      const headers = new Headers(init && init.headers);
      if (!headers.has('X-FRIDAY-Token')) {
        headers.set('X-FRIDAY-Token', token);
      }
      return originalFetch(input, { ...init, headers });
    }
    return originalFetch(input, init);
  };
  window.fetch.__fridayAuthWrapped = true;
}

export const API_ENDPOINTS = {
  chatText: `${API_BASE_URL}/api/chat/text`,
  speechTranscribe: `${API_BASE_URL}/api/speech/transcribe`,
  tts: `${API_BASE_URL}/api/tts`,
  ttsStream: `${API_BASE_URL}/api/tts/stream`,
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
