import { useState, useEffect, useCallback } from 'react';
import { CalendarDays, Search, Plus, X, Check, AlertTriangle, Loader, MapPin } from 'lucide-react';
import {
  fetchTodayEvents, fetchUpcomingEvents, searchCalendarEvents,
  createEventDraft, approveAndCreateEvent, cancelEventDraft, fetchCalendarStatus,
} from '../../api/calendar';

const CARD_STYLE = {
  position: 'fixed',
  top: 200,
  left: 40,
  zIndex: 50,
  width: 380,
  maxHeight: '72vh',
  display: 'flex',
  flexDirection: 'column',
  background: 'rgba(15, 23, 42, 0.92)',
  border: '1px solid rgba(100, 116, 139, 0.2)',
  borderRadius: 16,
  backdropFilter: 'blur(18px)',
  boxShadow: '0 24px 64px rgba(0,0,0,0.4)',
  overflow: 'hidden',
  fontFamily: 'Inter, system-ui, sans-serif',
};

const ACCENT = '#60a5fa';
const TEXT = '#f1f5f9';
const MUTED = 'rgba(223,250,255,0.55)';

const fmtTime = (iso) => {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString('en-IN', {
    weekday: 'short', day: 'numeric', month: 'short',
    hour: 'numeric', minute: '2-digit', hour12: true,
  });
};

export default function CalendarCard() {
  const [open, setOpen] = useState(true);
  const [tab, setTab] = useState('today');
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');

  // Create-event state (approval-first)
  const [summary, setSummary] = useState('');
  const [date, setDate] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [description, setDescription] = useState('');
  const [draft, setDraft] = useState(null);
  const [creating, setCreating] = useState(false);
  const [created, setCreated] = useState(null);

  const load = useCallback(async (which) => {
    setLoading(true);
    setError('');
    try {
      if (which === 'today') setEvents(await fetchTodayEvents());
      else if (which === 'upcoming') setEvents(await fetchUpcomingEvents(7));
    } catch (err) {
      setError(err.message || 'Could not load calendar.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    fetchCalendarStatus().then(setStatus).catch(() => {});
    load(tab === 'today' ? 'today' : 'upcoming');
  }, [open, tab, load]);

  const doSearch = async () => {
    if (!query.trim()) { load(tab); return; }
    setLoading(true);
    setError('');
    try {
      setEvents(await searchCalendarEvents(query.trim()));
    } catch (err) {
      setError(err.message || 'Search failed.');
    } finally {
      setLoading(false);
    }
  };

  const previewDraft = async () => {
    setError('');
    setCreated(null);
    try {
      const startIso = new Date(`${date}T${startTime || '09:00'}`).toISOString();
      const endIso = endTime ? new Date(`${date}T${endTime}`).toISOString() : '';
      const res = await createEventDraft({ summary, start: startIso, end: endIso, description });
      setDraft({ draft_id: res.draft_id, preview: res.preview });
    } catch (err) {
      setError(err.message || 'Could not create draft.');
    }
  };

  const confirmCreate = async () => {
    if (!draft) return;
    setCreating(true);
    setError('');
    try {
      const res = await approveAndCreateEvent(draft.draft_id);
      setCreated(`Created: ${res.summary} · ${fmtTime(res.start)}`);
      setDraft(null);
      setSummary(''); setDate(''); setStartTime(''); setEndTime(''); setDescription('');
      setTimeout(() => setCreated(null), 6000);
      load('today');
    } catch (err) {
      setError(err.message || 'Create failed.');
    } finally {
      setCreating(false);
    }
  };

  const cancelPreview = async () => {
    if (draft) await cancelEventDraft(draft.draft_id).catch(() => {});
    setDraft(null);
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        style={{
          position: 'fixed', top: 200, left: 40, zIndex: 50,
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '10px 14px', borderRadius: 999,
          background: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(100, 116, 139, 0.25)',
          color: ACCENT, cursor: 'pointer', fontFamily: 'Inter, system-ui, sans-serif',
          fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase',
        }}
      >
        <CalendarDays size={13} />
        Calendar
        {status?.connected && <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#22ff99', boxShadow: '0 0 6px #22ff99' }} />}
      </button>
    );
  }

  const inputStyle = {
    width: '100%', padding: '8px 10px', marginBottom: 8,
    background: 'rgba(100, 116, 139, 0.06)', border: '1px solid rgba(100, 116, 139, 0.15)',
    borderRadius: 8, color: TEXT, fontSize: 12, outline: 'none',
    boxSizing: 'border-box', fontFamily: 'inherit',
  };

  return (
    <div style={CARD_STYLE}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px', borderBottom: '1px solid rgba(100, 116, 139,0.15)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: ACCENT }}>
          <CalendarDays size={14} />
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.14em' }}>CALENDAR</span>
          {status?.connected
            ? <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#22ff99', boxShadow: '0 0 6px #22ff99' }} />
            : <span style={{ fontSize: 9, color: '#f59e0b' }}>not connected</span>}
        </div>
        <button onClick={() => setOpen(false)} style={{ background: 'none', border: 'none', color: MUTED, cursor: 'pointer', padding: 2 }}>
          <X size={14} />
        </button>
      </div>

      <div style={{ display: 'flex', gap: 4, padding: '8px 14px 0' }}>
        {[
          { id: 'today', label: 'Today', icon: CalendarDays },
          { id: 'upcoming', label: 'Upcoming', icon: CalendarDays },
          { id: 'new', label: 'New Event', icon: Plus },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => { setTab(id); setError(''); setCreated(null); }}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px',
              background: tab === id ? 'rgba(100,116,139,0.12)' : 'transparent',
              border: `1px solid ${tab === id ? 'rgba(100,116,139,0.4)' : 'rgba(100,116,139,0.15)'}`,
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
        {created && (
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', background: 'rgba(34,197,94,0.12)', border: '1px solid rgba(34,197,94,0.35)', borderRadius: 8, padding: 10, marginBottom: 10, fontSize: 11, color: '#86efac' }}>
            <Check size={12} />
            <span>{created}</span>
          </div>
        )}

        {(tab === 'today' || tab === 'upcoming') && (
          <>
            <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
              <div style={{ flex: 1, position: 'relative' }}>
                <Search size={11} style={{ position: 'absolute', left: 9, top: 9, color: MUTED }} />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && doSearch()}
                  placeholder="Search events…"
                  style={{ ...inputStyle, paddingLeft: 26 }}
                />
              </div>
              <button onClick={doSearch} style={{ padding: '0 12px', background: 'rgba(100, 116, 139, 0.1)', border: '1px solid rgba(100, 116, 139, 0.25)', borderRadius: 8, color: ACCENT, cursor: 'pointer', fontSize: 10, textTransform: 'uppercase' }}>
                Go
              </button>
            </div>

            {loading && <div style={{ color: MUTED, fontSize: 11, textAlign: 'center', padding: 16 }}>Loading calendar…</div>}

            {!loading && events.length === 0 && (
              <div style={{ color: MUTED, fontSize: 11, textAlign: 'center', padding: 20 }}>
                {query ? `No events match "${query}".` : tab === 'today' ? 'Nothing scheduled today.' : 'Nothing coming up.'}
              </div>
            )}

            {events.map((e, i) => (
              <div key={e.id || i} style={{ padding: '9px 10px', marginBottom: 6, background: 'rgba(100, 116, 139, 0.04)', border: '1px solid rgba(100, 116, 139, 0.1)', borderRadius: 10 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: TEXT, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{e.summary}</div>
                <div style={{ fontSize: 10, color: ACCENT, marginTop: 2 }}>{fmtTime(e.start)}{e.end ? ` → ${fmtTime(e.end)}` : ''}</div>
                {e.location && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: MUTED, marginTop: 2 }}>
                    <MapPin size={9} /> {e.location}
                  </div>
                )}
              </div>
            ))}
          </>
        )}

        {tab === 'new' && (
          <>
            {draft ? (
              <div>
                <div style={{ fontSize: 10, color: MUTED, letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 8 }}>
                  Preview — confirm to create
                </div>
                <div style={{ background: 'rgba(100, 116, 139, 0.04)', border: '1px solid rgba(100, 116, 139, 0.15)', borderRadius: 10, padding: 12, fontSize: 12, color: TEXT }}>
                  <div style={{ marginBottom: 6 }}><b style={{ color: ACCENT }}>Event:</b> {draft.preview.summary}</div>
                  <div style={{ marginBottom: 6 }}><b style={{ color: ACCENT }}>When:</b> {fmtTime(draft.preview.start)} → {fmtTime(draft.preview.end)}</div>
                  {draft.preview.description && (
                    <div style={{ borderTop: '1px solid rgba(100, 116, 139,0.15)', paddingTop: 8, color: MUTED, whiteSpace: 'pre-wrap' }}>{draft.preview.description}</div>
                  )}
                </div>
                <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                  <button onClick={confirmCreate} disabled={creating} style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, padding: '9px 0', background: ACCENT, border: 'none', borderRadius: 8, color: '#1e293b', fontWeight: 700, fontSize: 11, cursor: creating ? 'wait' : 'pointer', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                    {creating ? <Loader size={12} /> : <Check size={12} />}
                    {creating ? 'Creating…' : 'Confirm Create'}
                  </button>
                  <button onClick={cancelPreview} disabled={creating} style={{ padding: '0 14px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 8, color: MUTED, cursor: 'pointer', fontSize: 11 }}>
                    Edit
                  </button>
                </div>
              </div>
            ) : (
              <>
                <input value={summary} onChange={(e) => setSummary(e.target.value)} placeholder="Event title" style={inputStyle} />
                <input type="date" value={date} onChange={(e) => setDate(e.target.value)} style={{ ...inputStyle, colorScheme: 'dark' }} />
                <div style={{ display: 'flex', gap: 8 }}>
                  <input type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)} style={{ ...inputStyle, colorScheme: 'dark' }} />
                  <input type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} style={{ ...inputStyle, colorScheme: 'dark' }} />
                </div>
                <textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Details (optional)…" rows={3} style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit' }} />
                <button onClick={previewDraft} disabled={!summary.trim() || !date} style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, padding: '10px 0', background: summary.trim() && date ? ACCENT : 'rgba(100,116,139,0.15)', border: 'none', borderRadius: 8, color: '#1e293b', fontWeight: 700, fontSize: 11, cursor: summary.trim() && date ? 'pointer' : 'not-allowed', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                  <Plus size={12} />
                  Preview &amp; Ask to Create
                </button>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
