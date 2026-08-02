import { useState, useEffect } from 'react';
import { Search, Plus, Zap, ExternalLink, X } from 'lucide-react';
import { getJobs, addJob, updateJobStatus, analyzeJob, createApplication } from '../../../api/careerApi.js';
import JobCard from '../components/JobCard.jsx';
import MatchScoreRing from '../components/MatchScoreRing.jsx';
import SkillTag from '../components/SkillTag.jsx';
import StatusBadge from '../components/StatusBadge.jsx';
import Skeleton from '../components/Skeleton.jsx';

const SOURCES  = ['All', 'LinkedIn', 'Wellfound', 'Naukri', 'Indeed', 'Manual'];
const STATUSES = ['All', 'new', 'bookmarked', 'approved', 'applied', 'ignored'];

export default function Opportunities() {
  const [jobs, setJobs]             = useState([]);
  const [loading, setLoading]       = useState(true);
  const [selected, setSelected]     = useState(null);
  const [source, setSource]         = useState('All');
  const [statusFilter, setStatus]   = useState('All');
  const [search, setSearch]         = useState('');
  const [minScore, setMinScore]     = useState(0);
  const [analyzing, setAnalyzing]   = useState(false);
  const [showAddJob, setShowAddJob] = useState(false);
  const [newJob, setNewJob]         = useState({ title: '', company: '', description: '', source: 'manual', location: '', url: '' });

  const loadJobs = () => {
    setLoading(true);
    getJobs({ status: statusFilter === 'All' ? null : statusFilter, min_score: minScore, source: source === 'All' ? null : source.toLowerCase() })
      .then(d => { setJobs(d.jobs || []); })
      .finally(() => setLoading(false));
  };

  useEffect(loadJobs, [source, statusFilter, minScore]);

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

  const handleApprove = async (job) => {
    await createApplication(job.id);
    await updateJobStatus(job.id, 'approved');
    loadJobs();
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

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* ── Left Panel: Job List ───────────────────────────────────────────── */}
      <div style={{ width: 360, borderRight: '1px solid rgba(255,255,255,0.05)', display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
        {/* Toolbar */}
        <div style={{ padding: '16px 16px 0', display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <div style={{ flex: 1, position: 'relative' }}>
              <Search size={13} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: '#475569' }} />
              <input value={search} onChange={e => setSearch(e.target.value)}
                placeholder="Search opportunities…" style={inputStyle({ paddingLeft: 32 })} />
            </div>
            <button onClick={() => setShowAddJob(true)} style={btnPrimary}>
              <Plus size={14} /> Add
            </button>
          </div>
          {/* Source tabs */}
          <div style={{ display: 'flex', gap: 4, overflowX: 'auto', paddingBottom: 4 }}>
            {SOURCES.map(s => (
              <button key={s} onClick={() => setSource(s)} style={{
                padding: '4px 10px', borderRadius: 6, border: 'none', fontSize: 12, cursor: 'pointer', whiteSpace: 'nowrap',
                background: source === s ? 'rgba(99,102,241,0.15)' : 'transparent',
                color: source === s ? '#818cf8' : '#475569', fontWeight: source === s ? 600 : 400,
              }}>{s}</button>
            ))}
          </div>
          {/* Status filter tabs */}
          <div style={{ display: 'flex', gap: 4, overflowX: 'auto', paddingBottom: 4 }}>
            {STATUSES.map(s => (
              <button key={s} onClick={() => setStatus(s)} style={{
                padding: '4px 10px', borderRadius: 6, border: 'none', fontSize: 11, cursor: 'pointer', whiteSpace: 'nowrap', textTransform: 'capitalize',
                background: statusFilter === s ? 'rgba(99,102,241,0.12)' : 'transparent',
                color: statusFilter === s ? '#a5b4fc' : '#334155', fontWeight: statusFilter === s ? 600 : 400,
              }}>{s}</button>
            ))}
          </div>
          {/* Score filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, paddingBottom: 8, borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
            <span style={{ fontSize: 11, color: '#475569', whiteSpace: 'nowrap' }}>Min score: {minScore}%</span>
            <input type="range" min={0} max={90} step={10} value={minScore} onChange={e => setMinScore(+e.target.value)} style={{ flex: 1, accentColor: '#6366f1' }} />
          </div>
        </div>

        {/* Job list */}
        <div style={{ flex: 1, overflow: 'auto', padding: '8px 8px' }}>
          {loading ? <Skeleton count={8} /> : filtered.length === 0 ? (
            <div style={{ padding: 24, textAlign: 'center', color: '#475569', fontSize: 13 }}>
              No opportunities found.<br />
              <button onClick={() => setShowAddJob(true)} style={{ ...btnPrimary, marginTop: 12 }}>
                <Plus size={13} /> Add manually
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
