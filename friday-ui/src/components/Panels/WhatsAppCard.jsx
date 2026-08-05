import { useState, useEffect, useCallback, useRef } from 'react';
import { MessageCircle, Send, RefreshCw, X, Check, AlertTriangle, Loader, MessageSquareText } from 'lucide-react';
import {
  fetchWhatsAppStatus, fetchWhatsAppQr, fetchChats,
  createWhatsAppDraft, approveAndSendWhatsApp, cancelWhatsAppDraft,
} from '../../api/whatsapp';

const CARD_STYLE = {
  position: 'fixed',
  top: 200,
  right: 220,
  zIndex: 50,
  width: 380,
  maxHeight: '72vh',
  display: 'flex',
  flexDirection: 'column',
  background: 'rgba(2, 6, 20, 0.92)',
  border: '1px solid rgba(37, 211, 102, 0.25)',
  borderRadius: 16,
  backdropFilter: 'blur(18px)',
  boxShadow: '0 24px 64px rgba(0,0,0,0.55), 0 0 24px rgba(37,211,102,0.08)',
  overflow: 'hidden',
  fontFamily: 'Inter, system-ui, sans-serif',
};

const ACCENT = '#25D366';
const TEXT = '#f1f5f9';
const MUTED = 'rgba(223,250,255,0.55)';

export default function WhatsAppCard() {
  const [open, setOpen] = useState(true);
  const [tab, setTab] = useState('chats');
  const [status, setStatus] = useState(null);
  const [chats, setChats] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [qr, setQr] = useState('');

  // Compose state (approval-first)
  const [phone, setPhone] = useState('');
  const [message, setMessage] = useState('');
  const [draft, setDraft] = useState(null);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(null);

  const qrTimer = useRef(null);

  const loadStatus = useCallback(async () => {
    try {
      const s = await fetchWhatsAppStatus();
      setStatus(s);
      return s;
    } catch (err) {
      setStatus({ enabled: false, error: err.message });
      return null;
    }
  }, []);

  const loadChats = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setChats(await fetchChats(20));
    } catch (err) {
      setError(err.message || 'Could not load chats.');
    } finally {
      setLoading(false);
    }
  }, []);

  // Poll the QR while pairing
  const pollQr = useCallback(async () => {
    if (!status?.enabled) return;
    try {
      const q = await fetchWhatsAppQr();
      if (q.status === 'pairing' && q.qr_data_url) setQr(q.qr_data_url);
      else if (q.status === 'connected') { setQr(''); setStatus((s) => ({ ...s, connected: true })); }
    } catch (_) { /* not ready yet */ }
  }, [status?.enabled]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  useEffect(() => {
    if (!open) return;
    if (status?.connected) {
      loadChats();
    } else if (status?.enabled) {
      // start pairing → poll QR every 3s
      setTab('chats');
      pollQr();
      qrTimer.current = setInterval(pollQr, 3000);
    }
    return () => { if (qrTimer.current) clearInterval(qrTimer.current); };
  }, [open, status?.connected, status?.enabled, loadChats, pollQr]);

  const previewDraft = async () => {
    setError('');
    setSent(null);
    try {
      const res = await createWhatsAppDraft({ phone, message });
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
      const res = await approveAndSendWhatsApp(draft.draft_id);
      setSent(`Sent to +${res.phone}`);
      setDraft(null);
      setPhone(''); setMessage('');
      setTimeout(() => setSent(null), 5000);
    } catch (err) {
      setError(err.message || 'Send failed.');
    } finally {
      setSending(false);
    }
  };

  const cancelPreview = async () => {
    if (draft) await cancelWhatsAppDraft(draft.draft_id).catch(() => {});
    setDraft(null);
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        style={{
          position: 'fixed', top: 200, right: 220, zIndex: 50,
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '10px 14px', borderRadius: 999,
          background: 'rgba(2, 6, 20, 0.9)', border: '1px solid rgba(37,211,102,0.3)',
          color: ACCENT, cursor: 'pointer', fontFamily: 'Inter, system-ui, sans-serif',
          fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase',
        }}
      >
        <MessageCircle size={13} />
        WhatsApp
        {status?.connected && <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#22ff99', boxShadow: '0 0 6px #22ff99' }} />}
      </button>
    );
  }

  const inputStyle = {
    width: '100%', padding: '8px 10px', marginBottom: 8,
    background: 'rgba(37,211,102,0.06)', border: '1px solid rgba(37,211,102,0.2)',
    borderRadius: 8, color: TEXT, fontSize: 12, outline: 'none',
    boxSizing: 'border-box', fontFamily: 'inherit',
  };

  return (
    <div style={CARD_STYLE}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px', borderBottom: '1px solid rgba(37,211,102,0.15)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: ACCENT }}>
          <MessageCircle size={14} />
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.14em' }}>WHATSAPP</span>
          {status?.connected
            ? <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#22ff99', boxShadow: '0 0 6px #22ff99' }} />
            : <span style={{ fontSize: 9, color: '#f59e0b' }}>{status?.enabled ? 'pairing…' : 'disabled'}</span>}
        </div>
        <button onClick={() => setOpen(false)} style={{ background: 'none', border: 'none', color: MUTED, cursor: 'pointer', padding: 2 }}>
          <X size={14} />
        </button>
      </div>

      {/* Pairing panel */}
      {status?.enabled && !status?.connected && (
        <div style={{ padding: '12px 14px', borderBottom: '1px solid rgba(37,211,102,0.12)', textAlign: 'center' }}>
          {qr ? (
            <>
              <img src={qr} alt="WhatsApp pairing QR" style={{ width: 170, height: 170, borderRadius: 8, border: '1px solid rgba(37,211,102,0.3)' }} />
              <div style={{ fontSize: 10, color: MUTED, marginTop: 8, letterSpacing: '0.06em' }}>
                Scan with WhatsApp → Linked Devices → Link a Device
              </div>
            </>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, fontSize: 11, color: MUTED, padding: '12px 0' }}>
              <Loader size={13} /> Waiting for pairing QR…
            </div>
          )}
        </div>
      )}

      {!status?.enabled && (
        <div style={{ padding: '12px 14px', borderBottom: '1px solid rgba(37,211,102,0.12)', fontSize: 11, color: MUTED, lineHeight: 1.6 }}>
          WhatsApp driver is <b style={{ color: '#f59e0b' }}>disabled</b> (experimental — no official free API).
          To enable: set <code style={{ color: ACCENT }}>FRIDAY_WHATSAPP_ENABLED=1</code> in backend/.env
          and install Playwright Chromium. Sending always asks for confirmation.
        </div>
      )}

      <div style={{ display: 'flex', gap: 4, padding: '8px 14px 0' }}>
        {[
          { id: 'chats', label: 'Chats', icon: MessageSquareText },
          { id: 'compose', label: 'New Message', icon: Send },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => { setTab(id); setError(''); setSent(null); }}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px',
              background: tab === id ? 'rgba(37,211,102,0.12)' : 'transparent',
              border: `1px solid ${tab === id ? 'rgba(37,211,102,0.4)' : 'rgba(37,211,102,0.15)'}`,
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

        {sent && (
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', background: 'rgba(34,197,94,0.12)', border: '1px solid rgba(34,197,94,0.35)', borderRadius: 8, padding: 10, marginBottom: 10, fontSize: 11, color: '#86efac' }}>
            <Check size={12} />
            <span>{sent}</span>
          </div>
        )}

        {tab === 'chats' && (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontSize: 10, color: MUTED, letterSpacing: '0.08em' }}>Unread conversations</span>
              <button onClick={() => { loadChats(); loadStatus(); }} style={{ display: 'flex', alignItems: 'center', gap: 4, background: 'none', border: 'none', color: ACCENT, cursor: 'pointer', fontSize: 10, textTransform: 'uppercase' }}>
                <RefreshCw size={10} /> Refresh
              </button>
            </div>

            {loading && <div style={{ color: MUTED, fontSize: 11, textAlign: 'center', padding: 16 }}>Loading chats…</div>}

            {!loading && !status?.connected && (
              <div style={{ color: MUTED, fontSize: 11, textAlign: 'center', padding: 20 }}>
                Connect by scanning the QR above, Boss.
              </div>
            )}

            {!loading && status?.connected && chats.length === 0 && (
              <div style={{ color: MUTED, fontSize: 11, textAlign: 'center', padding: 20 }}>
                No chats with unread messages.
              </div>
            )}

            {chats.map((c, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, padding: '9px 10px', marginBottom: 6, background: 'rgba(37,211,102,0.03)', border: '1px solid rgba(37,211,102,0.12)', borderRadius: 10 }}>
                <span style={{ fontSize: 12, color: TEXT, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.name}</span>
                {c.unread > 0 && (
                  <span style={{ background: '#25D366', color: '#1e293b', borderRadius: 99, padding: '1px 8px', fontSize: 11, fontWeight: 700, flexShrink: 0 }}>{c.unread}</span>
                )}
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
                <div style={{ background: 'rgba(37,211,102,0.04)', border: '1px solid rgba(37,211,102,0.2)', borderRadius: 10, padding: 12, fontSize: 12, color: TEXT }}>
                  <div style={{ marginBottom: 6 }}><b style={{ color: ACCENT }}>To:</b> +{draft.preview.phone}</div>
                  <div style={{ borderTop: '1px solid rgba(37,211,102,0.15)', paddingTop: 8, color: MUTED, whiteSpace: 'pre-wrap' }}>{draft.preview.message}</div>
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
                <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Phone with country code, e.g. 919876543210" style={inputStyle} />
                <textarea value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Message…" rows={5} style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit' }} />
                <button onClick={previewDraft} disabled={!phone.trim() || !message.trim()} style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, padding: '10px 0', background: phone.trim() && message.trim() ? ACCENT : 'rgba(37,211,102,0.15)', border: 'none', borderRadius: 8, color: '#1e293b', fontWeight: 700, fontSize: 11, cursor: phone.trim() && message.trim() ? 'pointer' : 'not-allowed', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
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
