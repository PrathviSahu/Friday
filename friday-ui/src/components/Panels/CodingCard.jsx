import { useState } from 'react';
import { Code2, X, Bug, FileCode2, FlaskConical, BookOpen, RefreshCw, AlertTriangle, Loader } from 'lucide-react';
import { API_BASE_URL } from '../../api/config.js';

const CARD_STYLE = {
  position: 'fixed',
  top: 80,
  left: 220,
  zIndex: 50,
  width: 420,
  maxHeight: '74vh',
  display: 'flex',
  flexDirection: 'column',
  background: 'rgba(2, 6, 20, 0.94)',
  border: '1px solid rgba(34, 211, 238, 0.25)',
  borderRadius: 16,
  backdropFilter: 'blur(18px)',
  boxShadow: '0 24px 64px rgba(0,0,0,0.55), 0 0 24px rgba(34,211,238,0.08)',
  overflow: 'hidden',
  fontFamily: 'Inter, system-ui, sans-serif',
};

const ACCENT = '#22D3EE';
const TEXT = '#f1f5f9';
const MUTED = 'rgba(223,250,255,0.55)';

const ACTIONS = [
  { key: 'review', label: 'Review', icon: Code2 },
  { key: 'bugs', label: 'Find Bugs', icon: Bug },
  { key: 'explain', label: 'Explain', icon: FileCode2 },
  { key: 'tests', label: 'Tests', icon: FlaskConical },
  { key: 'docs', label: 'Docs', icon: BookOpen },
  { key: 'refactor', label: 'Refactor', icon: RefreshCw },
];

export default function CodingCard() {
  const [open, setOpen] = useState(true);
  const [code, setCode] = useState('');
  const [language, setLanguage] = useState('');
  const [result, setResult] = useState('');
  const [working, setWorking] = useState(false);
  const [error, setError] = useState('');
  const [lastAction, setLastAction] = useState('');

  const run = async (action) => {
    if (!code.trim()) { setError('Paste some code first, Boss.'); return; }
    setWorking(true);
    setError('');
    setResult('');
    setLastAction(action);
    try {
      const res = await fetch(`${API_BASE_URL}/api/coding/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, language }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setResult(data.result || '');
    } catch (err) {
      setError(err.message || 'Coding AI failed.');
    } finally {
      setWorking(false);
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        style={{
          position: 'fixed', top: 80, left: 220, zIndex: 50,
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '10px 14px', borderRadius: 999,
          background: 'rgba(2, 6, 20, 0.9)', border: '1px solid rgba(34,211,238,0.3)',
          color: ACCENT, cursor: 'pointer', fontFamily: 'Inter, system-ui, sans-serif',
          fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase',
        }}
      >
        <Code2 size={13} />
        Coding AI
      </button>
    );
  }

  return (
    <div style={CARD_STYLE}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px', borderBottom: '1px solid rgba(34,211,238,0.15)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: ACCENT }}>
          <Code2 size={14} />
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.14em' }}>CODING AI</span>
          <span style={{ fontSize: 9, color: MUTED }}>review · bugs · docs · tests</span>
        </div>
        <button onClick={() => setOpen(false)} style={{ background: 'none', border: 'none', color: MUTED, cursor: 'pointer', padding: 2 }}>
          <X size={14} />
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>
        {error && (
          <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 8, padding: 10, marginBottom: 10, fontSize: 11, color: '#fca5a5' }}>
            <AlertTriangle size={12} style={{ flexShrink: 0, marginTop: 1 }} />
            <span>{error}</span>
          </div>
        )}

        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="Paste your code here…"
          rows={9}
          spellCheck={false}
          style={{
            width: '100%', padding: 10, marginBottom: 8, boxSizing: 'border-box',
            background: 'rgba(34,211,238,0.04)', border: '1px solid rgba(34,211,238,0.2)',
            borderRadius: 8, color: TEXT, fontSize: 11.5, outline: 'none',
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', resize: 'vertical',
          }}
        />
        <input
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          placeholder="Language (optional, e.g. python)"
          style={{
            width: '100%', padding: '8px 10px', marginBottom: 10, boxSizing: 'border-box',
            background: 'rgba(34,211,238,0.04)', border: '1px solid rgba(34,211,238,0.2)',
            borderRadius: 8, color: TEXT, fontSize: 12, outline: 'none', fontFamily: 'inherit',
          }}
        />

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6, marginBottom: 10 }}>
          {ACTIONS.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => run(key)}
              disabled={working}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5,
                padding: '8px 0', background: lastAction === key ? 'rgba(34,211,238,0.2)' : 'rgba(34,211,238,0.08)',
                border: `1px solid ${lastAction === key ? 'rgba(34,211,238,0.5)' : 'rgba(34,211,238,0.2)'}`,
                borderRadius: 8, color: ACCENT, cursor: working ? 'wait' : 'pointer',
                fontSize: 10, textTransform: 'uppercase',
              }}
            >
              <Icon size={11} />
              {label}
            </button>
          ))}
        </div>

        {working && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, color: MUTED, fontSize: 11, padding: 10 }}>
            <Loader size={13} /> FRIDAY is analyzing your code…
          </div>
        )}

        {result && (
          <div style={{ background: 'rgba(34,211,238,0.05)', border: '1px solid rgba(34,211,238,0.2)', borderRadius: 10, padding: 12, fontSize: 12, color: TEXT, whiteSpace: 'pre-wrap', lineHeight: 1.65 }}>
            {result}
          </div>
        )}
      </div>
    </div>
  );
}
