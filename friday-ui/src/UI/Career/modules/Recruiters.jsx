import { useState, useEffect } from 'react';
import { Plus, X } from 'lucide-react';
import { getRecruiters, addRecruiter, updateRecruiter } from '../../../api/careerApi.js';
import Skeleton from '../components/Skeleton.jsx';

export default function Recruiters() {
  const [recruiters, setRecruiters] = useState([]);
  const [loading, setLoading]       = useState(true);
  const [selected, setSelected]     = useState(null);
  const [showForm, setShowForm]     = useState(false);
  const [form, setForm]             = useState({ name: '', company: '', email: '', linkedin: '', phone: '', notes: '' });
  const [editNotes, setEditNotes]   = useState('');

  const load = () => {
    getRecruiters().then(d => setRecruiters(d.recruiters || [])).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const handleAdd = async () => {
    if (!form.name) return;
    await addRecruiter(form);
    setShowForm(false); setForm({ name: '', company: '', email: '', linkedin: '', phone: '', notes: '' }); load();
  };

  const handleSaveNotes = async () => {
    if (!selected) return;
    await updateRecruiter(selected.id, { notes: editNotes, last_contact: new Date().toISOString() });
    load();
  };

  if (loading) return <div style={{ padding: 32 }}><Skeleton count={5} /></div>;

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      <div style={{ width: 320, borderRight: '1px solid rgba(255,255,255,0.05)', display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
        <div style={{ padding: '20px 16px 12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: '#f1f5f9' }}>Recruiters</h2>
          <button onClick={() => setShowForm(true)} style={btnPrimary}><Plus size={13} /> Add</button>
        </div>
        <div style={{ flex: 1, overflow: 'auto', padding: '0 8px 16px' }}>
          {recruiters.length === 0 ? (
            <div style={{ padding: 24, textAlign: 'center', color: '#475569', fontSize: 13 }}>No recruiters yet.</div>
          ) : recruiters.map(r => (
            <div key={r.id} onClick={() => { setSelected(r); setEditNotes(r.notes || ''); }}
              style={{ padding: '12px 14px', borderRadius: 8, marginBottom: 4, cursor: 'pointer',
                background: selected?.id === r.id ? 'rgba(99,102,241,0.08)' : 'transparent',
                border: selected?.id === r.id ? '1px solid rgba(99,102,241,0.2)' : '1px solid transparent', transition: 'all 150ms' }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0' }}>{r.name}</div>
              <div style={{ fontSize: 12, color: '#64748b', marginTop: 3 }}>{r.company}</div>
              {r.email && <div style={{ fontSize: 11, color: '#334155', marginTop: 4 }}>{r.email}</div>}
            </div>
          ))}
        </div>
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: 28 }}>
        {!selected ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60%', color: '#475569', fontSize: 14 }}>
            Select a recruiter to view details
          </div>
        ) : (
          <div style={{ maxWidth: 560 }}>
            <h3 style={{ margin: '0 0 4px', fontSize: 18, fontWeight: 700, color: '#f1f5f9' }}>{selected.name}</h3>
            <p style={{ margin: '0 0 20px', fontSize: 13, color: '#64748b' }}>{selected.company}</p>
            {[['Email', selected.email], ['LinkedIn', selected.linkedin], ['Phone', selected.phone]].map(([l, v]) => v ? (
              <div key={l} style={{ display: 'flex', gap: 16, marginBottom: 10 }}>
                <span style={{ fontSize: 12, color: '#475569', minWidth: 80 }}>{l}</span>
                <span style={{ fontSize: 13, color: '#94a3b8' }}>{v}</span>
              </div>
            ) : null)}
            {selected.last_contact && (
              <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
                <span style={{ fontSize: 12, color: '#475569', minWidth: 80 }}>Last contact</span>
                <span style={{ fontSize: 13, color: '#94a3b8' }}>{new Date(selected.last_contact).toLocaleDateString()}</span>
              </div>
            )}
            <div>
              <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 6 }}>Notes</label>
              <textarea value={editNotes} onChange={e => setEditNotes(e.target.value)} rows={6}
                placeholder="Conversation history, follow-up reminders…"
                style={{ width: '100%', padding: '10px 12px', borderRadius: 8, boxSizing: 'border-box', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: '#e2e8f0', fontSize: 13, resize: 'vertical', fontFamily: 'inherit', outline: 'none' }} />
              <button onClick={handleSaveNotes} style={{ ...btnPrimary, marginTop: 8 }}>Save Notes</button>
            </div>
          </div>
        )}
      </div>
      {showForm && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: '#0f1623', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 14, padding: 28, width: 440 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#f1f5f9' }}>Add Recruiter</h3>
              <button onClick={() => setShowForm(false)} style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer' }}><X size={16} /></button>
            </div>
            {[['Name *', 'name'], ['Company', 'company'], ['Email', 'email'], ['LinkedIn', 'linkedin'], ['Phone', 'phone']].map(([label, key]) => (
              <div key={key} style={{ marginBottom: 12 }}>
                <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 5 }}>{label}</label>
                <input value={form[key]} onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  style={{ width: '100%', padding: '9px 12px', borderRadius: 7, boxSizing: 'border-box', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: '#e2e8f0', fontSize: 13, fontFamily: 'inherit', outline: 'none' }} />
              </div>
            ))}
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 8 }}>
              <button onClick={() => setShowForm(false)} style={btnGhost}>Cancel</button>
              <button onClick={handleAdd} disabled={!form.name} style={btnPrimary}>Add</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
const btnPrimary = { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 14px', borderRadius: 7, background: '#6366f1', border: 'none', color: '#fff', fontSize: 12, fontWeight: 600, cursor: 'pointer' };
const btnGhost = { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 14px', borderRadius: 7, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: '#94a3b8', fontSize: 12, cursor: 'pointer' };
