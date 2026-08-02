import { useState, useEffect } from 'react';
import { Eye, EyeOff, Check, X } from 'lucide-react';
import { getProfile, updateProfile } from '../../../api/careerApi.js';
import { SkeletonCard } from '../components/Skeleton.jsx';

const FIELDS = [
  { key: 'name',           label: 'Full Name',         section: 'Contact'        },
  { key: 'email',          label: 'Email',             section: 'Contact', sensitive: true },
  { key: 'phone',          label: 'Phone',             section: 'Contact', sensitive: true },
  { key: 'address',        label: 'Address',           section: 'Contact', sensitive: true },
  { key: 'linkedin',       label: 'LinkedIn URL',      section: 'Links'          },
  { key: 'github',         label: 'GitHub URL',        section: 'Links'          },
  { key: 'portfolio',      label: 'Portfolio URL',     section: 'Links'          },
  { key: 'education',      label: 'Education',         section: 'Background', multiline: true },
  { key: 'experience',     label: 'Total Experience',  section: 'Background'     },
  { key: 'skills',         label: 'Core Skills',       section: 'Background', multiline: true },
  { key: 'certifications', label: 'Certifications',    section: 'Background', multiline: true },
  { key: 'achievements',   label: 'Achievements',      section: 'Background', multiline: true },
  { key: 'preferred_salary', label: 'Preferred Salary', section: 'Career'       },
  { key: 'notice_period',  label: 'Notice Period',     section: 'Career'         },
  { key: 'work_auth',      label: 'Work Authorization', section: 'Career'        },
];

const SECTIONS = [...new Set(FIELDS.map(f => f.section))];

export default function PersonalVault() {
  const [profile, setProfile]     = useState({});
  const [loading, setLoading]     = useState(true);
  const [editing, setEditing]     = useState(null);
  const [editVal, setEditVal]     = useState('');
  const [revealed, setRevealed]   = useState({});
  const [saving, setSaving]       = useState(false);

  const load = () => {
    getProfile().then(d => setProfile(d.profile || {})).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const getVal = (key) => profile[key]?.value || '';

  const handleEdit = (field) => {
    setEditing(field.key);
    setEditVal(getVal(field.key));
  };

  const handleSave = async (key) => {
    setSaving(true);
    await updateProfile({ [key]: editVal });
    setEditing(null);
    setSaving(false);
    load();
  };

  if (loading) return <div style={{ padding: 32 }}><SkeletonCard lines={6} /></div>;

  return (
    <div style={{ padding: 32, maxWidth: 680 }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, color: '#f1f5f9', margin: '0 0 6px', letterSpacing: '-0.02em' }}>Personal Vault</h2>
      <p style={{ fontSize: 13, color: '#475569', margin: '0 0 32px' }}>
        Your information is stored locally and used to fill applications and generate cover letters.
      </p>

      {SECTIONS.map(section => {
        const sectionFields = FIELDS.filter(f => f.section === section);
        return (
          <div key={section} style={{ marginBottom: 28 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }}>{section}</div>
            <div style={{ borderRadius: 10, border: '1px solid rgba(255,255,255,0.06)', overflow: 'hidden' }}>
              {sectionFields.map((field, i) => {
                const val = getVal(field.key);
                const isEditing = editing === field.key;
                const isRevealed = revealed[field.key];
                const showMasked = field.sensitive && !isRevealed && val;
                return (
                  <div key={field.key} style={{
                    padding: '14px 20px',
                    borderBottom: i < sectionFields.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
                    background: isEditing ? 'rgba(99,102,241,0.04)' : 'transparent',
                    transition: 'background 150ms',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
                      <label style={{ fontSize: 12, color: '#64748b', fontWeight: 500, minWidth: 160, paddingTop: isEditing ? 0 : 3 }}>{field.label}</label>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        {isEditing ? (
                          <div>
                            {field.multiline ? (
                              <textarea value={editVal} onChange={e => setEditVal(e.target.value)} rows={4}
                                style={textareaStyle} autoFocus />
                            ) : (
                              <input value={editVal} onChange={e => setEditVal(e.target.value)}
                                style={inputStyle} autoFocus />
                            )}
                            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                              <button onClick={() => handleSave(field.key)} disabled={saving} style={btnSave}>
                                <Check size={12} /> {saving ? 'Saving…' : 'Save'}
                              </button>
                              <button onClick={() => setEditing(null)} style={btnCancel}>
                                <X size={12} /> Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            <span style={{ fontSize: 13, color: val ? '#cbd5e1' : '#334155', flex: 1, wordBreak: 'break-word', fontStyle: val ? 'normal' : 'italic' }}>
                              {showMasked ? '••••••••••••' : val || 'Not set'}
                            </span>
                            {field.sensitive && val && (
                              <button onClick={() => setRevealed(r => ({ ...r, [field.key]: !r[field.key] }))}
                                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#475569', padding: 0 }}>
                                {isRevealed ? <EyeOff size={14} /> : <Eye size={14} />}
                              </button>
                            )}
                            <button onClick={() => handleEdit(field)} style={btnEdit}>Edit</button>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

const inputStyle = { width: '100%', padding: '8px 12px', borderRadius: 7, boxSizing: 'border-box', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(99,102,241,0.3)', color: '#e2e8f0', fontSize: 13, outline: 'none', fontFamily: 'inherit' };
const textareaStyle = { ...{ width: '100%', padding: '8px 12px', borderRadius: 7, boxSizing: 'border-box', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(99,102,241,0.3)', color: '#e2e8f0', fontSize: 13, outline: 'none', fontFamily: 'inherit', resize: 'vertical' } };
const btnSave = { display: 'inline-flex', alignItems: 'center', gap: 5, padding: '6px 12px', borderRadius: 6, background: '#6366f1', border: 'none', color: '#fff', fontSize: 12, fontWeight: 600, cursor: 'pointer' };
const btnCancel = { display: 'inline-flex', alignItems: 'center', gap: 5, padding: '6px 12px', borderRadius: 6, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: '#64748b', fontSize: 12, cursor: 'pointer' };
const btnEdit = { padding: '4px 12px', borderRadius: 6, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: '#64748b', fontSize: 12, cursor: 'pointer' };
