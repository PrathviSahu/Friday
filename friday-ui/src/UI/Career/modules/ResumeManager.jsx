import { useState, useEffect, useRef } from 'react';
import { Plus, Upload, Copy, Archive, Star, Trash2 } from 'lucide-react';
import { getResumes, createResume, uploadResume, updateResume, duplicateResume, recommendResume, deleteResume } from '../../../api/careerApi.js';
import Skeleton from '../components/Skeleton.jsx';

const SECTION_META = [
  { id: 'summary',        label: 'Professional Summary', icon: '📝', desc: 'Contact details, profile summary, and executive intro' },
  { id: 'skills',         label: 'Technical Skills',     icon: '⚡', desc: 'Languages, frameworks, databases, tools, and platforms' },
  { id: 'experience',     label: 'Work Experience',      icon: '💼', desc: 'Work history, job titles, companies, dates, and achievements' },
  { id: 'education',      label: 'Education',            icon: '🎓', desc: 'Degrees, colleges, graduation year, and GPA' },
  { id: 'projects',       label: 'Projects',             icon: '🚀', desc: 'Key projects, technical stack, architecture, and URLs' },
  { id: 'achievements',   label: 'Achievements',         icon: '🏆', desc: 'Awards, honors, hackathon wins, and competitive rankings' },
  { id: 'certifications', label: 'Certifications',       icon: '📜', desc: 'Professional certifications, credentials, and licenses' },
];

export default function ResumeManager() {
  const [resumes, setResumes]   = useState([]);
  const [loading, setLoading]   = useState(true);
  const [selected, setSelected] = useState(null);
  const [editing, setEditing]   = useState(null); // { section, content }
  const [saving, setSaving]     = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const load = (selectId = null) => {
    getResumes().then(d => {
      const r = d.resumes || [];
      setResumes(r);
      if (selectId) {
        const found = r.find(item => item.id === selectId);
        if (found) setSelected(found);
      } else if (!selected && r.length) {
        setSelected(r[0]);
      }
    }).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const getContent = (resume) => { try { return JSON.parse(resume?.content_json || '{}'); } catch { return {}; } };

  const handleCreate = async () => {
    const defaultTemplate = {
      summary: "Prathvi Sahu | Full-Stack & AI Software Engineer\nprathvisahu31@gmail.com | Mumbai, India",
      skills: "Java, Python, JavaScript, Spring Boot, FastAPI, React.js, MySQL, Redis, Docker, Git",
      experience: "Software Developer Trainee — ZDL Pvt. Ltd. (Zepto Digital Labs)\n• Designed and built high-performance microservices and AI integrations.",
      education: "Bachelor of Engineering in Computer Science and Design\nNew Horizon Institute of Technology and Management (2022 - 2026)",
      projects: "F.R.I.D.A.Y. Desktop AI System\n• Built multi-agent AI assistant with voice control, Career OS, and live trading workstation.",
      achievements: "• 1st Place — College Tech Innovation Hackathon (2025)\n• Top 5% Rank in Competitive Coding",
      certifications: "• AWS Certified Solutions Architect Associate (In Progress)\n• Oracle Certified Professional Java SE"
    };
    const res = await createResume(`Resume ${resumes.length + 1}`, defaultTemplate);
    load(res?.resume_id);
  };

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const res = await uploadResume(file);
      if (res?.resume_id) {
        load(res.resume_id);
      } else {
        load();
      }
    } catch (err) {
      console.error("Resume upload error:", err);
      alert("Failed to upload resume. Please try a .pdf, .docx, or .txt file.");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDuplicate = async (id) => {
    await duplicateResume(id);
    load();
  };

  const handleArchive = async (id) => {
    await updateResume(id, { is_archived: 1 });
    setSelected(null);
    load();
  };

  const handleDeleteResume = async (id, title, e) => {
    if (e) e.stopPropagation();
    if (window.confirm(`Are you sure you want to permanently delete '${title}'? This action cannot be undone.`)) {
      setResumes(prev => prev.filter(r => r.id !== id));
      if (selected?.id === id) setSelected(null);
      try {
        await deleteResume(id);
      } catch (err) {
        console.error("Delete resume error:", err);
      } finally {
        load();
      }
    }
  };

  const handleRecommend = async (id) => {
    await recommendResume(id);
    load();
  };

  const handleSaveSection = async (section, value) => {
    if (!selected) return;
    setSaving(true);
    const content = getContent(selected);
    content[section] = value;
    await updateResume(selected.id, { content_json: content });
    setEditing(null);
    setSaving(false);
    load();
  };

  const [viewTab, setViewTab]     = useState('sections'); // 'sections' | 'intelligence'
  const [intelData, setIntelData] = useState(null);
  const [loadingIntel, setLoadingIntel] = useState(false);

  useEffect(() => {
    if (selected && viewTab === 'intelligence') {
      setLoadingIntel(true);
      getCandidateIntelligence(selected.id)
        .then(d => setIntelData(d.intelligence || {}))
        .catch(err => console.warn("Intel load notice:", err))
        .finally(() => setLoadingIntel(false));
    }
  }, [selected, viewTab]);

  const selectedContent = selected ? getContent(selected) : {};

  if (loading) return <div style={{ padding: 32 }}><Skeleton count={5} /></div>;

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* ── Resume List ──────────────────────────────────────────────────────── */}
      <div style={{ width: 280, borderRight: '1px solid rgba(255,255,255,0.05)', padding: '20px 12px', overflow: 'auto', flexShrink: 0 }}>
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept=".pdf,.docx,.txt,.md,.json"
          style={{ display: 'none' }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, paddingLeft: 4 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: '#94a3b8' }}>Resumes ({resumes.length})</span>
          <div style={{ display: 'flex', gap: 6 }}>
            <button onClick={() => fileInputRef.current?.click()} disabled={uploading} style={btnSecondary} title="Upload PDF/Word/Text Resume">
              <Upload size={13} /> {uploading ? 'Uploading...' : 'Upload'}
            </button>
            <button onClick={handleCreate} style={btnPrimary}>
              <Plus size={13} /> New
            </button>
          </div>
        </div>
        {resumes.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#475569', fontSize: 13, padding: '32px 0' }}>
            No resumes yet.<br />Create your first one above.
          </div>
        ) : resumes.map(r => (
          <div key={r.id} onClick={() => setSelected(r)} style={{
            padding: '12px 14px', borderRadius: 8, cursor: 'pointer', marginBottom: 4,
            background: selected?.id === r.id ? 'rgba(99,102,241,0.08)' : 'transparent',
            border: selected?.id === r.id ? '1px solid rgba(99,102,241,0.2)' : '1px solid transparent',
            transition: 'all 150ms',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0' }}>{r.title}</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                {r.is_recommended ? <Star size={12} style={{ color: '#f59e0b', fill: '#f59e0b' }} /> : null}
                <button
                  onClick={(e) => handleDeleteResume(r.id, r.title, e)}
                  title="Delete Resume"
                  style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', padding: 2 }}
                  onMouseEnter={e => e.currentTarget.style.color = '#ef4444'}
                  onMouseLeave={e => e.currentTarget.style.color = '#64748b'}
                >
                  <Trash2 size={12} />
                </button>
              </div>
            </div>
            {r.ats_score > 0 && (
              <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{ flex: 1, height: 3, borderRadius: 99, background: 'rgba(255,255,255,0.08)' }}>
                  <div style={{ width: `${r.ats_score}%`, height: '100%', borderRadius: 99, background: '#22c55e' }} />
                </div>
                <span style={{ fontSize: 11, color: '#64748b' }}>ATS {Math.round(r.ats_score)}%</span>
              </div>
            )}
            <div style={{ fontSize: 11, color: '#334155', marginTop: 4 }}>
              Updated {new Date(r.updated_at).toLocaleDateString()}
            </div>
          </div>
        ))}
      </div>

      {/* ── Resume Editor / Candidate Intelligence View ──────────────────────── */}
      <div style={{ flex: 1, overflow: 'auto', padding: 28 }}>
        {!selected ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60%', color: '#334155', gap: 12 }}>
            <span style={{ fontSize: 36 }}>📄</span>
            <p style={{ fontSize: 14, color: '#475569' }}>Select a resume to edit</p>
          </div>
        ) : (
          <>
            {/* Resume header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
              <div>
                <h2 style={{ fontSize: 20, fontWeight: 700, color: '#f1f5f9', margin: 0 }}>{selected.title}</h2>
                <p style={{ fontSize: 13, color: '#475569', margin: '6px 0 0' }}>
                  Version {selected.version} · Updated {new Date(selected.updated_at).toLocaleDateString()}
                </p>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={() => handleRecommend(selected.id)} style={btnGhost} title="Mark as recommended">
                  <Star size={14} style={{ color: selected.is_recommended ? '#f59e0b' : undefined }} />
                </button>
                <button onClick={() => handleDuplicate(selected.id)} style={btnGhost}>
                  <Copy size={14} /> Copy
                </button>
                <button onClick={() => handleArchive(selected.id)} style={btnGhost}>
                  <Archive size={14} /> Archive
                </button>
                <button onClick={() => handleDeleteResume(selected.id, selected.title)} style={{ ...btnGhost, color: '#ef4444', borderColor: 'rgba(239,68,68,0.3)', background: 'rgba(239,68,68,0.08)' }}>
                  <Trash2 size={14} /> Delete
                </button>
              </div>
            </div>

            {/* Mode Switcher Tabs: Resume Sections vs Candidate Intelligence */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 24, borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: 12 }}>
              <button
                onClick={() => setViewTab('sections')}
                style={{
                  padding: '7px 16px', borderRadius: 8, border: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer',
                  background: viewTab === 'sections' ? 'rgba(99,102,241,0.15)' : 'transparent',
                  color: viewTab === 'sections' ? '#818cf8' : '#64748b'
                }}
              >
                📄 Resume Content & Sections
              </button>
              <button
                onClick={() => setViewTab('intelligence')}
                style={{
                  padding: '7px 16px', borderRadius: 8, border: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer',
                  background: viewTab === 'intelligence' ? 'rgba(99,102,241,0.15)' : 'transparent',
                  color: viewTab === 'intelligence' ? '#818cf8' : '#64748b'
                }}
              >
                🧠 Candidate Intelligence Engine
              </button>
            </div>

            {/* View 1: Candidate Intelligence Dashboard */}
            {viewTab === 'intelligence' ? (
              <div>
                {loadingIntel ? <Skeleton count={4} /> : (
                  <div>
                    {/* SWOT Grid */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 14, marginBottom: 24 }}>
                      <div style={{ padding: 18, borderRadius: 12, background: 'rgba(34,197,94,0.05)', border: '1px solid rgba(34,197,94,0.2)' }}>
                        <div style={{ fontSize: 12, fontWeight: 700, color: '#22c55e', textTransform: 'uppercase', marginBottom: 10 }}>💪 Strengths</div>
                        <ul style={{ margin: 0, paddingLeft: 16, color: '#e2e8f0', fontSize: 13, lineHeight: 1.6 }}>
                          {(intelData?.swot?.strengths || ["Solid technical foundation"]).map((s, i) => <li key={i}>{s}</li>)}
                        </ul>
                      </div>
                      <div style={{ padding: 18, borderRadius: 12, background: 'rgba(245,158,11,0.05)', border: '1px solid rgba(245,158,11,0.2)' }}>
                        <div style={{ fontSize: 12, fontWeight: 700, color: '#f59e0b', textTransform: 'uppercase', marginBottom: 10 }}>⚠️ Weaknesses</div>
                        <ul style={{ margin: 0, paddingLeft: 16, color: '#e2e8f0', fontSize: 13, lineHeight: 1.6 }}>
                          {(intelData?.swot?.weaknesses || ["Add production metrics"]).map((s, i) => <li key={i}>{s}</li>)}
                        </ul>
                      </div>
                      <div style={{ padding: 18, borderRadius: 12, background: 'rgba(99,102,241,0.05)', border: '1px solid rgba(99,102,241,0.2)' }}>
                        <div style={{ fontSize: 12, fontWeight: 700, color: '#818cf8', textTransform: 'uppercase', marginBottom: 10 }}>🚀 Opportunities</div>
                        <ul style={{ margin: 0, paddingLeft: 16, color: '#e2e8f0', fontSize: 13, lineHeight: 1.6 }}>
                          {(intelData?.swot?.opportunities || ["AWS Certification"]).map((s, i) => <li key={i}>{s}</li>)}
                        </ul>
                      </div>
                      <div style={{ padding: 18, borderRadius: 12, background: 'rgba(239,68,68,0.05)', border: '1px solid rgba(239,68,68,0.2)' }}>
                        <div style={{ fontSize: 12, fontWeight: 700, color: '#f87171', textTransform: 'uppercase', marginBottom: 10 }}>🛑 Risks</div>
                        <ul style={{ margin: 0, paddingLeft: 16, color: '#e2e8f0', fontSize: 13, lineHeight: 1.6 }}>
                          {(intelData?.swot?.risks || ["Missing quantified outcomes"]).map((s, i) => <li key={i}>{s}</li>)}
                        </ul>
                      </div>
                    </div>

                    {/* Skill Gap Roadmap */}
                    <div style={{ padding: 20, borderRadius: 12, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', marginBottom: 24 }}>
                      <div style={{ fontSize: 14, fontWeight: 700, color: '#f1f5f9', marginBottom: 6 }}>
                        🎯 Skill Gap Roadmap — {intelData?.skill_gap?.target_role || "Java & AI Backend Developer"}
                      </div>
                      <div style={{ display: 'flex', gap: 20, marginTop: 12 }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: 12, color: '#22c55e', fontWeight: 600, marginBottom: 8 }}>✅ Already Have</div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                            {(intelData?.skill_gap?.already_have || ["Java", "Python", "React"]).map(s => (
                              <span key={s} style={{ padding: '4px 10px', borderRadius: 6, background: 'rgba(34,197,94,0.1)', color: '#4ade80', fontSize: 12 }}>{s}</span>
                            ))}
                          </div>
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: 12, color: '#f87171', fontWeight: 600, marginBottom: 8 }}>⚡ Recommended to Learn</div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                            {(intelData?.skill_gap?.needed || ["Docker", "Redis", "Kafka"]).map(s => (
                              <span key={s} style={{ padding: '4px 10px', borderRadius: 6, background: 'rgba(239,68,68,0.1)', color: '#f87171', fontSize: 12 }}>{s}</span>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : null}

            {/* View 2: Sections List */}
            {viewTab === 'sections' && SECTION_META.map(meta => {
              const section = meta.id;
              const isEditing = editing?.section === section;
              const value = selectedContent[section] || '';
              return (
                <div key={section} style={{ marginBottom: 20, borderRadius: 12, border: '1px solid rgba(255,255,255,0.06)', background: 'rgba(15,23,42,0.4)', overflow: 'hidden' }}>
                  <div style={{
                    padding: '12px 18px', background: 'rgba(255,255,255,0.02)',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    borderBottom: isEditing || value ? '1px solid rgba(255,255,255,0.06)' : 'none',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{ fontSize: 16 }}>{meta.icon}</span>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 700, color: '#f1f5f9' }}>{meta.label}</div>
                        <div style={{ fontSize: 11, color: '#64748b' }}>{meta.desc}</div>
                      </div>
                    </div>
                    <button
                      onClick={() => setEditing(isEditing ? null : { section, content: value })}
                      style={{
                        ...btnGhost,
                        borderColor: !value ? 'rgba(99,102,241,0.3)' : undefined,
                        color: !value ? '#818cf8' : undefined,
                        background: !value ? 'rgba(99,102,241,0.1)' : undefined,
                      }}
                    >
                      {isEditing ? 'Cancel' : !value ? `+ Add ${meta.label}` : 'Edit'}
                    </button>
                  </div>
                  {isEditing ? (
                    <div style={{ padding: 16 }}>
                      <textarea
                        value={editing.content}
                        onChange={e => setEditing(ed => ({ ...ed, content: e.target.value }))}
                        rows={section === 'experience' || section === 'projects' ? 8 : 4}
                        placeholder={`Enter details for ${meta.label}…`}
                        style={{
                          width: '100%', padding: '10px 12px', borderRadius: 7, boxSizing: 'border-box',
                          background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
                          color: '#e2e8f0', fontSize: 13, fontFamily: 'monospace', resize: 'vertical',
                        }} />
                      <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                        <button onClick={() => handleSaveSection(section, editing.content)} disabled={saving} style={btnPrimary}>
                          {saving ? 'Saving…' : 'Save Section'}
                        </button>
                        <button onClick={() => setEditing(null)} style={btnGhost}>Cancel</button>
                      </div>
                    </div>
                  ) : (
                    <div style={{ padding: '14px 18px' }}>
                      {value ? renderFormattedSection(section, value) : (
                        <p style={{ margin: 0, fontSize: 12, color: '#475569', fontStyle: 'italic' }}>
                          No {meta.label.toLowerCase()} added yet. Click <strong>+ Add {meta.label}</strong> above.
                        </p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </>
        )}
      </div>
    </div>
  );
}
const renderFormattedSection = (section, value) => {
  if (!value) return null;
  const strValue = typeof value === 'string' ? value : JSON.stringify(value, null, 2);

  // 1. Tag Pills for Skills / Languages / Certifications
  if (['skills', 'languages', 'certifications'].includes(section.toLowerCase())) {
    const tags = strValue
      .split(/[,;\n•\-\*]+/)
      .map(t => t.trim())
      .filter(t => t.length > 0);

    return (
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {tags.map((tag, idx) => (
          <span key={idx} style={{
            padding: '5px 12px', borderRadius: 6,
            background: 'rgba(99, 102, 241, 0.1)',
            border: '1px solid rgba(99, 102, 241, 0.25)',
            color: '#a5b4fc', fontSize: 12, fontWeight: 500,
            display: 'inline-flex', alignItems: 'center', gap: 6
          }}>
            <span style={{ width: 4, height: 4, borderRadius: '50%', background: '#6366f1' }} />
            {tag}
          </span>
        ))}
      </div>
    );
  }

  // 2. Structured Bullet Points for Experience / Education / Projects / Achievements / Summary
  const lines = strValue.split('\n').filter(l => l.trim().length > 0);

  return (
    <ul style={{ margin: 0, paddingLeft: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8 }}>
      {lines.map((line, idx) => {
        const cleanLine = line.replace(/^[\s•\-\*\d\.\)\:]+/, '').trim();
        const isHeader = line.includes(':') || (line.length < 35 && line === line.toUpperCase());

        return (
          <li key={idx} style={{
            display: 'flex', alignItems: 'flex-start', gap: 10,
            fontSize: 13, color: isHeader ? '#f1f5f9' : '#94a3b8',
            fontWeight: isHeader ? 600 : 400, lineHeight: 1.6
          }}>
            {!isHeader && (
              <span style={{ color: '#6366f1', fontSize: 14, lineHeight: 1, marginTop: 4 }}>•</span>
            )}
            <span style={{ flex: 1 }}>{cleanLine || line}</span>
          </li>
        );
      })}
    </ul>
  );
};

const btnPrimary = { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 14px', borderRadius: 7, background: '#6366f1', border: 'none', color: '#fff', fontSize: 12, fontWeight: 600, cursor: 'pointer' };
const btnSecondary = { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 12px', borderRadius: 7, background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.3)', color: '#818cf8', fontSize: 12, fontWeight: 600, cursor: 'pointer' };
const btnGhost = { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 12px', borderRadius: 7, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: '#94a3b8', fontSize: 12, fontWeight: 500, cursor: 'pointer' };
