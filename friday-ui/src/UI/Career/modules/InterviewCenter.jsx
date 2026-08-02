import { useState, useEffect } from 'react';
import { Calendar, Plus, Video, X } from 'lucide-react';
import { getInterviews, addInterview, updateInterview, generateInterviewQuestions, getApplications } from '../../../api/careerApi.js';
import StatusBadge from '../components/StatusBadge.jsx';
import Skeleton from '../components/Skeleton.jsx';

const STAGES = ['phone', 'technical', 'hr', 'final', 'offer'];
const OUTCOMES = ['pending', 'passed', 'failed'];

export default function InterviewCenter() {
  const [interviews, setInterviews] = useState([]);
  const [loading, setLoading]       = useState(true);
  const [selected, setSelected]     = useState(null);
  const [questions, setQuestions]   = useState([]);
  const [loadingQ, setLoadingQ]     = useState(false);
  const [showForm, setShowForm]     = useState(false);
  const [applications, setApplications] = useState([]);
  const [form, setForm]             = useState({ application_id: '', stage: 'phone', scheduled_at: '', meeting_link: '', interviewer_name: '', notes: '' });

  const load = () => {
    setLoading(true);
    Promise.all([getInterviews(), getApplications()])
      .then(([iRes, aRes]) => {
        setInterviews(iRes.interviews || []);
        setApplications(aRes.applications || []);
      })
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const upcoming = interviews.filter(i => i.outcome === 'pending');
  const past     = interviews.filter(i => i.outcome !== 'pending');

  const handleGenerateQuestions = async (interview) => {
    setLoadingQ(true);
    // Find job_id via application
    const app = applications.find(a => a.id === interview.application_id);
    if (!app) { setLoadingQ(false); return; }
    const result = await generateInterviewQuestions(app.job_id);
    setQuestions(result.questions || []);
    setLoadingQ(false);
  };

  const handleAddInterview = async () => {
    if (!form.application_id) return;
    await addInterview(form);
    setShowForm(false);
    setForm({ application_id: '', stage: 'phone', scheduled_at: '', meeting_link: '', interviewer_name: '', notes: '' });
    load();
  };

  const handleOutcome = async (id, outcome) => {
    await updateInterview(id, { outcome });
    load();
  };

  if (loading) return <div style={{ padding: 32 }}><Skeleton count={5} /></div>;

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* Left: Interview list */}
      <div style={{ width: 360, borderRight: '1px solid rgba(255,255,255,0.05)', display: 'flex', flexDirection: 'column', overflow: 'hidden', flexShrink: 0 }}>
        <div style={{ padding: '20px 16px 12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
          <h2 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: '#f1f5f9' }}>Interviews</h2>
          <button onClick={() => setShowForm(true)} style={btnPrimary}><Plus size={13} /> Schedule</button>
        </div>
        <div style={{ flex: 1, overflow: 'auto', padding: '0 8px 16px' }}>
          {upcoming.length > 0 && (
            <>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.06em', padding: '4px 8px 8px' }}>Upcoming ({upcoming.length})</div>
              {upcoming.map(i => <InterviewItem key={i.id} interview={i} selected={selected?.id === i.id} onClick={() => { setSelected(i); setQuestions([]); }} />)}
            </>
          )}
          {past.length > 0 && (
            <>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#334155', textTransform: 'uppercase', letterSpacing: '0.06em', padding: '12px 8px 8px' }}>Past ({past.length})</div>
              {past.map(i => <InterviewItem key={i.id} interview={i} selected={selected?.id === i.id} onClick={() => { setSelected(i); setQuestions([]); }} />)}
            </>
          )}
          {interviews.length === 0 && (
            <div style={{ padding: 24, textAlign: 'center', color: '#475569', fontSize: 13 }}>
              No interviews yet.<br />Schedule one above.
            </div>
          )}
        </div>
      </div>

      {/* Right: Detail */}
      <div style={{ flex: 1, overflow: 'auto', padding: 28 }}>
        {!selected ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60%', color: '#334155', gap: 12 }}>
            <Calendar size={40} style={{ strokeWidth: 1 }} />
            <p style={{ fontSize: 14, color: '#475569' }}>Select an interview to see details</p>
          </div>
        ) : (
          <div style={{ maxWidth: 600 }}>
            <div style={{ marginBottom: 20 }}>
              <h3 style={{ margin: '0 0 4px', fontSize: 18, fontWeight: 700, color: '#f1f5f9' }}>
                {selected.job_title || 'Interview'}
              </h3>
              <div style={{ fontSize: 13, color: '#64748b', marginBottom: 10 }}>{selected.company}</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <StatusBadge status={selected.outcome || 'pending'} />
                <span style={{ fontSize: 12, color: '#64748b', padding: '3px 10px', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 999, textTransform: 'capitalize' }}>
                  {selected.stage} round
                </span>
              </div>
            </div>

            {selected.scheduled_at && (
              <InfoRow label="Scheduled" value={new Date(selected.scheduled_at).toLocaleString()} />
            )}
            {selected.interviewer_name && (
              <InfoRow label="Interviewer" value={selected.interviewer_name} />
            )}
            {selected.meeting_link && (
              <div style={{ marginBottom: 12 }}>
                <a href={selected.meeting_link} target="_blank" rel="noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 8, background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)', color: '#818cf8', fontSize: 13, textDecoration: 'none', fontWeight: 600 }}>
                  <Video size={13} /> Join Meeting
                </a>
              </div>
            )}
            {selected.notes && <InfoRow label="Notes" value={selected.notes} />}

            {/* Outcome buttons */}
            {selected.outcome === 'pending' && (
              <div style={{ display: 'flex', gap: 8, margin: '16px 0' }}>
                <button onClick={() => handleOutcome(selected.id, 'passed')} style={{ ...btnPrimary, background: '#22c55e' }}>✓ Passed</button>
                <button onClick={() => handleOutcome(selected.id, 'failed')} style={{ ...btnGhost, color: '#ef4444', borderColor: 'rgba(239,68,68,0.3)' }}>✗ Did not proceed</button>
              </div>
            )}

            {/* Prep Questions */}
            <div style={{ marginTop: 24, padding: '20px', borderRadius: 10, background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  Prep Questions
                </span>
                <button onClick={() => handleGenerateQuestions(selected)} disabled={loadingQ} style={btnGhost}>
                  {loadingQ ? 'Generating…' : '⚡ Generate with Friday'}
                </button>
              </div>
              {questions.length > 0 ? (
                <ol style={{ padding: '0 0 0 18px', margin: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {questions.map((q, i) => (
                    <li key={i} style={{ fontSize: 13, color: '#94a3b8', lineHeight: 1.6 }}>{q}</li>
                  ))}
                </ol>
              ) : (
                <p style={{ fontSize: 13, color: '#334155', margin: 0 }}>
                  Click "Generate" to get AI-powered interview questions for this role.
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Add Interview Modal */}
      {showForm && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: '#0f1623', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 14, padding: 28, width: 480, maxWidth: '90vw' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#f1f5f9' }}>Schedule Interview</h3>
              <button onClick={() => setShowForm(false)} style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer' }}><X size={16} /></button>
            </div>
            <FormField label="Application">
              <select value={form.application_id} onChange={e => setForm(f => ({ ...f, application_id: e.target.value }))} style={selectStyle}>
                <option value="">Select application…</option>
                {applications.map(a => <option key={a.id} value={a.id}>{a.job_title} – {a.company}</option>)}
              </select>
            </FormField>
            <FormField label="Stage">
              <select value={form.stage} onChange={e => setForm(f => ({ ...f, stage: e.target.value }))} style={selectStyle}>
                {STAGES.map(s => <option key={s} value={s} style={{ textTransform: 'capitalize' }}>{s}</option>)}
              </select>
            </FormField>
            <FormField label="Date & Time">
              <input type="datetime-local" value={form.scheduled_at} onChange={e => setForm(f => ({ ...f, scheduled_at: e.target.value }))} style={inputStyle} />
            </FormField>
            <FormField label="Meeting Link">
              <input value={form.meeting_link} onChange={e => setForm(f => ({ ...f, meeting_link: e.target.value }))} placeholder="https://…" style={inputStyle} />
            </FormField>
            <FormField label="Interviewer">
              <input value={form.interviewer_name} onChange={e => setForm(f => ({ ...f, interviewer_name: e.target.value }))} style={inputStyle} />
            </FormField>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 8 }}>
              <button onClick={() => setShowForm(false)} style={btnGhost}>Cancel</button>
              <button onClick={handleAddInterview} disabled={!form.application_id} style={btnPrimary}>Schedule</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function InterviewItem({ interview, selected, onClick }) {
  return (
    <div onClick={onClick} style={{
      padding: '12px 14px', borderRadius: 8, marginBottom: 4, cursor: 'pointer',
      background: selected ? 'rgba(99,102,241,0.08)' : 'transparent',
      border: selected ? '1px solid rgba(99,102,241,0.2)' : '1px solid transparent',
      transition: 'all 150ms',
    }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0' }}>{interview.job_title || 'Interview'}</div>
      <div style={{ fontSize: 12, color: '#64748b', marginTop: 3, textTransform: 'capitalize' }}>{interview.company} · {interview.stage}</div>
      {interview.scheduled_at && (
        <div style={{ fontSize: 11, color: '#475569', marginTop: 5 }}>{new Date(interview.scheduled_at).toLocaleDateString()}</div>
      )}
      <div style={{ marginTop: 6 }}><StatusBadge status={interview.outcome || 'pending'} size="xs" /></div>
    </div>
  );
}

function InfoRow({ label, value }) {
  return (
    <div style={{ display: 'flex', gap: 16, marginBottom: 10 }}>
      <span style={{ fontSize: 12, color: '#475569', minWidth: 100 }}>{label}</span>
      <span style={{ fontSize: 13, color: '#94a3b8' }}>{value}</span>
    </div>
  );
}

function FormField({ label, children }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 5 }}>{label}</label>
      {children}
    </div>
  );
}

const inputStyle = { width: '100%', padding: '9px 12px', borderRadius: 7, boxSizing: 'border-box', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: '#e2e8f0', fontSize: 13, fontFamily: 'inherit', outline: 'none' };
const selectStyle = { ...inputStyle, appearance: 'none' };
const btnPrimary = { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 16px', borderRadius: 8, background: '#6366f1', border: 'none', color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer' };
const btnGhost = { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 14px', borderRadius: 8, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: '#94a3b8', fontSize: 13, fontWeight: 500, cursor: 'pointer' };
