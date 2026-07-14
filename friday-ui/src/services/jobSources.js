/**
 * jobSources.js — job-board adapters + aggregator.
 *
 * Sources: mock (always works, for dev/demo) + Indeed / Naukri / LinkedIn /
 * Wellfound. Real boards need API keys (stored in the vault) and have ToS
 * constraints, so each adapter returns { configured, jobs, note }. When a key
 * isn't present the adapter reports unconfigured instead of failing loud.
 *
 * FRIDAY NEVER auto-applies — the orchestrator only applies on explicit user
 * confirmation (see memory: friday-security-trading-guards).
 */

// ── Mock source: realistic jobs so the pipeline works without external APIs ──
const MOCK_JOBS = [
  {
    id: 'mock-1', source: 'mock', title: 'Senior Frontend Engineer', company: 'Stark Labs',
    location: 'Bangalore / Remote', salary: '₹28 LPA',
    description: 'We need a senior frontend engineer with React, TypeScript, Three.js and 6+ years building polished UIs. Remote friendly.',
    url: 'https://example.com/job/1',
  },
  {
    id: 'mock-2', source: 'mock', title: 'Quantitative Trader', company: 'Roxxon Capital',
    location: 'Mumbai', salary: '₹45 LPA',
    description: 'Seeking a quant trader with Python, algorithmic trading, options and 4+ years. Strong risk management required.',
    url: 'https://example.com/job/2',
  },
  {
    id: 'mock-3', source: 'mock', title: 'Full Stack Developer', company: 'Pym Technologies',
    location: 'Hyderabad', salary: '₹18 LPA',
    description: 'Full stack developer with Node, React, Postgres and 2+ years. REST APIs and microservices.',
    url: 'https://example.com/job/3',
  },
  {
    id: 'mock-4', source: 'mock', title: 'AI Engineer', company: 'Stark Labs',
    location: 'Remote', salary: '₹32 LPA',
    description: 'AI engineer with Python, PyTorch, LLM fine-tuning and 5+ years building ML systems. Remote.',
    url: 'https://example.com/job/4',
  },
];

const mockSource = {
  id: 'mock',
  label: 'Mock Board',
  async fetchJobs(query) {
    const q = (query || '').toLowerCase();
    const jobs = q
      ? MOCK_JOBS.filter((j) => (j.title + j.description + j.company).toLowerCase().includes(q))
      : MOCK_JOBS;
    return { configured: true, jobs, note: 'Local mock data.' };
  },
};

// Generic adapter factory for real boards. Reads an API key from the vault
// (passed in by the orchestrator) and, if present, would call the board's API.
// The actual HTTP calls are left as TODOs to avoid shipping unvetted scraping.
function makeBoardAdapter({ id, label, keyName }) {
  return {
    id,
    label,
    async fetchJobs(_query, { apiKey } = {}) {
      if (!apiKey) {
        return {
          configured: false,
          jobs: [],
          note: `No ${label} API key in vault. Add "${keyName}" to enable.`,
        };
      }
      // TODO: implement the real board API call here. Respect each board's ToS
      // (LinkedIn/Naukri prohibit automated apply — use for discovery only).
      return { configured: true, jobs: [], note: `${label} adapter ready (API call not yet implemented).` };
    },
  };
}

export const SOURCES = {
  mock: mockSource,
  indeed: makeBoardAdapter({ id: 'indeed', label: 'Indeed', keyName: 'indeed_api_key' }),
  naukri: makeBoardAdapter({ id: 'naukri', label: 'Naukri', keyName: 'naukri_api_key' }),
  linkedin: makeBoardAdapter({ id: 'linkedin', label: 'LinkedIn', keyName: 'linkedin_api_key' }),
  wellfound: makeBoardAdapter({ id: 'wellfound', label: 'Wellfound', keyName: 'wellfound_api_key' }),
};

/**
 * Fetch from all requested sources. `keys` maps sourceId -> apiKey (from vault).
 * Returns aggregated jobs + per-source status so the UI can show what's live.
 */
export async function fetchAllJobs(query, { sources = ['mock'], keys = {} } = {}) {
  const results = await Promise.all(
    sources.map(async (sid) => {
      const src = SOURCES[sid] || mockSource;
      const res = await src.fetchJobs(query, { apiKey: keys[sid] });
      return { source: sid, ...res };
    }),
  );
  const jobs = results.flatMap((r) => r.jobs || []);
  const seen = new Set();
  const deduped = jobs.filter((j) => {
    const k = j.id || j.url;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
  return { jobs: deduped, sources: results };
}
