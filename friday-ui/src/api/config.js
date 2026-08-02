/**
 * config.js — Centralized API configuration for F.R.I.D.A.Y. frontend.
 * Reads environment variable VITE_API_URL or defaults to local backend at http://localhost:8000.
 */

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const API_ENDPOINTS = {
  chatText: `${API_BASE_URL}/api/chat/text`,
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
};
