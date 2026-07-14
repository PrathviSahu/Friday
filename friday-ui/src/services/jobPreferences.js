/**
 * jobPreferences.js — persisted job-search preferences (non-secret).
 * Stored in localStorage; secrets (board API keys) live in the vault instead.
 */

const PREFS_KEY = 'friday_job_prefs_v1';

const DEFAULTS = {
  roles: ['software engineer'],
  locations: ['remote'],
  remote: 'any', // 'remote' | 'hybrid' | 'onsite' | 'any'
  minSalary: 0,
  skills: [],
  seniority: 'any', // 'junior' | 'mid' | 'senior' | 'any'
};

export function loadPreferences() {
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    return raw ? { ...DEFAULTS, ...JSON.parse(raw) } : { ...DEFAULTS };
  } catch {
    return { ...DEFAULTS };
  }
}

export function savePreferences(prefs) {
  localStorage.setItem(PREFS_KEY, JSON.stringify({ ...DEFAULTS, ...prefs }));
}

export function updatePreferences(patch) {
  const next = { ...loadPreferences(), ...patch };
  savePreferences(next);
  return next;
}
