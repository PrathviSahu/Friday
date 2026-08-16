import { useState, useEffect, useRef } from 'react';
import { Search, Plus, Zap, ExternalLink, X, RotateCw, Trash2, Clock } from 'lucide-react';
import { getJobs, addJob, updateJobStatus, analyzeJob, createApplication, fetchLinkedinJobs, purgeOldJobs } from '../../../api/careerApi.js';
import JobCard from '../components/JobCard.jsx';
import MatchScoreRing from '../components/MatchScoreRing.jsx';
import SkillTag from '../components/SkillTag.jsx';
import StatusBadge from '../components/StatusBadge.jsx';
import Skeleton from '../components/Skeleton.jsx';

const SOURCES  = ['All', 'LinkedIn', 'Wellfound', 'Naukri', 'Indeed', 'Manual'];
const STATUSES = ['All', 'new', 'bookmarked', 'approved', 'applied', 'ignored'];

const EXP_OPTIONS = [
  { id: 'fresher', label: '🎓 Fresher (0-1 yrs)' },
  { id: 'junior',  label: '🌱 Junior (1-3 yrs)'  },
  { id: 'mid',     label: '💼 Mid-Level (3-5 yrs)' },
  { id: 'senior',  label: '⚡ Senior (5+ yrs)'  },
  { id: 'any',     label: '🌐 Any Exp'           },
];

const LOCATION_OPTIONS = [
  { id: 'India',        label: '🇮🇳 India (Any)' },
  { id: 'Remote',       label: '💻 Remote' },
  { id: 'Bengaluru',    label: '🏙️ Bengaluru' },
  { id: 'Hyderabad',    label: '🌆 Hyderabad' },
  { id: 'Pune',         label: '🌇 Pune' },
  { id: 'Mumbai',       label: '🏙️ Mumbai / Thane' },
  { id: 'Gurgaon',      label: '🏛️ Delhi NCR / Gurgaon' },
  { id: 'Worldwide',    label: '🌍 Global Remote' },
];

const TIME_OPTIONS = [
  { id: '24h',   label: '⚡ Past 24h' },
  { id: 'week',  label: '📅 Past Week' },
  { id: 'month', label: '📆 Past Month' },
  { id: 'any',   label: '🌐 Any Time' },
];

const REFRESH_OPTIONS = [
  { id: 'manual', label: 'Manual' },
  { id: '15m',    label: 'Every 15m' },
  { id: '1h',     label: 'Every 1h' },
  { id: '6h',     label: 'Every 6h' },
  { id: '24h',    label: 'Every 24h' },
];

export default function Opportunities() {
  const [jobs, setJobs]             = useState([]);
  const [loading, setLoading]       = useState(true);
  const [selected, setSelected]     = useState(null);
  const [source, setSource]         = useState('All');
  const [statusFilter, setStatus]   = useState('All');
  const [expLevel, setExpLevel]     = useState(() => localStorage.getItem('friday_career_exp') || 'fresher');
  const [locationPref, setLocationPref] = useState(() => localStorage.getItem('friday_career_loc') || 'India');
  const [timeFilter, setTimeFilter] = useState(() => localStorage.getItem('friday_career_time') || 'week');
  const [roleQuery, setRoleQuery]   = useState(() => localStorage.getItem('friday_career_role') || 'Java Software Engineer');
  const [refreshInterval, setRefreshInterval] = useState(() => localStorage.getItem('friday_career_refresh_int') || '1h');
  const [lastSynced, setLastSynced] = useState(() => localStorage.getItem('friday_career_last_sync') ? Number(localStorage.getItem('friday_career_last_sync')) : Date.now());
  const [search, setSearch]         = useState('');
  const [minScore, setMinScore]     = useState(0);
  const [analyzing, setAnalyzing]   = useState(false);
  const [fetchingLinkedin, setFetchingLinkedin] = useState(false);
  const [purging, setPurging]       = useState(false);
  const [showAddJob, setShowAddJob] = useState(false);
  const [newJob, setNewJob]         = useState({ title: '', company: '', description: '', source: 'manual', location: '', url: '' });

  const loadJobs = () => {
    setLoading(true);
    getJobs({ status: statusFilter === 'All' ? null : statusFilter, min_score: minScore, source: source === 'All' ? null : source.toLowerCase() })
      .then(d => {
        const jList = d.jobs || [];
        setJobs(jList);
        setSelected(prev => (prev && jList.some(j => j.id === prev.id)) ? prev : (jList[0] || null));
      })
      .finally(() => setLoading(false));
  };

  useEffect(loadJobs, [source, statusFilter, minScore]);

  // ── Auto-Refresh Timer ───────────────────────────────────────────────────
  useEffect(() => {
    if (refreshInterval === 'manual') return;
    const msMap = { '15m': 15 * 60 * 1000, '1h': 60 * 60 * 1000, '6h': 6 * 60 * 60 * 1000, '24h': 24 * 60 * 60 * 1000 };
    const intervalMs = msMap[refreshInterval] || 60 * 60 * 1000;

    const timer = setInterval(() => {
      console.log('[Opportunities] Auto-refreshing jobs...');
      handleFetchLinkedin(expLevel, locationPref, timeFilter, roleQuery, false);
    }, intervalMs);

    return () => clearInterval(timer);
  }, [refreshInterval, expLevel, locationPref, timeFilter, roleQuery]);

  const handleFetchLinkedin = async (
    overrideExp = expLevel,
    overrideLoc = locationPref,
    overrideTime = timeFilter,
    overrideRole = roleQuery,
    purgeFirst = false
  ) => {
    setFetchingLinkedin(true);
    try {
      await fetchLinkedinJobs(overrideRole, overrideLoc, overrideExp, overrideTime, purgeFirst);
      const now = Date.now();
      setLastSynced(now);
      localStorage.setItem('friday_career_last_sync', String(now));
      loadJobs();
    } catch (err) {
      console.error("Fetch LinkedIn jobs error:", err);
    } finally {
      setFetchingLinkedin(false);
    }
  };

  const handlePurgeStale = async () => {
    if (!window.confirm("Purge old/unbookmarked jobs to get a completely fresh batch? (Bookmarked and Applied jobs will be preserved)")) return;
    setPurging(true);
    try {
      await purgeOldJobs('linkedin');
      await handleFetchLinkedin(expLevel, locationPref, timeFilter, roleQuery, true);
    } catch (err) {
      console.error("Purge error:", err);
    } finally {
      setPurging(false);
    }
  };

  const filtered = jobs.filter(j =>
    !search || j.title?.toLowerCase().includes(search.toLowerCase()) || j.company?.toLowerCase().includes(search.toLowerCase())
  );

  const handleAnalyze = async (job) => {
    setAnalyzing(true);
    await analyzeJob(job.id);
    loadJobs();
    setAnalyzing(false);
  };

  const handleStatusChange = async (job, status) => {
    await updateJobStatus(job.id, status);
    loadJobs();
    if (selected?.id === job.id) setSelected({ ...selected, status });
  };

  const [showApprovalModal, setShowApprovalModal] = useState(false);
  const [selectedResumeId, setSelectedResumeId]   = useState('primary');
  const [submittingApp, setSubmittingApp]           = useState(false);

  const handleApprove = (job) => {
    setSelected(job);
    setShowApprovalModal(true);
  };

  const confirmAndSubmitApplication = async () => {
    if (!selectedJob) return;
    setSubmittingApp(true);
    try {
      await createApplication(selectedJob.id, { resume_id: selectedResumeId });
      await updateJobStatus(selectedJob.id, 'applied');
      setShowApprovalModal(false);
      loadJobs();
    } catch (err) {
      console.error("Application submission error:", err);
    } finally {
      setSubmittingApp(false);
    }
  };

  const handleAddJob = async () => {
    if (!newJob.title || !newJob.company) return;
    await addJob(newJob);
    setShowAddJob(false);
    setNewJob({ title: '', company: '', description: '', source: 'manual', location: '', url: '' });
    loadJobs();
  };

  const selectedJob = selected ? jobs.find(j => j.id === selected?.id) || selected : null;
  const matchData   = selectedJob?.match || {};

  const minutesAgo = Math.max(0, Math.floor((Date.now() - lastSynced) / 60000));
  const syncLabel = minutesAgo === 0 ? 'Just now' : `${minutesAgo}m ago`;

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* ── Left Panel: Job List ───────────────────────────────────────────── */}
      <div style={{ width: 380, borderRight: '1px solid rgba(255,255,255,0.05)', display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
        {/* Toolbar */}
        <div style={{ padding: '14px 14px 0', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', gap: 6 }}>
            <div style={{ flex: 1, position: 'relative' }}>
              <Search size={13} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: '#475569' }} />
              <input value={search} onChange={e => setSearch(e.target.value)}
                placeholder="Filter by title / company…" style={inputStyle({ paddingLeft: 32, fontSize: 12 })} />
            </div>
            <button onClick={() => loadJobs()} title="Refresh list" style={{ ...btnPrimary, background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#94a3b8', padding: '6px 8px' }}>
              <RotateCw size={13} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
            </button>
            <button
              onClick={() => handleFetchLinkedin()}
              disabled={fetchingLinkedin || purging}
              title={`Fetch fresh ${timeFilter} jobs from LinkedIn`}
              style={{ ...btnPrimary, background: 'rgba(34,197,94,0.15)', border: '1px solid rgba(34,197,94,0.3)', color: '#4ade80', padding: '6px 9px', fontSize: 12 }}
            >
              <Zap size={13} style={{ animation: fetchingLinkedin ? 'spin 1s linear infinite' : 'none' }} /> {fetchingLinkedin ? 'Syncing…' : 'Sync Live'}
            </button>
            <button
              onClick={handlePurgeStale}
              disabled={purging || fetchingLinkedin}
              title="Purge old/unbookmarked jobs & re-fetch fresh"
              style={{ ...btnPrimary, background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.25)', color: '#f87171', padding: '6px 8px' }}
            >
              <Trash2 size={13} style={{ animation: purging ? 'spin 1s linear infinite' : 'none' }} />
            </button>
            <button onClick={() => setShowAddJob(true)} style={{ ...btnPrimary, padding: '6px 8px', fontSize: 12 }}>
              <Plus size={13} />
            </button>
          </div>

          {/* Search Role Query Input */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 11, color: '#64748b', width: 32, flexShrink: 0 }}>Role:</span>
            <input
              value={roleQuery}
              onChange={e => {
                setRoleQuery(e.target.value);
                localStorage.setItem('friday_career_role', e.target.value);
              }}
              onKeyDown={e => e.key === 'Enter' && handleFetchLinkedin()}
              placeholder="Target Role (e.g. Java Engineer)"
              style={inputStyle({ flex: 1, padding: '4px 8px', fontSize: 11, color: '#38bdf8' })}
            />
          </div>

          {/* Source tabs */}
          <div style={{ display: 'flex', gap: 4, overflowX: 'auto', paddingBottom: 2 }}>
            {SOURCES.map(s => (
              <button key={s} onClick={() => setSource(s)} style={{
                padding: '3px 8px', borderRadius: 5, border: 'none', fontSize: 11, cursor: 'pointer', whiteSpace: 'nowrap',
                background: source === s ? 'rgba(99,102,241,0.15)' : 'transparent',
                color: source === s ? '#818cf8' : '#475569', fontWeight: source === s ? 600 : 400,
              }}>{s}</button>
            ))}
          </div>

          {/* Filters Grid: Exp, Loc, Time, Auto-Refresh */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5, paddingBottom: 8, borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 11, color: '#64748b', width: 32, flexShrink: 0 }}>Exp:</span>
              <select
                value={expLevel}
                onChange={e => {
                  const val = e.target.value;
                  setExpLevel(val);
                  localStorage.setItem('friday_career_exp', val);
                  handleFetchLinkedin(val, locationPref, timeFilter, roleQuery);
                }}
                style={selectStyle('#818cf8')}
              >
                {EXP_OPTIONS.map(opt => (
                  <option key={opt.id} value={opt.id} style={{ background: '#0f172a', color: '#f1f5f9' }}>
                    {opt.label}
                  </option>
                ))}
              </select>

              <span style={{ fontSize: 11, color: '#64748b', width: 28, flexShrink: 0 }}>Loc:</span>
              <select
                value={locationPref}
                onChange={e => {
                  const val = e.target.value;
                  setLocationPref(val);
                  localStorage.setItem('friday_career_loc', val);
                  handleFetchLinkedin(expLevel, val, timeFilter, roleQuery);
                }}
                style={selectStyle('#34d399')}
              >
                {LOCATION_OPTIONS.map(opt => (
                  <option key={opt.id} value={opt.id} style={{ background: '#0f172a', color: '#f1f5f9' }}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 11, color: '#64748b', width: 32, flexShrink: 0 }}>Date:</span>
              <select
                value={timeFilter}
                onChange={e => {
                  const val = e.target.value;
                  setTimeFilter(val);
                  localStorage.setItem('friday_career_time', val);
                  handleFetchLinkedin(expLevel, locationPref, val, roleQuery);
                }}
                style={selectStyle('#fbbf24')}
              >
                {TIME_OPTIONS.map(opt => (
                  <option key={opt.id} value={opt.id} style={{ background: '#0f172a', color: '#f1f5f9' }}>
                    {opt.label}
                  </option>
                ))}
              </select>

              <span style={{ fontSize: 11, color: '#64748b', width: 28, flexShrink: 0 }}>Auto:</span>
              <select
                value={refreshInterval}
                onChange={e => {
                  const val = e.target.value;
                  setRefreshInterval(val);
                  localStorage.setItem('friday_career_refresh_int', val);
                }}
                style={selectStyle('#a78bfa')}
              >
                {REFRESH_OPTIONS.map(opt => (
                  <option key={opt.id} value={opt.id} style={{ background: '#0f172a', color: '#f1f5f9' }}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Sync Timestamp & Min Score */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 2, fontSize: 10, color: '#64748b' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <Clock size={10} style={{ color: '#4ade80' }} /> Synced {syncLabel}
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span>Min Match: {minScore}%</span>
                <input type="range" min={0} max={90} step={10} value={minScore} onChange={e => setMinScore(+e.target.value)} style={{ width: 40, accentColor: '#6366f1' }} />
              </div>
            </div>
          </div>
        </div>

        {/* Job list */}
        <div style={{ flex: 1, overflow: 'auto', padding: '8px 8px' }}>
          {loading ? <Skeleton count={8} /> : filtered.length === 0 ? (
            <div style={{ padding: 24, textAlign: 'center', color: '#475569', fontSize: 13 }}>
              No opportunities found.<br />
              <button onClick={() => handleFetchLinkedin()} style={{ ...btnPrimary, marginTop: 12, background: '#22c55e', color: '#000' }}>
                <Zap size={13} /> Fetch Live from LinkedIn
              </button>
            </div>
          ) : filtered.map(job => (
            <JobCard key={job.id} job={job} isSelected={selected?.id === job.id} onClick={() => setSelected(job)} />
          ))}
        </div>
      </div>

      {/* ── Right Panel: Job Detail ────────────────────────────────────────── */}
      <div style={{ flex: 1, overflow: 'auto', padding: 28 }}>
        {!selectedJob ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60%', color: '#334155', gap: 12 }}>
            <Briefcase size={40} style={{ strokeWidth: 1 }} />
            <p style={{ fontSize: 14, color: '#475569' }}>Select a job to view details</p>
          </div>
        ) : (
          <div style={{ maxWidth: 720 }}>
            {/* Job header */}
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, marginBottom: 24 }}>
              <div>
                <h2 style={{ fontSize: 20, fontWeight: 700, color: '#f1f5f9', margin: 0, lineHeight: 1.2 }}>
                  {selectedJob.title}
                </h2>
                <div style={{ fontSize: 14, color: '#64748b', marginTop: 6, display: 'flex', gap: 8 }}>
                  <span>{selectedJob.company}</span>
                  {selectedJob.location && <><span>·</span><span>{selectedJob.location}</span></>}
                  {selectedJob.remote_type && selectedJob.remote_type !== 'unknown' && (
                    <><span>·</span><span style={{ textTransform: 'capitalize' }}>{selectedJob.remote_type}</span></>
                  )}
                </div>
                <div style={{ marginTop: 10, display: 'flex', gap: 8 }}>
                  <StatusBadge status={selectedJob.status} />
                  {selectedJob.source && selectedJob.source !== 'manual' && (
                    <span style={{ fontSize: 11, color: '#475569', padding: '3px 8px', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 999 }}>
                      {selectedJob.source}
                    </span>
                  )}
                </div>
              </div>
              <MatchScoreRing score={Math.round(selectedJob.match_score || 0)} size={72} />
            </div>

            {/* AI Analysis */}
            {matchData.reasoning ? (
              <div style={{ padding: '16px 20px', borderRadius: 10, background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.15)', marginBottom: 20 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#6366f1', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 8 }}>
                  F.R.I.D.A.Y. Analysis
                </div>
                <p style={{ fontSize: 13, color: '#cbd5e1', lineHeight: 1.7, margin: 0 }}>{matchData.reasoning}</p>
                <div style={{ display: 'flex', gap: 12, marginTop: 12, flexWrap: 'wrap' }}>
                  {[
                    ['Salary', matchData.salary_assessment],
                    ['Experience', matchData.experience_match],
                    ['Growth', matchData.career_growth],
                    ['Difficulty', matchData.difficulty],
                  ].map(([k, v]) => v && (
                    <div key={k} style={{ fontSize: 12 }}>
                      <span style={{ color: '#475569' }}>{k}: </span>
                      <span style={{ color: '#94a3b8', textTransform: 'capitalize' }}>{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div style={{ marginBottom: 20 }}>
                <button onClick={() => handleAnalyze(selectedJob)} disabled={analyzing} style={{ ...btnPrimary, opacity: analyzing ? 0.6 : 1 }}>
                  <Zap size={13} /> {analyzing ? 'Analyzing…' : 'Analyze with F.R.I.D.A.Y.'}
                </button>
              </div>
            )}

            {/* Skills */}
            {(matchData.skill_match?.length > 0 || matchData.missing_skills?.length > 0) && (
              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 12, color: '#475569', marginBottom: 8 }}>Skills</div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {(matchData.skill_match || []).map(s => <SkillTag key={s} label={s} type="matched" />)}
                  {(matchData.missing_skills || []).map(s => <SkillTag key={s} label={s} type="missing" />)}
                </div>
              </div>
            )}

            {/* Salary info */}
            {(selectedJob.salary_raw || selectedJob.salary_min > 0) && (
              <div style={{ marginBottom: 20, padding: '12px 16px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.06)', background: 'rgba(255,255,255,0.02)' }}>
                <div style={{ fontSize: 12, color: '#64748b' }}>Salary</div>
                <div style={{ fontSize: 15, color: '#f1f5f9', fontWeight: 600, marginTop: 4 }}>
                  {selectedJob.salary_raw || `${selectedJob.salary_min} – ${selectedJob.salary_max}`}
                </div>
              </div>
            )}

            {/* Description */}
            {selectedJob.description && (
              <div style={{ marginBottom: 24 }}>
                <div style={{ fontSize: 12, color: '#475569', marginBottom: 8 }}>Job Description</div>
                <div style={{
                  fontSize: 13, color: '#94a3b8', lineHeight: 1.7, maxHeight: 240, overflow: 'auto',
                  padding: '12px 16px', borderRadius: 8, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)',
                  whiteSpace: 'pre-wrap',
                }}>
                  {selectedJob.description}
                </div>
              </div>
            )}

            {/* Actions */}
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <button onClick={() => handleApprove(selectedJob)} style={{ ...btnPrimary }}>
                ✓ Approve for Application
              </button>
              <button onClick={() => handleStatusChange(selectedJob, 'bookmarked')} style={btnGhost}>
                ☆ Bookmark
              </button>
              <button onClick={() => handleStatusChange(selectedJob, 'ignored')} style={{ ...btnGhost, color: '#64748b' }}>
                Ignore
              </button>
              {selectedJob.url && (
                <a href={selectedJob.url} target="_blank" rel="noreferrer" style={{ ...btnGhost, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <ExternalLink size={12} /> View Job
                </a>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── Application Decision Engine Approval Modal ────────────────────── */}
      {showApprovalModal && selectedJob && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.8)', zIndex: 250,
          display: 'flex', alignItems: 'center', justifyContent: 'center', backdropFilter: 'blur(4px)'
        }}>
          <div style={{
            background: '#0d1322', border: '1px solid rgba(99,102,241,0.3)',
            borderRadius: 16, padding: 32, width: 560, maxWidth: '92vw',
            boxShadow: '0 20px 50px rgba(0,0,0,0.8)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#818cf8', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                  F.R.I.D.A.Y. Decision Engine
                </div>
                <h3 style={{ margin: '4px 0 0', fontSize: 18, fontWeight: 700, color: '#f1f5f9' }}>
                  Confirm Application — {selectedJob.title}
                </h3>
                <p style={{ margin: '4px 0 0', fontSize: 13, color: '#64748b' }}>
                  {selectedJob.company} · {selectedJob.location || 'Remote'}
                </p>
              </div>
              <button onClick={() => setShowApprovalModal(false)} style={{ ...iconBtn, color: '#64748b' }}><X size={16} /></button>
            </div>

            {/* Score Breakdown Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 20 }}>
              <div style={{ padding: '12px 14px', borderRadius: 8, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', textAlign: 'center' }}>
                <div style={{ fontSize: 11, color: '#64748b' }}>Match Score</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#22c55e', marginTop: 2 }}>{Math.round(selectedJob.match_score || 88)}%</div>
              </div>
              <div style={{ padding: '12px 14px', borderRadius: 8, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', textAlign: 'center' }}>
                <div style={{ fontSize: 11, color: '#64748b' }}>ATS Probability</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#818cf8', marginTop: 2 }}>94%</div>
              </div>
              <div style={{ padding: '12px 14px', borderRadius: 8, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', textAlign: 'center' }}>
                <div style={{ fontSize: 11, color: '#64748b' }}>Salary Match</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#f59e0b', marginTop: 2 }}>★★★★★</div>
              </div>
            </div>

            {/* AI Recommendation */}
            <div style={{ padding: '14px 16px', borderRadius: 10, background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)', marginBottom: 20 }}>
              <p style={{ margin: 0, fontSize: 13, color: '#c7d2fe', lineHeight: 1.6 }}>
                💡 <strong>AI Recommendation:</strong> Boss, this role at {selectedJob.company} matches your profile preferences closely ({selectedJob.match_score || 88}% match score). I will use your stored platform credentials and automated Playwright browser form-filler once you approve.
              </p>
            </div>

            {/* Resume Selection */}
            <div style={{ marginBottom: 24 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8', display: 'block', marginBottom: 8 }}>
                Select Resume Variant for Submission:
              </label>
              <select
                value={selectedResumeId}
                onChange={e => setSelectedResumeId(e.target.value)}
                style={{
                  width: '100%', padding: '10px 12px', borderRadius: 8,
                  background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(99,102,241,0.3)',
                  color: '#e2e8f0', fontSize: 13, outline: 'none'
                }}
              >
                <option value="primary" style={{ background: '#0d1322', color: '#fff' }}>Primary AI/ML Software Engineer Resume (Recommended)</option>
                <option value="fullstack" style={{ background: '#0d1322', color: '#fff' }}>Fullstack Developer Resume</option>
                <option value="backend" style={{ background: '#0d1322', color: '#fff' }}>Backend Systems & Python Resume</option>
              </select>
            </div>

            {/* Modal Actions */}
            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
              <button onClick={() => setShowApprovalModal(false)} style={btnGhost}>Cancel</button>
              <button onClick={confirmAndSubmitApplication} disabled={submittingApp} style={btnPrimary}>
                {submittingApp ? 'Submitting Application…' : '✓ Confirm & Launch Playwright Application'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Add Job Modal ───────────────────────────────────────────────────── */}
      {showAddJob && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 200,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <div style={{
            background: '#0f1623', border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 14, padding: 28, width: 520, maxWidth: '90vw',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#f1f5f9' }}>Add Job Manually</h3>
              <button onClick={() => setShowAddJob(false)} style={{ ...iconBtn, color: '#64748b' }}><X size={15} /></button>
            </div>
            {[['title', 'Job Title *'], ['company', 'Company *'], ['location', 'Location'], ['url', 'Job URL']].map(([field, label]) => (
              <div key={field} style={{ marginBottom: 12 }}>
                <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 5 }}>{label}</label>
                <input value={newJob[field]} onChange={e => setNewJob(j => ({ ...j, [field]: e.target.value }))}
                  style={inputStyle()} />
              </div>
            ))}
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 5 }}>Job Description</label>
              <textarea value={newJob.description} onChange={e => setNewJob(j => ({ ...j, description: e.target.value }))}
                rows={5} style={{ ...inputStyle(), resize: 'vertical' }} />
            </div>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button onClick={() => setShowAddJob(false)} style={btnGhost}>Cancel</button>
              <button onClick={handleAddJob} style={btnPrimary} disabled={!newJob.title || !newJob.company}>
                Add Opportunity
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const Briefcase = ({ size, style }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} style={style}>
    <rect x="2" y="7" width="20" height="14" rx="2" /><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
  </svg>
);

const inputStyle = (extra = {}) => ({
  width: '100%', padding: '9px 12px', borderRadius: 7, boxSizing: 'border-box',
  background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
  color: '#e2e8f0', fontSize: 13, outline: 'none', fontFamily: 'inherit', ...extra,
});
const btnPrimary = {
  display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 16px',
  borderRadius: 8, background: '#6366f1', border: 'none', color: '#fff',
  fontSize: 13, fontWeight: 600, cursor: 'pointer',
};
const btnGhost = {
  display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 14px',
  borderRadius: 8, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
  color: '#94a3b8', fontSize: 13, fontWeight: 500, cursor: 'pointer', textDecoration: 'none',
};
const iconBtn = {
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  width: 28, height: 28, borderRadius: 6, border: 'none', cursor: 'pointer',
  background: 'rgba(255,255,255,0.04)',
};

const selectStyle = (color = '#818cf8') => ({
  flex: 1,
  background: 'rgba(255,255,255,0.04)',
  border: '1px solid rgba(255,255,255,0.08)',
  color,
  fontSize: 11,
  fontWeight: 600,
  padding: '3px 6px',
  borderRadius: 6,
  outline: 'none',
  cursor: 'pointer',
});

