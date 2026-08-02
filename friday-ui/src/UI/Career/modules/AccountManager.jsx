import { useState, useEffect } from 'react';
import { KeyRound, Eye, EyeOff, X, Check } from 'lucide-react';
import { getProfile, updateProfile } from '../../../api/careerApi.js';
import { SkeletonCard } from '../components/Skeleton.jsx';

const PLATFORMS = [
  { key: 'linkedin_email',    label: 'LinkedIn',    icon: '💼', field_type: 'email' },
  { key: 'linkedin_password', label: 'LinkedIn',    icon: '💼', field_type: 'password' },
  { key: 'naukri_email',      label: 'Naukri',      icon: '🔍', field_type: 'email' },
  { key: 'naukri_password',   label: 'Naukri',      icon: '🔍', field_type: 'password' },
  { key: 'indeed_email',      label: 'Indeed',      icon: '📋', field_type: 'email' },
  { key: 'indeed_password',   label: 'Indeed',      icon: '📋', field_type: 'password' },
  { key: 'wellfound_email',   label: 'Wellfound',   icon: '🚀', field_type: 'email' },
  { key: 'wellfound_password',label: 'Wellfound',   icon: '🚀', field_type: 'password' },
  { key: 'github_token',      label: 'GitHub',      icon: '🐙', field_type: 'token' },
  { key: 'openai_key',        label: 'OpenAI',      icon: '🤖', field_type: 'api_key' },
];

// Group by platform name
const GROUPED = PLATFORMS.reduce((acc, p) => {
  (acc[p.label] = acc[p.label] || { icon: p.icon, fields: [] }).fields.push(p);
  return acc;
}, {});

export default function AccountManager() {
  const [profile, setProfile]     = useState({});
  const [loading, setLoading]     = useState(true);
  const [revealed, setRevealed]   = useState({});
  const [editing, setEditing]     = useState(null);
  const [editVal, setEditVal]     = useState('');
  const [saving, setSaving]       = useState(false);
  const [saved, setSaved]         = useState(null);

  const load = () => {
    getProfile().then(d => setProfile(d.profile || {})).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const getVal = (key) => profile[key]?.value || '';

  const handleSave = async (key) => {
    setSaving(true);
    await updateProfile({ [key]: editVal });
    setSaved(key);
    setEditing(null);
    setSaving(false);
    setTimeout(() => setSaved(null), 2000);
    load();
  };

  if (loading) return <div style={{ padding: 32 }}><SkeletonCard lines={5} /></div>;

  return (
    <div style={{ padding: 32, maxWidth: 680 }}>
      <div style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: '#f1f5f9', margin: '0 0 6px', letterSpacing: '-0.02em' }}>
          Account Manager
        </h2>
        <p style={{ fontSize: 13, color: '#475569', margin: 0 }}>
          Store platform credentials securely for auto-fill and one-click applications.
          All data is encrypted locally — never sent to external servers.
        </p>
      </div>

      {/* Security notice */}
      <div style={{ padding: '12px 16px', borderRadius: 8, background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)', marginBottom: 28, display: 'flex', gap: 10 }}>
        <KeyRound size={14} style={{ color: '#f59e0b', flexShrink: 0, marginTop: 1 }} />
        <p style={{ margin: 0, fontSize: 12, color: '#92400e', lineHeight: 1.6 }}>
          Credentials are stored in your local vault and encrypted at rest. F.R.I.D.A.Y. will never auto-submit applications — you always confirm first.
        </p>
      </div>

      {Object.entries(GROUPED).map(([platformName, { icon, fields }]) => (
        <div key={platformName} style={{ marginBottom: 20, borderRadius: 10, border: '1px solid rgba(255,255,255,0.06)', overflow: 'hidden' }}>
          <div style={{ padding: '12px 20px', background: 'rgba(255,255,255,0.02)', borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 16 }}>{icon}</span>
            <span style={{ fontSize: 14, fontWeight: 600, color: '#e2e8f0' }}>{platformName}</span>
            {fields.every(f => getVal(f.key)) && (
              <span style={{ marginLeft: 'auto', fontSize: 11, color: '#22c55e', display: 'flex', alignItems: 'center', gap: 4 }}>
                <Check size={12} /> Connected
              </span>
            )}
          </div>
          {fields.map((field, i) => {
            const val = getVal(field.key);
            const isEditing = editing === field.key;
            const isRevealed = revealed[field.key];
            const fieldLabel = field.field_type === 'password' ? 'Password' : field.field_type === 'token' ? 'Token' : field.field_type === 'api_key' ? 'API Key' : 'Email / Username';
            return (
              <div key={field.key} style={{
                padding: '13px 20px',
                borderBottom: i < fields.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
                background: isEditing ? 'rgba(99,102,241,0.04)' : 'transparent',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{ fontSize: 12, color: '#64748b', minWidth: 120 }}>{fieldLabel}</span>
                  {isEditing ? (
                    <div style={{ flex: 1, display: 'flex', gap: 8 }}>
                      <input
                        type={field.field_type === 'password' || field.field_type === 'token' || field.field_type === 'api_key' ? 'password' : 'email'}
                        value={editVal}
                        onChange={e => setEditVal(e.target.value)}
                        placeholder={`Enter ${fieldLabel.toLowerCase()}…`}
                        autoFocus
                        style={{ flex: 1, padding: '7px 10px', borderRadius: 7, background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(99,102,241,0.3)', color: '#e2e8f0', fontSize: 13, outline: 'none', fontFamily: 'inherit' }} />
                      <button onClick={() => handleSave(field.key)} disabled={saving} style={btnSave}>
                        {saving ? '…' : <Check size={14} />}
                      </button>
                      <button onClick={() => setEditing(null)} style={btnCancel}><X size={14} /></button>
                    </div>
                  ) : (
                    <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{ fontSize: 13, color: val ? '#94a3b8' : '#334155', fontStyle: val ? 'normal' : 'italic', flex: 1 }}>
                        {val ? (isRevealed ? val : '••••••••••••') : 'Not set'}
                      </span>
                      {saved === field.key && (
                        <span style={{ fontSize: 11, color: '#22c55e', display: 'flex', alignItems: 'center', gap: 4 }}>
                          <Check size={11} /> Saved
                        </span>
                      )}
                      {val && (
                        <button onClick={() => setRevealed(r => ({ ...r, [field.key]: !r[field.key] }))}
                          style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#475569', padding: 0 }}>
                          {isRevealed ? <EyeOff size={14} /> : <Eye size={14} />}
                        </button>
                      )}
                      <button onClick={() => { setEditing(field.key); setEditVal(val); }} style={btnEdit}>
                        {val ? 'Update' : '+ Set'}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}

const btnSave = { display: 'flex', alignItems: 'center', padding: '7px 12px', borderRadius: 7, background: '#6366f1', border: 'none', color: '#fff', fontSize: 13, cursor: 'pointer' };
const btnCancel = { display: 'flex', alignItems: 'center', padding: '7px 10px', borderRadius: 7, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: '#64748b', cursor: 'pointer' };
const btnEdit = { padding: '4px 12px', borderRadius: 6, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: '#64748b', fontSize: 12, cursor: 'pointer' };
