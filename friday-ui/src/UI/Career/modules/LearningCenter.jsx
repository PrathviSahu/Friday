import { useState, useEffect } from 'react';
import { BookOpen } from 'lucide-react';
import { getSkillGap, getResumes } from '../../../api/careerApi.js';
import { SkeletonCard } from '../components/Skeleton.jsx';

export default function LearningCenter() {
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading]   = useState(true);
  const [resumes, setResumes]   = useState([]);
  const [resumeId, setResumeId] = useState(null);

  const load = (rid) => {
    setLoading(true);
    getSkillGap(rid).then(d => setAnalysis(d.analysis)).finally(() => setLoading(false));
  };

  useEffect(() => {
    getResumes().then(d => {
      const r = d.resumes || [];
      setResumes(r);
      const rec = r.find(x => x.is_recommended) || r[0];
      if (rec) { setResumeId(rec.id); load(rec.id); }
      else { setLoading(false); }
    });
  }, []);

  const priorityColor = (p) => p === 'high' ? '#ef4444' : p === 'medium' ? '#f59e0b' : '#64748b';

  return (
    <div style={{ padding: 32, maxWidth: 900 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28 }}>
        <div>
          <h2 style={{ margin: '0 0 6px', fontSize: 20, fontWeight: 700, color: '#f1f5f9', letterSpacing: '-0.02em' }}>Learning Center</h2>
          <p style={{ margin: 0, fontSize: 13, color: '#475569' }}>AI-powered skill gap analysis from your job market</p>
        </div>
        <select value={resumeId || ''} onChange={e => { setResumeId(+e.target.value); load(+e.target.value); }}
          style={{ padding: '8px 12px', borderRadius: 7, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: '#e2e8f0', fontSize: 13 }}>
          <option value="">Select resume…</option>
          {resumes.map(r => <option key={r.id} value={r.id}>{r.title}</option>)}
        </select>
      </div>

      {loading ? (
        <SkeletonCard lines={5} />
      ) : !analysis || (!analysis.skills_in_demand?.length && !analysis.missing_skills?.length) ? (
        <div style={{ textAlign: 'center', padding: '64px 0', color: '#475569' }}>
          <BookOpen size={40} style={{ margin: '0 auto 12px', display: 'block', strokeWidth: 1 }} />
          <p style={{ fontSize: 14 }}>Add job listings to get skill gap analysis.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Match score impact */}
          {(analysis.current_avg_match > 0 || analysis.potential_avg_match > 0) && (
            <div style={{ display: 'flex', gap: 12 }}>
              <ScoreCard label="Current Match Avg" value={`${analysis.current_avg_match}%`} color="#f59e0b" />
              <ScoreCard label="After Learning" value={`${analysis.potential_avg_match}%`} color="#22c55e" />
            </div>
          )}

          {/* Impact statement */}
          {analysis.impact && (
            <div style={{ padding: '14px 18px', borderRadius: 10, background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.15)', borderLeft: '3px solid #6366f1' }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: '#6366f1', textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: 6 }}>F.R.I.D.A.Y. Insight</span>
              <p style={{ margin: 0, fontSize: 13, color: '#cbd5e1', lineHeight: 1.7 }}>{analysis.impact}</p>
            </div>
          )}

          {/* Skills in demand */}
          {analysis.skills_in_demand?.length > 0 && (
            <Section title="Market Skills in Demand">
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {analysis.skills_in_demand.map(s => (
                  <span key={s.skill} style={{
                    display: 'inline-flex', alignItems: 'center', gap: 6, padding: '5px 12px',
                    borderRadius: 999, border: '1px solid rgba(255,255,255,0.08)',
                    background: 'rgba(255,255,255,0.03)', fontSize: 13, color: '#94a3b8',
                  }}>
                    {s.skill}
                    {s.frequency && <span style={{ fontSize: 11, color: '#475569' }}>{s.frequency}%</span>}
                  </span>
                ))}
              </div>
            </Section>
          )}

          {/* Missing skills */}
          {analysis.missing_skills?.length > 0 && (
            <Section title="Your Skill Gaps (Priority Order)">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {analysis.missing_skills.map((s, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderRadius: 8, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{ width: 6, height: 6, borderRadius: '50%', background: priorityColor(s.priority), flexShrink: 0 }} />
                      <span style={{ fontSize: 14, fontWeight: 600, color: '#e2e8f0' }}>{s.skill}</span>
                    </div>
                    <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                      {s.weeks_to_learn && (
                        <span style={{ fontSize: 12, color: '#475569' }}>{s.weeks_to_learn}w to learn</span>
                      )}
                      <span style={{ fontSize: 11, color: priorityColor(s.priority), fontWeight: 600, textTransform: 'capitalize' }}>{s.priority}</span>
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Learning roadmap */}
          {analysis.roadmap?.length > 0 && (
            <Section title="Learning Roadmap">
              {analysis.roadmap.map((step, i) => (
                <div key={i} style={{ display: 'flex', gap: 16, marginBottom: i < analysis.roadmap.length - 1 ? 20 : 0 }}>
                  <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 700, color: '#818cf8', flexShrink: 0 }}>
                    {i + 1}
                  </div>
                  <div>
                    <div style={{ fontSize: 12, color: '#6366f1', fontWeight: 600, marginBottom: 4 }}>{step.week}</div>
                    <div style={{ fontSize: 14, color: '#e2e8f0', fontWeight: 500, marginBottom: 6 }}>{step.focus}</div>
                    {step.resources?.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {step.resources.map((r, j) => (
                          <span key={j} style={{ fontSize: 11, color: '#64748b', padding: '2px 8px', borderRadius: 99, border: '1px solid rgba(255,255,255,0.06)', background: 'rgba(255,255,255,0.02)' }}>
                            {r}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </Section>
          )}
        </div>
      )}
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div style={{ padding: '20px 24px', borderRadius: 10, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
      <div style={{ fontSize: 11, fontWeight: 600, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 16 }}>{title}</div>
      {children}
    </div>
  );
}

function ScoreCard({ label, value, color }) {
  return (
    <div style={{ flex: 1, padding: '16px 20px', borderRadius: 10, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', textAlign: 'center' }}>
      <div style={{ fontSize: 11, color: '#475569', marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color }}>{value}</div>
    </div>
  );
}
