import { useState, useEffect, useCallback } from 'react';
import { Mic, Upload, FileText, ListChecks, Search, X, Check, AlertTriangle, Loader, CheckCircle2 } from 'lucide-react';
import {
  fetchMeetings, searchMeetings, fetchActionItems,
  processTranscript, transcribeMeeting, pushMeetingTodos,
} from '../../api/meetings';

const CARD_STYLE = {
  position: 'fixed',
  top: 80,
  right: 220,
  zIndex: 50,
  width: 380,
  maxHeight: '72vh',
  display: 'flex',
  flexDirection: 'column',
  background: 'rgba(2, 6, 20, 0.92)',
  border: '1px solid rgba(0, 183, 255, 0.25)',
  borderRadius: 16,
  backdropFilter: 'blur(18px)',
  boxShadow: '0 24px 64px rgba(0,0,0,0.55), 0 0 24px rgba(0,183,255,0.08)',
  overflow: 'hidden',
  fontFamily: 'Inter, system-ui, sans-serif',
};

const ACCENT = '#00B7FF';
const TEXT = '#DFFAFF';
const MUTED = 'rgba(223,250,255,0.55)';

const fmtDate = (iso) => {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString('en-IN', {
    day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit', hour12: true,
  });
};

export default function MeetingsCard() {
  const [open, setOpen] = useState(true);
  const [tab, setTab] = useState('meetings');
  const [meetings, setMeetings] = useState([]);
  const [actionItems, setActionItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');

  // New meeting state
  const [pasteText, setPasteText] = useState('');
  const [processing, setProcessing] = useState(false);
  const [lastMeeting, setLastMeeting] = useState(null);
  const [pushingTodos, setPushingTodos] = useState(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [m, a] = await Promise.all([fetchMeetings(20), fetchActionItems()]);
      setMeetings(m);
      setActionItems(a);
    } catch (err) {
      setError(err.message || 'Could not load meetings.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { if (open) loadAll(); }, [open, loadAll]);

  const doSearch = async () => {
    if (!query.trim()) { loadAll(); return; }
    setLoading(true);
    setError('');
    try {
      setMeetings(await searchMeetings(query.trim()));
    } catch (err) {
      setError(err.message || 'Search failed.');
    } finally {
      setLoading(false);
    }
  };

  const runProcess = async () => {
    setError('');
    setLastMeeting(null);
    setProcessing(true);
    try {
      const meeting = await processTranscript(pasteText.trim());
      setLastMeeting(meeting);
      setPasteText('');
      loadAll();
    } catch (err) {
      setError(err.message || 'Processing failed.');
    } finally {
      setProcessing(false);
    }
  };

  const onFile = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setError('');
    setLastMeeting(null);
    setProcessing(true);
    try {
      const meeting = await transcribeMeeting(f, f.name);
      setLastMeeting(meeting);
      loadAll();
    } catch (err) {
      setError(err.message || 'Transcription failed.');
    } finally {
      setProcessing(false);
      e.target.value = '';
    }
  };

  const pushTodos = async (id) => {
    setPushingTodos(id);
    setError('');
    try {
      const res = await pushMeetingTodos(id);
      setError(`Added ${res.added?.length || 0} todo(s) to Tasks.`);
      setTimeout(() => setError(''), 4000);
    } catch (err) {
      setError(err.message || 'Could not push todos.');
    } finally {
      setPushingTodos(null);
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        style={{
          position: 'fixed', top: 80, right: 220, zIndex: 50,
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '10px 14px', borderRadius: 999,
          background: 'rgba(2, 6, 20, 0.9)', border: '1px solid rgba(0,183,255,0.3)',
          color: ACCENT, cursor: 'pointer', fontFamily: 'Inter, system-ui, sans-serif',
          fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase',
        }}
      >
        <Mic size={13} />
        Meetings
        {actionItems.length > 0 && (
          <span style={{ background: '#0ea5e9', color: '#001018', borderRadius: 99, padding: '1px 7px', fontSize: 10, fontWeight: 700 }}>
            {actionItems.length}
          </span>
        )}
      </button>
    );
  }

  const inputStyle = {
    width: '100%', padding: '8px 10px', marginBottom: 8,
    background: 'rgba(0,183,255,0.06)', border: '1px solid rgba(0,183,255,0.2)',
    borderRadius: 8, color: TEXT, fontSize: 12, outline: 'none',
    boxSizing: 'border-box', fontFamily: 'inherit',
  };

  return (
    <div style={CARD_STYLE}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px', borderBottom: '1px solid rgba(0,183,255,0.15)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: ACCENT }}>
          <Mic size={14} />
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.14em' }}>MEETINGS</span>
          {actionItems.length > 0 && (
            <span style={{ background: 'rgba(14,165,233,0.2)', color: '#7dd3fc', borderRadius: 99, padding: '1px 7px', fontSize: 10, fontWeight: 700 }}>
              {actionItems.length} actions
            </span>
          )}
        </div>
        <button onClick={() => setOpen(false)} style={{ background: 'none', border: 'none', color: MUTED, cursor: 'pointer', padding: 2 }}>
          <X size={14} />
        </button>
      </div>

      <div style={{ display: 'flex', gap: 4, padding: '8px 14px 0' }}>
        {[
          { id: 'meetings', label: 'Meetings', icon: FileText },
          { id: 'actions', label: 'Action Items', icon: ListChecks },
          { id: 'new', label: 'New', icon: Upload },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => { setTab(id); setError(''); }}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px',
              background: tab === id ? 'rgba(0,183,255,0.12)' : 'transparent',
              border: `1px solid ${tab === id ? 'rgba(0,183,255,0.4)' : 'rgba(0,183,255,0.15)'}`,
              borderRadius: 8, color: tab === id ? ACCENT : MUTED, cursor: 'pointer',
              fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase',
            }}
          >
            <Icon size={11} />
            {label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>
        {error && (
          <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 8, padding: 10, marginBottom: 10, fontSize: 11, color: '#fca5a5' }}>
            <AlertTriangle size={12} style={{ flexShrink: 0, marginTop: 1 }} />
            <span>{error}</span>
          </div>
        )}

        {lastMeeting && (
          <div style={{ background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.3)', borderRadius: 10, padding: 12, marginBottom: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#86efac', fontSize: 11, fontWeight: 700, marginBottom: 4 }}>
              <CheckCircle2 size={12} /> Processed — {lastMeeting.title}
            </div>
            <div style={{ fontSize: 11, color: MUTED }}>{lastMeeting.summary}</div>
            {lastMeeting.action_items?.length > 0 && (
              <button onClick={() => pushTodos(lastMeeting.id)} disabled={pushingTodos === lastMeeting.id} style={{ marginTop: 8, display: 'inline-flex', alignItems: 'center', gap: 6, padding: '5px 10px', background: 'rgba(0,183,255,0.12)', border: '1px solid rgba(0,183,255,0.3)', borderRadius: 8, color: ACCENT, cursor: 'pointer', fontSize: 10, textTransform: 'uppercase' }}>
                {pushingTodos === lastMeeting.id ? <Loader size={11} /> : <Check size={11} />}
                {pushingTodos === lastMeeting.id ? 'Adding…' : `Add ${lastMeeting.action_items.length} to Todos`}
              </button>
            )}
          </div>
        )}

        {tab === 'meetings' && (
          <>
            <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
              <div style={{ flex: 1, position: 'relative' }}>
                <Search size={11} style={{ position: 'absolute', left: 9, top: 9, color: MUTED }} />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && doSearch()}
                  placeholder="Search meetings…"
                  style={{ ...inputStyle, paddingLeft: 26 }}
                />
              </div>
              <button onClick={doSearch} style={{ padding: '0 12px', background: 'rgba(0,183,255,0.12)', border: '1px solid rgba(0,183,255,0.3)', borderRadius: 8, color: ACCENT, cursor: 'pointer', fontSize: 10, textTransform: 'uppercase' }}>
                Go
              </button>
            </div>

            {loading && <div style={{ color: MUTED, fontSize: 11, textAlign: 'center', padding: 16 }}>Loading…</div>}

            {!loading && meetings.length === 0 && (
              <div style={{ color: MUTED, fontSize: 11, textAlign: 'center', padding: 20 }}>
                No meetings yet — record one or paste a transcript.
              </div>
            )}

            {meetings.map((m) => (
              <div key={m.id} style={{ padding: '10px', marginBottom: 6, background: 'rgba(0,183,255,0.03)', border: '1px solid rgba(0,183,255,0.12)', borderRadius: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: TEXT, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{m.title}</span>
                  <span style={{ fontSize: 9, color: MUTED }}>{fmtDate(m.date)}</span>
                </div>
                <div style={{ fontSize: 11, color: MUTED, marginTop: 4, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                  {m.summary || '—'}
                </div>
                {m.action_items?.length > 0 && (
                  <button onClick={() => pushTodos(m.id)} disabled={pushingTodos === m.id} style={{ marginTop: 8, display: 'inline-flex', alignItems: 'center', gap: 6, padding: '5px 10px', background: 'rgba(0,183,255,0.12)', border: '1px solid rgba(0,183,255,0.3)', borderRadius: 8, color: ACCENT, cursor: 'pointer', fontSize: 10, textTransform: 'uppercase' }}>
                    {pushingTodos === m.id ? <Loader size={11} /> : <Check size={11} />}
                    {pushingTodos === m.id ? 'Adding…' : `Todos (${m.action_items.length})`}
                  </button>
                )}
              </div>
            ))}
          </>
        )}

        {tab === 'actions' && (
          <>
            {actionItems.length === 0 && !loading && (
              <div style={{ color: MUTED, fontSize: 11, textAlign: 'center', padding: 20 }}>
                No action items yet, Boss. 🎉
              </div>
            )}
            {actionItems.map((it, i) => (
              <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', padding: '9px 10px', marginBottom: 6, background: 'rgba(251,146,60,0.05)', border: '1px solid rgba(251,146,60,0.2)', borderRadius: 10 }}>
                <CheckCircle2 size={12} style={{ color: '#fb923c', flexShrink: 0, marginTop: 2 }} />
                <div>
                  <div style={{ fontSize: 12, color: TEXT }}>{it.text}</div>
                  <div style={{ fontSize: 9, color: MUTED, marginTop: 2 }}>
                    {it.owner ? `${it.owner} · ` : ''}{it.meeting_title} · {fmtDate(it.meeting_date)}
                  </div>
                </div>
              </div>
            ))}
          </>
        )}

        {tab === 'new' && (
          <>
            <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, padding: '16px 10px', marginBottom: 10, border: '1px dashed rgba(0,183,255,0.35)', borderRadius: 10, cursor: 'pointer', color: ACCENT, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              <Upload size={13} />
              Upload recording (mp3/wav/ogg/webm)
              <input type="file" accept="audio/*" onChange={onFile} style={{ display: 'none' }} />
            </label>

            <div style={{ fontSize: 10, color: MUTED, textAlign: 'center', marginBottom: 8 }}>— or paste a transcript —</div>

            <textarea
              value={pasteText}
              onChange={(e) => setPasteText(e.target.value)}
              placeholder="Paste meeting transcript here…"
              rows={6}
              style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit' }}
            />
            <button
              onClick={runProcess}
              disabled={!pasteText.trim() || processing}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                padding: '10px 0', background: pasteText.trim() && !processing ? ACCENT : 'rgba(0,183,255,0.15)',
                border: 'none', borderRadius: 8, color: '#001018', fontWeight: 700, fontSize: 11,
                cursor: pasteText.trim() && !processing ? 'pointer' : 'not-allowed',
                textTransform: 'uppercase', letterSpacing: '0.1em',
              }}
            >
              {processing ? <Loader size={12} /> : <FileText size={12} />}
              {processing ? 'Processing…' : 'Extract Summary & Action Items'}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
