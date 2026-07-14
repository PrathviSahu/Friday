/**
 * jobMatch.js — score a job against the user's profile + preferences.
 * Returns 0-100 plus human-readable reasons so FRIDAY can explain a match.
 */

function tokenize(s) {
  return (s || '').toLowerCase().split(/[^a-z0-9+#.]+/i).filter(Boolean);
}

function overlap(a, b) {
  const setB = new Set(b.map((x) => x.toLowerCase()));
  return a.filter((x) => setB.has(x.toLowerCase()));
}

function titleSimilarity(profileTitle, jobTitle) {
  if (!profileTitle || !jobTitle) return 0;
  const p = tokenize(profileTitle);
  const j = tokenize(jobTitle);
  if (!p.length || !j.length) return 0;
  return overlap(p, j).length / Math.max(p.length, j.length);
}

function locationMatches(prefLocations, prefRemote, jobLocation) {
  if (!jobLocation) return null; // unknown -> neutral
  const loc = jobLocation.toLowerCase();
  if (prefRemote === 'remote' && /remote|anywhere|work from home/.test(loc)) return true;
  if (prefRemote === 'onsite' && /remote/.test(loc)) return false;
  if (!prefLocations?.length) return null;
  return prefLocations.some((l) => loc.includes(l.toLowerCase()));
}

function parseSalary(text) {
  // crude: find "₹/Rs/$ <number> <lpa|k|per annum>" style
  const m = text.match(/(?:₹|rs\.?|\$)\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(lpa|k|lac|per annum)?/i);
  if (!m) return null;
  let n = parseFloat(m[1].replace(/,/g, ''));
  const unit = (m[2] || '').toLowerCase();
  if (unit === 'lpa' || unit === 'lac') n = n * 100000;
  else if (unit === 'k') n = n * 1000;
  return n;
}

export function scoreJob(job, { profile, preferences }) {
  const reasons = [];
  const warnings = [];
  let score = 0;

  // 1) Title similarity (up to 30)
  const tSim = titleSimilarity(profile?.title, job.title);
  const titlePts = Math.round(tSim * 30);
  score += titlePts;
  if (titlePts > 15) reasons.push(`Title aligns with your profile (${Math.round(tSim * 100)}% keyword match).`);
  else if (titlePts === 0) warnings.push('Title does not match your background.');

  // 2) Skills overlap (up to 35)
  const requiredSkills = tokenize(job.description)
    .filter((t) => profile?.skills?.includes(t));
  const matched = overlap(profile?.skills || [], tokenize(job.description));
  const skillPts = Math.min(35, matched.length * 7);
  score += skillPts;
  if (matched.length) reasons.push(`Matches ${matched.length} of your skills: ${matched.slice(0, 6).join(', ')}.`);
  else warnings.push('No skill overlap detected.');

  // 3) Location (up to 15)
  const loc = locationMatches(preferences?.locations, preferences?.remote, job.location);
  if (loc === true) { score += 15; reasons.push(`Location fits (${job.location}).`); }
  else if (loc === false) { warnings.push(`Location mismatch (${job.location}).`); }

  // 4) Salary (up to 15)
  const salary = parseSalary(job.description + ' ' + (job.salary || ''));
  if (salary != null) {
    if (salary >= (preferences?.minSalary || 0)) { score += 15; reasons.push(`Compensation meets your minimum.`); }
    else { warnings.push(`Below your minimum salary.`); }
  }

  // 5) Seniority (up to 5)
  if (preferences?.seniority && preferences.seniority !== 'any' && job.description) {
    const yrs = job.description.match(/(\d{1,2})\+?\s*years/i);
    if (yrs) {
      const need = parseInt(yrs[1], 10);
      const have = profile?.years ?? 0;
      if (have >= need - 1) { score += 5; reasons.push('Seniority requirement met.'); }
      else warnings.push(`Asks for ${need} yrs; you have ~${have}.`);
    }
  }

  score = Math.max(0, Math.min(100, score));
  return {
    score,
    matched: [...new Set([...matched, ...requiredSkills])],
    reasons,
    warnings,
    verdict: score >= 70 ? 'strong' : score >= 45 ? 'moderate' : 'weak',
  };
}

/**
 * Rank a list of jobs. `apply` is the user confirmation callback — FRIDAY only
 * auto-applies when the user explicitly says yes (per project guard rules).
 */
export function rankJobs(jobs, ctx) {
  return jobs
    .map((j) => ({ job: j, match: scoreJob(j, ctx) }))
    .sort((a, b) => b.match.score - a.match.score);
}
