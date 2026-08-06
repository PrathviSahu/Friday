import { useState, useEffect, useCallback } from 'react';
import { Mail, Search, Send, Inbox, X, Check, AlertTriangle, Loader } from 'lucide-react';
import { fetchUnread, searchEmails, createEmailDraft, approveAndSendEmail, cancelEmailDraft } from '../../api/email';

const CARD_STYLE = {
  position: 'fixed',
  top: 200,
  right: 40,
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

export default function EmailCard() {
  const [open, setOpen] = useState(true);
  const [tab, setTab] = useState('inbox');
  const [unread, setUnread] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [searching, setSearching] = useState(false);

  // Compose state
  const [to, setTo] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [draft, setDraft] = useState(null);       // { draft_id, preview }
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(null);

  const loadInbox = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [emails, sum] = await Promise.all([fetchUnread(15), fetchEmailSummary()]);
      setUnread(emails);
      setSummary(sum);
    } catch (err) {
      setError(err.message || 'Could not load email.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) loadInbox();
  }, [open, loadInbox]);

  const doSearch = async () => {
    if (!query.trim()) { loadInbox(); return; }
    setSearching(true);
    setError('');
    try {
      const results = await searchEmails(query.trim());
      setUnread(results);
    } catch (err) {
      setError(err.message || 'Search failed.');
    } finally {
      setSearching(false);
    }
  };

  const previewDraft = async () => {
    setError('');
    setSent(null);
    try {
      const res = await createEmailDraft({ to, subject, body });
      setDraft({ draft_id: res.draft_id, preview: res.preview });
    } catch (err) {
      setError(err.message || 'Could not create draft.');
    }
  };

  const confirmSend = async () => {
    if (!draft) return;
    setSending(true);
    setError('');
    try {
      const res = await approveAndSendEmail(draft.draft_id);
      setSent(`Sent to ${res.to}`);
      setDraft(null);
      setTo(''); setSubject(''); setBody('');
      setTimeout(() => setSent(null), 5000);
    } catch (err) {
      setError(err.message || 'Send failed.');
    } finally {
      setSending(false);
    }
  };

  const cancelPreview = async () => {
    if (draft) await cancelEmailDraft(draft.draft_id).catch(() => {});
    setDraft(null);
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        style={{
          position: 'fixed', top: 200, right: 40, zIndex: 50,
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '10px 14px', borderRadius: 999,
          background: 'rgba(15, 23, 42, 0.9)', border: `1px solid rgba(100,116,139,0.3)`,
          color: ACCENT, cursor: 'pointer', fontFamily: 'Inter, system-ui, sans-serif',
          fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase',
        }}
      >
        <Mail size={13} />
        Email
        {summary?.unread_count > 0 && (
          <span style={{ background: '#0ea5e9', color: '#1e293b', borderRadius: 99, padding: '1px 7px', fontSize: 10, fontWeight: 700 }}>
            {summary.unread_count}
          </span>
        )}
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
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px', borderBottom: '1px solid rgba(100, 116, 139,0.15)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: ACCENT }}>
          <Mail size={14} />
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.14em' }}>EMAIL</span>
          {summary?.unread_count > 0 && (
            <span style={{ background: 'rgba(14,165,233,0.2)', color: '#7dd3fc', borderRadius: 99, padding: '1px 7px', fontSize: 10, fontWeight: 700 }}>
              {summary.unread_count} unread
            </span>
          )}
        </div>
        <button onClick={() => setOpen(false)} style={{ background: 'none', border: 'none', color: MUTED, cursor: 'pointer', padding: 2 }}>
          <X size={14} />
        </button>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, padding: '8px 14px 0' }}>
        {[
          { id: 'inbox', label: 'Inbox', icon: Inbox },
          { id: 'compose', label: 'Compose', icon: Send },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => { setTab(id); setError(''); setSent(null); }}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px',
              background: tab === id ? 'rgba(100,116,139,0.12)' : 'transparent',
              border: `1px solid ${tab === id ? 'rgba(100,116,139,0.4)' : 'rgba(100,116,139,0.15)'}`,
              borderRadius: 8, color: tab === id ? ACCENT : MUTED, cursor: 'pointer',
              fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase',
            }}
          >
            <Icon size={11} />
            {label}
          </button>
        ))}
      </div>

      {/* Body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>
        {error && (
          <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 8, padding: 10, marginBottom: 10, fontSize: 11, color: '#fca5a5' }}>
            <AlertTriangle size={12} style={{ flexShrink: 0, marginTop: 1 }} />
            <span>{error}</span>
          </div>
        )}

        {sent && (
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', background: 'rgba(34,197,94,0.12)', border: '1px solid rgba(34,197,94,0.35)', borderRadius: 8, padding: 10, marginBottom: 10, fontSize: 11, color: '#86efac' }}>
            <Check size={12} />
            <span>{sent}</span>
          </div>
        )}

        {tab === 'inbox' && (
          <>
            <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
              <div style={{ flex: 1, position: 'relative' }}>
                <Search size={11} style={{ position: 'absolute', left: 9, top: 9, color: MUTED }} />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && doSearch()}
                  placeholder="Search sender or subject…"
                  style={{ ...inputStyle, paddingLeft: 26 }}
                />
              </div>
              <button onClick={doSearch} style={{ padding: '0 12px', background: 'rgba(100, 116, 139, 0.1)', border: '1px solid rgba(100, 116, 139, 0.25)', borderRadius: 8, color: ACCENT, cursor: 'pointer', fontSize: 10, textTransform: 'uppercase' }}>
                {searching ? <Loader size={11} /> : 'Go'}
              </button>
            </div>

            {loading && <div style={{ color: MUTED, fontSize: 11, textAlign: 'center', padding: 16 }}>Loading inbox…</div>}

            {!loading && unread.length === 0 && (
              <div style={{ color: MUTED, fontSize: 11, textAlign: 'center', padding: 20 }}>
                {query ? `No matches for "${query}".` : 'Inbox zero — all caught up, Boss.'}
              </div>
            )}

            {unread.map((m, i) => (
              <div key={i} style={{ padding: '9px 10px', marginBottom: 6, background: m.priority ? 'rgba(251,146,60,0.07)' : 'rgba(100,116,139,0.03)', border: `1px solid ${m.priority ? 'rgba(251,146,60,0.25)' : 'rgba(100,116,139,0.12)'}`, borderRadius: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: m.priority ? '#fdba74' : TEXT, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {m.from_name || m.from}
                  </span>
                  {m.priority && <span style={{ fontSize: 8, color: '#fb923c', border: '1px solid rgba(251,146,60,0.4)', borderRadius: 99, padding: '1px 6px', letterSpacing: '0.08em' }}>PRIORITY</span>}
                </div>
                <div style={{ fontSize: 12, color: TEXT, marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{m.subject}</div>
                <div style={{ fontSize: 10, color: MUTED, marginTop: 3, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                  {m.snippet || '—'}
                </div>
              </div>
            ))}
          </>
        )}

        {tab === 'compose' && (
          <>
            {draft ? (
              <div>
                <div style={{ fontSize: 10, color: MUTED, letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 8 }}>
                  Preview — confirm to send
                </div>
                <div style={{ background: 'rgba(100, 116, 139, 0.04)', border: '1px solid rgba(100, 116, 139, 0.15)', borderRadius: 10, padding: 12, fontSize: 12, color: TEXT }}>
                  <div style={{ marginBottom: 6 }}><b style={{ color: ACCENT }}>To:</b> {draft.preview.to}</div>
                  <div style={{ marginBottom: 6 }}><b style={{ color: ACCENT }}>Subject:</b> {draft.preview.subject || '(none)'}</div>
                  <div style={{ whiteSpace: 'pre-wrap', borderTop: '1px solid rgba(100, 116, 139,0.15)', paddingTop: 8, color: MUTED }}>{draft.preview.body}</div>
                </div>
                <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                  <button onClick={confirmSend} disabled={sending} style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, padding: '9px 0', background: ACCENT, border: 'none', borderRadius: 8, color: '#1e293b', fontWeight: 700, fontSize: 11, cursor: sending ? 'wait' : 'pointer', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                    {sending ? <Loader size={12} /> : <Check size={12} />}
                    {sending ? 'Sending…' : 'Confirm Send'}
                  </button>
                  <button onClick={cancelPreview} disabled={sending} style={{ padding: '0 14px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 8, color: MUTED, cursor: 'pointer', fontSize: 11 }}>
                    Edit
                  </button>
                </div>
              </div>
            ) : (
              <>
                <input value={to} onChange={(e) => setTo(e.target.value)} placeholder="To (email address)" style={inputStyle} />
                <input value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Subject" style={inputStyle} />
                <textarea value={body} onChange={(e) => setBody(e.target.value)} placeholder="Message…" rows={6} style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit' }} />
                <button onClick={previewDraft} disabled={!to.trim() || !body.trim()} style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, padding: '10px 0', background: to.trim() && body.trim() ? ACCENT : 'rgba(100,116,139,0.15)', border: 'none', borderRadius: 8, color: '#1e293b', fontWeight: 700, fontSize: 11, cursor: to.trim() && body.trim() ? 'pointer' : 'not-allowed', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                  <Send size={12} />
                  Preview &amp; Ask to Send
                </button>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
