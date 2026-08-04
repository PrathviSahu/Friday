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
