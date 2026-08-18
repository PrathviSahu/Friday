/**
 * safeStorage.js — Safe localStorage & sessionStorage wrappers.
 *
 * Prevents SecurityError or QuotaExceededError in hardened environments
 * (Safari Private Browsing, iOS WebKit incognito, iframe sandboxes).
 */

export function getLocalItem(key, defaultValue = null) {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return defaultValue;
    const val = window.localStorage.getItem(key);
    return val !== null ? val : defaultValue;
  } catch (_) {
    return defaultValue;
  }
}

export function setLocalItem(key, value) {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return false;
    window.localStorage.setItem(key, String(value));
    return true;
  } catch (_) {
    return false;
  }
}

export function removeLocalItem(key) {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return false;
    window.localStorage.removeItem(key);
    return true;
  } catch (_) {
    return false;
  }
}

export function getSessionItem(key, defaultValue = null) {
  try {
    if (typeof window === 'undefined' || !window.sessionStorage) return defaultValue;
    const val = window.sessionStorage.getItem(key);
    return val !== null ? val : defaultValue;
  } catch (_) {
    return defaultValue;
  }
}

export function setSessionItem(key, value) {
  try {
    if (typeof window === 'undefined' || !window.sessionStorage) return false;
    window.sessionStorage.setItem(key, String(value));
    return true;
  } catch (_) {
    return false;
  }
}

export function removeSessionItem(key) {
  try {
    if (typeof window === 'undefined' || !window.sessionStorage) return false;
    window.sessionStorage.removeItem(key);
    return true;
  } catch (_) {
    return false;
  }
}
