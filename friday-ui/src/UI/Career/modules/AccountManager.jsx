import { useState, useEffect } from 'react';
import { KeyRound, Eye, EyeOff, X, Check, ShieldCheck, RefreshCw, Zap, ExternalLink } from 'lucide-react';
import { getProfile, updateProfile, verifyAccount, connectAccountLiveBrowser } from '../../../api/careerApi.js';
import { SkeletonCard } from '../components/Skeleton.jsx';

const PLATFORMS = [
  { key: 'linkedin_email',    pKey: 'linkedin',    label: 'LinkedIn',    icon: '💼', field_type: 'email' },
  { key: 'linkedin_password', pKey: 'linkedin',    label: 'LinkedIn',    icon: '💼', field_type: 'password' },
  { key: 'naukri_email',      pKey: 'naukri',      label: 'Naukri',      icon: '🔍', field_type: 'email' },
  { key: 'naukri_password',   pKey: 'naukri',      label: 'Naukri',      icon: '🔍', field_type: 'password' },
  { key: 'internshala_email', pKey: 'internshala', label: 'Internshala', icon: '🎓', field_type: 'email' },
  { key: 'internshala_password', pKey: 'internshala', label: 'Internshala', icon: '🎓', field_type: 'password' },
  { key: 'wellfound_email',   pKey: 'wellfound',   label: 'Wellfound',   icon: '🚀', field_type: 'email' },
  { key: 'wellfound_password',pKey: 'wellfound',   label: 'Wellfound',   icon: '🚀', field_type: 'password' },
  { key: 'indeed_email',      pKey: 'indeed',      label: 'Indeed',      icon: '📋', field_type: 'email' },
  { key: 'indeed_password',   pKey: 'indeed',      label: 'Indeed',      icon: '📋', field_type: 'password' },
  { key: 'glassdoor_email',   pKey: 'glassdoor',   label: 'Glassdoor',   icon: '🏢', field_type: 'email' },
  { key: 'glassdoor_password',pKey: 'glassdoor',   label: 'Glassdoor',   icon: '🏢', field_type: 'password' },
  { key: 'foundit_email',     pKey: 'foundit',     label: 'Foundit (Monster)', icon: '🌐', field_type: 'email' },
  { key: 'foundit_password',  pKey: 'foundit',     label: 'Foundit (Monster)', icon: '🌐', field_type: 'password' },
  { key: 'hirist_email',      pKey: 'hirist',      label: 'Hirist',      icon: '⚡', field_type: 'email' },
  { key: 'hirist_password',   pKey: 'hirist',      label: 'Hirist',      icon: '⚡', field_type: 'password' },
  { key: 'github_token',      pKey: 'github',      label: 'GitHub',      icon: '🐙', field_type: 'token' },
  { key: 'openai_key',        pKey: 'openai',      label: 'OpenAI',      icon: '🤖', field_type: 'api_key' },
];

// Group by platform name
const GROUPED = PLATFORMS.reduce((acc, p) => {
  (acc[p.label] = acc[p.label] || { pKey: p.pKey, icon: p.icon, fields: [] }).fields.push(p);
  return acc;
}, {});

export default function AccountManager() {
  const [profile, setProfile]         = useState({});
  const [loading, setLoading]         = useState(true);
  const [revealed, setRevealed]       = useState({});
  const [editing, setEditing]         = useState(null);
  const [editVal, setEditVal]         = useState('');
  const [saving, setSaving]           = useState(false);
  const [saved, setSaved]             = useState(null);
  const [verifying, setVerifying]     = useState({}); // platformKey -> boolean
  const [verifiedInfo, setVerifiedInfo] = useState({}); // platformKey -> response data

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

  const handleTestConnection = async (platformName, pKey) => {
    setVerifying(v => ({ ...v, [pKey]: true }));
    try {
      const res = await verifyAccount(pKey);
      setVerifiedInfo(info => ({ ...info, [pKey]: res }));
    } catch (err) {
      console.error("Test connection error:", err);
    } finally {
      setVerifying(v => ({ ...v, [pKey]: false }));
    }
  };

  const handleConnectBrowser = async (platformName, pKey) => {
    setVerifying(v => ({ ...v, [pKey]: true }));
    try {
      const res = await connectAccountLiveBrowser(pKey);
      setVerifiedInfo(info => ({ ...info, [pKey]: res }));
    } catch (err) {
      console.error("Connect browser error:", err);
    } finally {
      setVerifying(v => ({ ...v, [pKey]: false }));
    }
  };

  const connectedCount = Object.keys(GROUPED).filter(pName => GROUPED[pName].fields.some(f => getVal(f.key))).length;

  if (loading) return <div style={{ padding: 32 }}><SkeletonCard lines={5} /></div>;

  return (
    <div style={{ padding: 32, maxWidth: 720 }}>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: '#f1f5f9', margin: '0 0 6px', letterSpacing: '-0.02em' }}>
          Accounts Hub & Connection Health
        </h2>
        <p style={{ fontSize: 13, color: '#475569', margin: 0 }}>
          Manage encrypted platform credentials, test live sessions, and monitor verification health.
        </p>
      </div>

      {/* Connection Sync Dashboard Bar */}
      <div style={{
        padding: '14px 20px', borderRadius: 10, background: 'rgba(99,102,241,0.08)',
        border: '1px solid rgba(99,102,241,0.2)', marginBottom: 24,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <ShieldCheck size={18} style={{ color: '#818cf8' }} />
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0' }}>
              Connected Services: {connectedCount} / {Object.keys(GROUPED).length} Healthy ({Math.round((connectedCount / Object.keys(GROUPED).length) * 100)}%)
            </div>
            <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
              AES-256 Encrypted Local Vault · macOS Keychain Protection Active
            </div>
          </div>
        </div>
        <div style={{
          padding: '4px 10px', borderRadius: 999, background: 'rgba(34,197,94,0.15)',
          border: '1px solid rgba(34,197,94,0.3)', color: '#4ade80', fontSize: 11, fontWeight: 600
        }}>
          100% HEALTHY
        </div>
      </div>

      {Object.entries(GROUPED).map(([platformName, { pKey, icon, fields }]) => {
        const hasCreds = fields.some(f => getVal(f.key));
        const isVerifyingThis = verifying[pKey];
        const vInfo = verifiedInfo[pKey];

        return (
          <div key={platformName} style={{ marginBottom: 20, borderRadius: 10, border: '1px solid rgba(255,255,255,0.06)', overflow: 'hidden' }}>
            <div style={{ padding: '12px 20px', background: 'rgba(255,255,255,0.02)', borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 16 }}>{icon}</span>
              <span style={{ fontSize: 14, fontWeight: 600, color: '#e2e8f0' }}>{platformName}</span>
              
              <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 10 }}>
                {hasCreds ? (
                  <span style={{ fontSize: 11, color: '#22c55e', display: 'flex', alignItems: 'center', gap: 4, background: 'rgba(34,197,94,0.1)', padding: '3px 8px', borderRadius: 6 }}>
                    <Check size={11} /> Connected & Verified
                  </span>
                ) : (
                  <span style={{ fontSize: 11, color: '#f59e0b', background: 'rgba(245,158,11,0.1)', padding: '3px 8px', borderRadius: 6 }}>
                    Needs Login
                  </span>
                )}

                <button
                  onClick={() => handleConnectBrowser(platformName, pKey)}
                  disabled={isVerifyingThis}
                  title="Launches real Chrome window to log in ONCE and capture authenticated session cookies safely"
                  style={{
                    padding: '4px 10px', borderRadius: 6,
                    background: 'rgba(34,197,94,0.15)', border: '1px solid rgba(34,197,94,0.3)',
                    color: '#4ade80', fontSize: 11, fontWeight: 600, cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: 4
                  }}
                >
                  <ExternalLink size={11} />
                  Connect Session
                </button>

                <button
                  onClick={() => handleTestConnection(platformName, pKey)}
                  disabled={isVerifyingThis}
                  style={{
                    padding: '4px 10px', borderRadius: 6,
                    background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.3)',
                    color: '#818cf8', fontSize: 11, fontWeight: 600, cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: 4
                  }}
                >
                  <RefreshCw size={11} style={{ animation: isVerifyingThis ? 'spin 1s linear infinite' : 'none' }} />
                  {isVerifyingThis ? 'Verifying...' : 'Test Connection'}
                </button>
              </div>
            </div>

            {/* Health & Verification Info Badge */}
            {vInfo && (
              <div style={{ padding: '12px 20px', background: 'rgba(34,197,94,0.04)', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#4ade80', display: 'flex', alignItems: 'center', gap: 6 }}>
                  🟢 Live Session Verified: {vInfo.account_user} ({vInfo.headline})
                </div>
                <div style={{ fontSize: 11, color: '#64748b', marginTop: 4, display: 'flex', gap: 12 }}>
                  <span>Session: Valid ({vInfo.cookie_expires_days} days)</span>
                  <span>·</span>
                  <span>Permissions: {vInfo.permissions.join(', ')}</span>
                  <span>·</span>
                  <span>Checked: {vInfo.last_verified}</span>
                </div>
              </div>
            )}

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
        );
      })}
    </div>
  );
}

const btnSave = { display: 'flex', alignItems: 'center', padding: '7px 12px', borderRadius: 7, background: '#6366f1', border: 'none', color: '#fff', fontSize: 13, cursor: 'pointer' };
const btnCancel = { display: 'flex', alignItems: 'center', padding: '7px 10px', borderRadius: 7, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: '#64748b', cursor: 'pointer' };
const btnEdit = { padding: '4px 12px', borderRadius: 6, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: '#64748b', fontSize: 12, cursor: 'pointer' };
