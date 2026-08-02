import { useState, useEffect } from 'react';
import { getApplications, updateApplication } from '../../../api/careerApi.js';
import StatusBadge from '../components/StatusBadge.jsx';
import MatchScoreRing from '../components/MatchScoreRing.jsx';
import Skeleton from '../components/Skeleton.jsx';

const COLUMNS = [
  { id: 'saved',      label: 'Saved'     },
  { id: 'ready',      label: 'Ready'     },
  { id: 'submitted',  label: 'Submitted' },
  { id: 'viewed',     label: 'Viewed'    },
  { id: 'interview',  label: 'Interview' },
  { id: 'offer',      label: 'Offer'     },
  { id: 'rejected',   label: 'Rejected'  },
];

export default function Applications() {
  const [apps, setApps]         = useState([]);
  const [loading, setLoading]   = useState(true);
  const [selected, setSelected] = useState(null);
  const [dragging, setDragging] = useState(null);
  const [view, setView]         = useState('kanban'); // 'kanban' | 'table'

  useEffect(() => {
    getApplications().then(d => setApps(d.applications || [])).finally(() => setLoading(false));
  }, []);

  const grouped = COLUMNS.reduce((acc, col) => {
    acc[col.id] = apps.filter(a => a.status === col.id);
    return acc;
  }, {});

  const handleDrop = async (e, targetStatus) => {
    e.preventDefault();
    if (!dragging) return;
    if (dragging.status === targetStatus) { setDragging(null); return; }
    await updateApplication(dragging.id, { status: targetStatus });
    setApps(prev => prev.map(a => a.id === dragging.id ? { ...a, status: targetStatus } : a));
    setDragging(null);
  };

  const handleNotes = async (id, notes) => {
    await updateApplication(id, { notes });
    setApps(prev => prev.map(a => a.id === id ? { ...a, notes } : a));
  };

  if (loading) return <div style={{ padding: 32 }}><Skeleton count={6} /></div>;

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ padding: '20px 24px 0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#f1f5f9' }}>Applications</h2>
          <p style={{ margin: '4px 0 0', fontSize: 13, color: '#475569' }}>{apps.length} total applications</p>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {['kanban', 'table'].map(v => (
            <button key={v} onClick={() => setView(v)} style={{
              padding: '6px 14px', borderRadius: 7, border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 600, textTransform: 'capitalize',
              background: view === v ? 'rgba(99,102,241,0.15)' : 'rgba(255,255,255,0.04)',
              color: view === v ? '#818cf8' : '#64748b',
            }}>{v}</button>
          ))}
        </div>
      </div>

      {/* Kanban Board */}
      {view === 'kanban' && (
        <div style={{ flex: 1, overflow: 'auto', padding: 24 }}>
          <div style={{ display: 'flex', gap: 12, minWidth: 'max-content', alignItems: 'flex-start', height: '100%' }}>
            {COLUMNS.map(col => (
              <div key={col.id} style={{ width: 220, flexShrink: 0 }}
                onDragOver={e => e.preventDefault()}
                onDrop={e => handleDrop(e, col.id)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                  <span style={{ fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{col.label}</span>
                  <span style={{ fontSize: 11, color: '#334155', background: 'rgba(255,255,255,0.05)', borderRadius: 99, padding: '2px 7px' }}>
                    {grouped[col.id]?.length || 0}
                  </span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minHeight: 60, padding: 4, borderRadius: 8, background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.04)' }}>
                  {(grouped[col.id] || []).map(app => (
                    <div key={app.id}
                      draggable onDragStart={() => setDragging(app)}
                      onClick={() => setSelected(selected?.id === app.id ? null : app)}
                      style={{
                        padding: '10px 12px', borderRadius: 8, background: '#0f172a',
                        border: selected?.id === app.id ? '1px solid rgba(99,102,241,0.4)' : '1px solid rgba(255,255,255,0.06)',
                        cursor: 'grab', transition: 'all 150ms',
                      }}>
                      <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0', lineHeight: 1.3 }}>{app.job_title || 'Unknown Role'}</div>
                      <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>{app.company}</div>
                      {app.match_score > 0 && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 8 }}>
                          <MatchScoreRing score={Math.round(app.match_score)} size={28} />
                          <span style={{ fontSize: 11, color: '#475569' }}>match</span>
                        </div>
                      )}
                    </div>
                  ))}
                  {(grouped[col.id] || []).length === 0 && (
                    <div style={{ padding: '20px 8px', textAlign: 'center', color: '#1e293b', fontSize: 12 }}>
                      Drop here
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Table View */}
      {view === 'table' && (
        <div style={{ flex: 1, overflow: 'auto', padding: '0 24px 24px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, marginTop: 16 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                {['Company', 'Role', 'Status', 'Match', 'Applied', 'Notes'].map(h => (
                  <th key={h} style={{ padding: '8px 12px', textAlign: 'left', color: '#64748b', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {apps.map(app => (
                <tr key={app.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                  <td style={{ padding: '10px 12px', color: '#cbd5e1', fontWeight: 500 }}>{app.company}</td>
                  <td style={{ padding: '10px 12px', color: '#94a3b8' }}>{app.job_title}</td>
                  <td style={{ padding: '10px 12px' }}><StatusBadge status={app.status} /></td>
                  <td style={{ padding: '10px 12px' }}>
                    {app.match_score > 0 ? <span style={{ color: '#22c55e', fontWeight: 600 }}>{Math.round(app.match_score)}%</span> : '—'}
                  </td>
                  <td style={{ padding: '10px 12px', color: '#475569', fontSize: 12 }}>
                    {app.applied_at ? new Date(app.applied_at).toLocaleDateString() : '—'}
                  </td>
                  <td style={{ padding: '10px 12px', color: '#475569', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {app.notes || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Notes drawer for selected */}
      {selected && view === 'kanban' && (
        <div style={{
          position: 'fixed', right: 0, top: 52, bottom: 0, width: 320,
          background: '#0d1420', borderLeft: '1px solid rgba(255,255,255,0.07)',
          padding: 20, overflow: 'auto', zIndex: 10,
        }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#f1f5f9', marginBottom: 4 }}>{selected.job_title}</div>
          <div style={{ fontSize: 13, color: '#64748b', marginBottom: 16 }}>{selected.company}</div>
          <StatusBadge status={selected.status} />
          <div style={{ marginTop: 20 }}>
            <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 6 }}>Notes</label>
            <textarea
              defaultValue={selected.notes || ''}
              onBlur={e => handleNotes(selected.id, e.target.value)}
              placeholder="Add notes about this application…"
              rows={6}
              style={{
                width: '100%', padding: '10px 12px', borderRadius: 8, boxSizing: 'border-box',
                background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
                color: '#e2e8f0', fontSize: 13, resize: 'vertical', fontFamily: 'inherit',
              }} />
          </div>
          {selected.follow_up_date && (
            <div style={{ marginTop: 12 }}>
              <span style={{ fontSize: 12, color: '#64748b' }}>Follow-up: </span>
              <span style={{ fontSize: 12, color: '#f59e0b' }}>{selected.follow_up_date}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
