import { useState, useEffect, useRef } from 'react';
import { Plus, Upload, Copy, Archive, Star } from 'lucide-react';
import { getResumes, createResume, uploadResume, updateResume, duplicateResume, recommendResume } from '../../../api/careerApi.js';
import Skeleton from '../components/Skeleton.jsx';

const SECTIONS = ['summary', 'skills', 'experience', 'education', 'projects', 'achievements', 'certifications'];

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
    await createResume(`Resume ${resumes.length + 1}`, {});
    load();
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
              {r.is_recommended ? <Star size={12} style={{ color: '#f59e0b', fill: '#f59e0b' }} /> : null}
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

      {/* ── Resume Editor ────────────────────────────────────────────────────── */}
      <div style={{ flex: 1, overflow: 'auto', padding: 28 }}>
        {!selected ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60%', color: '#334155', gap: 12 }}>
            <span style={{ fontSize: 36 }}>📄</span>
            <p style={{ fontSize: 14, color: '#475569' }}>Select a resume to edit</p>
          </div>
        ) : (
          <>
            {/* Resume header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28 }}>
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
                <button onClick={() => handleArchive(selected.id)} style={{ ...btnGhost, color: '#ef4444' }}>
                  <Archive size={14} /> Archive
                </button>
              </div>
            </div>

            {/* Sections */}
            {SECTIONS.map(section => {
              const isEditing = editing?.section === section;
              const value = selectedContent[section] || '';
              return (
                <div key={section} style={{ marginBottom: 20, borderRadius: 10, border: '1px solid rgba(255,255,255,0.06)', overflow: 'hidden' }}>
                  <div style={{
                    padding: '12px 16px', background: 'rgba(255,255,255,0.02)',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    borderBottom: isEditing ? '1px solid rgba(255,255,255,0.06)' : 'none',
                  }}>
                    <span style={{ fontSize: 12, fontWeight: 600, color: '#64748b', textTransform: 'capitalize' }}>{section}</span>
                    <button onClick={() => setEditing(isEditing ? null : { section, content: value })} style={btnGhost}>
                      {isEditing ? 'Cancel' : 'Edit'}
                    </button>
                  </div>
                  {isEditing ? (
                    <div style={{ padding: 16 }}>
                      <textarea
                        value={editing.content}
                        onChange={e => setEditing(ed => ({ ...ed, content: e.target.value }))}
                        rows={section === 'experience' || section === 'projects' ? 8 : 4}
                        placeholder={`Enter your ${section}…`}
                        style={{
                          width: '100%', padding: '10px 12px', borderRadius: 7, boxSizing: 'border-box',
                          background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
                          color: '#e2e8f0', fontSize: 13, fontFamily: 'monospace', resize: 'vertical',
                        }} />
                      <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                        <button onClick={() => handleSaveSection(section, editing.content)} disabled={saving} style={btnPrimary}>
                          {saving ? 'Saving…' : 'Save'}
                        </button>
                        <button onClick={() => setEditing(null)} style={btnGhost}>Cancel</button>
                      </div>
                    </div>
                  ) : (
                    <div style={{ padding: '12px 16px' }}>
                      {value ? (
                        <p style={{ margin: 0, fontSize: 13, color: '#94a3b8', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>{value}</p>
                      ) : (
                        <p style={{ margin: 0, fontSize: 13, color: '#334155', fontStyle: 'italic' }}>Not filled in yet. Click Edit to add.</p>
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
const btnPrimary = { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 14px', borderRadius: 7, background: '#6366f1', border: 'none', color: '#fff', fontSize: 12, fontWeight: 600, cursor: 'pointer' };
const btnSecondary = { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 12px', borderRadius: 7, background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.3)', color: '#818cf8', fontSize: 12, fontWeight: 600, cursor: 'pointer' };
const btnGhost = { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 12px', borderRadius: 7, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: '#94a3b8', fontSize: 12, fontWeight: 500, cursor: 'pointer' };
