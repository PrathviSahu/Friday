/**
 * resumeProfile.js — turn raw resume text into a lightweight structured profile.
 *
 * Deliberately heuristic (no ML dependency): good enough to drive job matching
 * and to seed the user's preference defaults. PDF/DOCX -> text extraction is the
 * caller's job (pdfjs-dist / mammoth); this module owns the analysis.
 */

// Curated skill lexicon — extend as needed. Blends tech + finance/trading
// since FRIDAY's user does both software and markets.
const SKILL_LEXICON = [
  // tech
  'javascript', 'typescript', 'react', 'vue', 'svelte', 'node', 'nodejs', 'python',
  'go', 'golang', 'rust', 'java', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin',
  'sql', 'postgres', 'postgresql', 'mysql', 'mongodb', 'redis', 'dynamodb',
  'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'ci/cd', 'graphql',
  'rest', 'microservices', 'machine learning', 'ml', 'ai', 'llm', 'tensorflow',
  'pytorch', 'pandas', 'numpy', 'spark', 'kafka', 'websocket', 'three.js', 'tauri',
  'electron', 'tailwind', 'django', 'flask', 'fastapi', 'spring', 'laravel',
  // finance / trading
  'trading', 'algorithmic trading', 'quant', 'quantitative', 'options', 'futures',
  'equities', 'forex', 'derivatives', 'zerodha', 'kite connect', 'technical analysis',
  'fundamental analysis', 'risk management', 'portfolio', 'bloomberg', 'screener',
];

const DEGREE_RE = /(b\.?tech|b\.?e\.?|b\.?sc|bachelor|m\.?tech|m\.?e\.?|m\.?sc|master|mba|phd|doctorate|diploma)/i;
const YEARS_RE = /(\d{1,2})\+?\s*years?/i;
const TITLE_RE = /(software engineer|full stack|frontend|backend|devops|data scientist|ml engineer|ai engineer|quant|trader|analyst|consultant|developer|engineer|architect|lead|manager|founder|cto|ceo)/i;

function uniqueSkillsFound(text) {
  const lower = ` ${text.toLowerCase()} `;
  return SKILL_LEXICON.filter((s) => lower.includes(s)).sort();
}

export function parseResume(text) {
  const lower = text.toLowerCase();
  const skills = uniqueSkillsFound(text);

  const yearsMatch = lower.match(YEARS_RE);
  const years = yearsMatch ? parseInt(yearsMatch[1], 10) : null;

  const titleMatch = text.match(TITLE_RE);
  const title = titleMatch ? titleMatch[0] : null;

  const education = DEGREE_RE.test(text);

  // crude location sniff — common Indian + global cities
  const CITIES = ['mumbai', 'delhi', 'bangalore', 'bengaluru', 'hyderabad', 'chennai',
    'pune', 'kolkata', 'gurgaon', 'gurugram', 'noida', 'ahmedabad', 'remote',
    'san francisco', 'new york', 'london', 'berlin', 'singapore', 'dubai'];
  const location = CITIES.find((c) => lower.includes(c)) || null;

  return {
    rawText: text,
    skills,
    years,
    title,
    education,
    location,
  };
}

/**
 * Seed default job preferences from a parsed profile so the user starts from a
 * sensible baseline instead of blanks.
 */
export function profileToPreferences(profile, overrides = {}) {
  return {
    roles: profile.title ? [profile.title] : ['software engineer'],
    locations: profile.location ? [profile.location] : ['remote'],
    remote: 'any',
    minSalary: 0,
    skills: profile.skills,
    seniority: profile.years != null
      ? (profile.years >= 8 ? 'senior' : profile.years >= 3 ? 'mid' : 'junior')
      : 'any',
    ...overrides,
  };
}
