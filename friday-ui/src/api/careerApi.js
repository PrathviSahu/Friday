/**
 * careerApi.js — Career Intelligence Center: typed fetch client.
 * All requests go to http://localhost:8000/api/career/*
 */

import { API_ENDPOINTS } from './config.js';

const BASE = API_ENDPOINTS.career;

// ── Simple in-memory cache ────────────────────────────────────────────────────
const _cache = new Map();
const CACHE_TTL = 30_000; // 30 seconds

function cached(key, fetcher) {
  const hit = _cache.get(key);
  if (hit && Date.now() - hit.ts < CACHE_TTL) return Promise.resolve(hit.data);
  return fetcher().then((data) => {
    _cache.set(key, { data, ts: Date.now() });
    return data;
  });
}

function invalidate(...keys) {
  keys.forEach((k) => _cache.delete(k));
}

// ── Core fetch wrapper ────────────────────────────────────────────────────────
async function api(method, path, body = null) {
  try {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' },
    };
    if (body !== null) opts.body = JSON.stringify(body);
    const res = await fetch(`${BASE}${path}`, opts);
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`[Career API] ${method} ${path} → ${res.status}: ${err}`);
    }
    return await res.json();
  } catch (e) {
    console.warn(e);
    throw e;
  }
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
export const getDashboard = () =>
  cached('dashboard', () => api('GET', '/dashboard'));

// ── Preferences ───────────────────────────────────────────────────────────────
export const getPreferences = () =>
  cached('preferences', () => api('GET', '/preferences'));

export const updatePreferences = async (updates, source = 'user') => {
  const result = await api('PUT', '/preferences', { updates, source });
  invalidate('preferences', 'dashboard');
  return result;
};

export const learnFromText = async (text) => {
  const result = await api('POST', '/learn', { text });
  invalidate('preferences', 'dashboard');
  return result;
};

// ── Profile ───────────────────────────────────────────────────────────────────
export const getProfile = () =>
  cached('profile', () => api('GET', '/profile'));

export const updateProfile = async (fields) => {
  const result = await api('PUT', '/profile', { fields });
  invalidate('profile');
  return result;
};

// ── Resumes ───────────────────────────────────────────────────────────────────
export const getResumes = (includeArchived = false) =>
  cached(`resumes_${includeArchived}`, () =>
    api('GET', `/resumes?include_archived=${includeArchived}`)
  );

export const getResume = (id) => api('GET', `/resumes/${id}`);

export const createResume = async (title, content = {}) => {
  const result = await api('POST', '/resumes', { title, content });
  invalidate('resumes_false', 'resumes_true');
  return result;
};

export const uploadResume = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${BASE}/resumes/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error(`[Career API] Upload failed with status ${res.status}`);
  const result = await res.json();
  invalidate('resumes_false', 'resumes_true');
  return result;
};

export const updateResume = async (id, updates) => {
  const result = await api('PUT', `/resumes/${id}`, updates);
  invalidate('resumes_false', 'resumes_true', 'dashboard');
  return result;
};

export const duplicateResume = async (id) => {
  const result = await api('POST', `/resumes/${id}/duplicate`);
  invalidate('resumes_false', 'resumes_true');
  return result;
};

export const recommendResume = async (id) => {
  const result = await api('POST', `/resumes/${id}/recommend`);
  invalidate('resumes_false', 'resumes_true');
  return result;
};

export const deleteResume = async (id) => {
  let result;
  try {
    result = await api('DELETE', `/resumes/${id}`);
  } catch (_err) {
    result = await api('POST', `/resumes/${id}/delete`);
  }
  invalidate('resumes_false', 'resumes_true');
  return result;
};

// ── Jobs / Opportunities ──────────────────────────────────────────────────────
export const getJobs = (params = {}) => {
  const { status, min_score = 0, source } = params;
  const qs = new URLSearchParams();
  if (status) qs.set('status', status);
  if (min_score) qs.set('min_score', min_score);
  if (source) qs.set('source', source);
  const key = `jobs_${qs.toString()}`;
  return cached(key, () => api('GET', `/jobs?${qs.toString()}`));
};

export const fetchLinkedinJobs = (query = 'Java Software Engineer', location = 'India', expLevel = 'fresher') =>
  api('POST', `/jobs/fetch-linkedin?query=${encodeURIComponent(query)}&location=${encodeURIComponent(location)}&exp_level=${encodeURIComponent(expLevel)}`);

export const getJob = (id) => api('GET', `/jobs/${id}`);

export const addJob = async (data) => {
  const result = await api('POST', '/jobs', data);
  invalidate('jobs_', 'dashboard');
  return result;
};

export const updateJobStatus = async (id, status, notes = '') => {
  const result = await api('PUT', `/jobs/${id}`, { status, notes });
  invalidate('jobs_', 'dashboard');
  return result;
};

export const analyzeJob = async (job_id, resume_id = null) => {
  const result = await api('POST', '/jobs/analyze', { job_id, resume_id });
  invalidate('jobs_', 'dashboard');
  return result;
};

// ── Applications ──────────────────────────────────────────────────────────────
export const getApplications = (status = null) =>
  cached(`apps_${status || 'all'}`, () =>
    api('GET', `/applications${status ? `?status=${status}` : ''}`)
  );

export const createApplication = async (job_id, resume_id = null) => {
  const result = await api('POST', '/applications', { job_id, resume_id });
  invalidate('apps_', 'dashboard', 'jobs_');
  return result;
};

export const updateApplication = async (id, updates) => {
  const result = await api('PUT', `/applications/${id}`, updates);
  invalidate('apps_', 'dashboard');
  return result;
};

// ── Cover Letters ─────────────────────────────────────────────────────────────
export const generateCoverLetter = (job_id, resume_id = null, tone = 'professional') =>
  api('POST', '/cover-letter', { job_id, resume_id, tone });

export const getCoverLetters = (job_id = null) =>
  api('GET', `/cover-letters${job_id ? `?job_id=${job_id}` : ''}`);

export const verifyAccount = (platformKey) =>
  api('POST', `/accounts/verify/${platformKey}`);

export const connectAccountLiveBrowser = (platformKey) =>
  api('POST', `/accounts/connect/${platformKey}`);

export const getCandidateIntelligence = (resumeId) =>
  cached(`intelligence_${resumeId}`, () => api('GET', `/candidate-intelligence/${resumeId}`));

// ── Recruiters ────────────────────────────────────────────────────────────────
export const getRecruiters = () =>
  cached('recruiters', () => api('GET', '/recruiters'));

export const addRecruiter = async (data) => {
  const result = await api('POST', '/recruiters', data);
  invalidate('recruiters');
  return result;
};

export const updateRecruiter = async (id, updates) => {
  const result = await api('PUT', `/recruiters/${id}`, updates);
  invalidate('recruiters');
  return result;
};

// ── Interviews ────────────────────────────────────────────────────────────────
export const getInterviews = (upcomingOnly = false) =>
  cached(`interviews_${upcomingOnly}`, () =>
    api('GET', `/interviews?upcoming_only=${upcomingOnly}`)
  );

export const addInterview = async (data) => {
  const result = await api('POST', '/interviews', data);
  invalidate('interviews_false', 'interviews_true', 'dashboard');
  return result;
};

export const updateInterview = async (id, updates) => {
  const result = await api('PUT', `/interviews/${id}`, updates);
  invalidate('interviews_false', 'interviews_true', 'dashboard');
  return result;
};

export const generateInterviewQuestions = (job_id, resume_id = null) =>
  api('POST', '/interviews/questions', { job_id, resume_id });

// ── Companies ─────────────────────────────────────────────────────────────────
export const getCompanies = (blacklistedOnly = false) =>
  cached(`companies_${blacklistedOnly}`, () =>
    api('GET', `/companies?blacklisted_only=${blacklistedOnly}`)
  );

export const blacklistCompany = async (name, reason = 'User preference') => {
  const result = await api('POST', '/companies/blacklist', { name, reason });
  invalidate('companies_false', 'companies_true', 'preferences', 'dashboard');
  return result;
};

// ── Analytics ─────────────────────────────────────────────────────────────────
export const getAnalytics = () =>
  cached('analytics', () => api('GET', '/analytics'));

export const getSkillGap = (resume_id = null) =>
  api('GET', `/skill-gap${resume_id ? `?resume_id=${resume_id}` : ''}`);

// ── Activity ──────────────────────────────────────────────────────────────────
export const getActivity = (limit = 20) =>
  api('GET', `/activity?limit=${limit}`);

// ── Cache helpers ─────────────────────────────────────────────────────────────
export const clearCache = () => _cache.clear();
