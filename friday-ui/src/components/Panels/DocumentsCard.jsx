import { useState, useEffect, useCallback } from 'react';
import { FileText, Upload, Search, X, Trash2, Sparkles, AlertTriangle, Loader } from 'lucide-react';
import {
  uploadDocument, fetchDocuments, searchDocuments,
  askDocument, summarizeDocument, deleteDocument,
} from '../../api/documents';

const CARD_STYLE = {
  position: 'fixed',
  top: 200,
  left: 220,
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

const ACCENT = '#A78BFA';
const TEXT = '#f1f5f9';
const MUTED = 'rgba(223,250,255,0.55)';

export default function DocumentsCard() {
  const [open, setOpen] = useState(true);
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const [query, setQuery] = useState('');

  // Ask state
  const [askDocId, setAskDocId] = useState('');
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [working, setWorking] = useState(false);
  const [summaryFor, setSummaryFor] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const fetched = await fetchDocuments();
      setDocs(fetched);
      if (!askDocId && fetched.length === 0) { /* keep */ }
    } catch (err) {
      setError(err.message || 'Could not load documents.');
    } finally {
      setLoading(false);
    }
  }, [askDocId]);

  useEffect(() => { if (open) load(); }, [open, load]);

  const onUpload = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setUploading(true);
    setError('');
    try {
      const doc = await uploadDocument(f);
      setDocs((prev) => [doc, ...prev]);
    } catch (err) {
      setError(err.message || 'Upload failed.');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const doSearch = async () => {
    if (!query.trim()) { load(); return; }
    setLoading(true);
    setError('');
    try {
      setDocs(await searchDocuments(query.trim()));
    } catch (err) {
      setError(err.message || 'Search failed.');
    } finally {
      setLoading(false);
    }
  };

  const doAsk = async () => {
    if (!askDocId || !question.trim()) return;
    setWorking(true);
    setAnswer('');
    setError('');
    try {
      setAnswer(await askDocument(askDocId, question.trim()));
    } catch (err) {
      setError(err.message || 'Ask failed.');
    } finally {
      setWorking(false);
    }
  };

  const doSummarize = async (id) => {
    setSummaryFor(id);
    setError('');
    try {
      setAnswer(await summarizeDocument(id));
      setAskDocId(id);
    } catch (err) {
      setError(err.message || 'Summarize failed.');
    } finally {
      setSummaryFor(null);
    }
  };

  const doDelete = async (id) => {
    setError('');
    try {
      await deleteDocument(id);
      setDocs((prev) => prev.filter((d) => d.id !== id));
      if (askDocId === id) { setAskDocId(''); setAnswer(''); }
    } catch (err) {
      setError(err.message || 'Delete failed.');
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        style={{
          position: 'fixed', top: 200, left: 220, zIndex: 50,
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '10px 14px', borderRadius: 999,
          background: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(100, 116, 139, 0.25)',
          color: ACCENT, cursor: 'pointer', fontFamily: 'Inter, system-ui, sans-serif',
          fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase',
        }}
      >
        <FileText size={13} />
        Documents
        {docs.length > 0 && (
          <span style={{ background: 'rgba(100,116,139,0.25)', color: '#ddd6fe', borderRadius: 99, padding: '1px 7px', fontSize: 10, fontWeight: 700 }}>
            {docs.length}
          </span>
        )}
      </button>
    );
  }

  const inputStyle = {
    width: '100%', padding: '8px 10px', marginBottom: 8,
    background: 'rgba(100,116,139,0.06)', border: '1px solid rgba(100,116,139,0.2)',
    borderRadius: 8, color: TEXT, fontSize: 12, outline: 'none',
    boxSizing: 'border-box', fontFamily: 'inherit',
  };

  return (
    <div style={CARD_STYLE}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px', borderBottom: '1px solid rgba(100,116,139,0.15)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: ACCENT }}>
          <FileText size={14} />
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.14em' }}>DOCUMENTS</span>
          <span style={{ fontSize: 9, color: MUTED }}>Document AI</span>
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

        {/* Upload */}
        <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, padding: '13px 10px', marginBottom: 10, border: '1px dashed rgba(100,116,139,0.35)', borderRadius: 10, cursor: 'pointer', color: ACCENT, fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
          {uploading ? <Loader size={13} /> : <Upload size={13} />}
          {uploading ? 'Uploading & extracting…' : 'Upload PDF / DOCX / PPTX / XLSX / TXT'}
          <input type="file" accept=".pdf,.docx,.pptx,.xlsx,.txt,.md" onChange={onUpload} style={{ display: 'none' }} />
        </label>

        {/* Search */}
        <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <Search size={11} style={{ position: 'absolute', left: 9, top: 9, color: MUTED }} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && doSearch()}
              placeholder="Search documents…"
              style={{ ...inputStyle, paddingLeft: 26 }}
            />
          </div>
          <button onClick={doSearch} style={{ padding: '0 12px', background: 'rgba(100,116,139,0.12)', border: '1px solid rgba(100, 116, 139, 0.25)', borderRadius: 8, color: ACCENT, cursor: 'pointer', fontSize: 10, textTransform: 'uppercase' }}>
            Go
          </button>
        </div>

        {loading && <div style={{ color: MUTED, fontSize: 11, textAlign: 'center', padding: 16 }}>Loading…</div>}

        {!loading && docs.length === 0 && (
          <div style={{ color: MUTED, fontSize: 11, textAlign: 'center', padding: 20 }}>
            No documents yet — upload one and I can answer questions from it.
          </div>
        )}

        {docs.map((d) => (
          <div key={d.id} style={{ padding: '10px', marginBottom: 6, background: 'rgba(100,116,139,0.03)', border: '1px solid rgba(100,116,139,0.14)', borderRadius: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: TEXT, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {d.title}<span style={{ color: MUTED, fontWeight: 400 }}> {d.ext}</span>
              </span>
              <button onClick={() => doDelete(d.id)} style={{ background: 'none', border: 'none', color: MUTED, cursor: 'pointer', padding: 2, flexShrink: 0 }}>
                <Trash2 size={12} />
              </button>
            </div>
            <div style={{ fontSize: 10, color: MUTED, marginTop: 3 }}>{d.pages} page(s) · {Math.round(d.size / 1024)} KB</div>
            <div style={{ fontSize: 11, color: MUTED, marginTop: 4, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
              {d.snippet || '—'}
            </div>
            <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
              <button onClick={() => { setAskDocId(d.id); setAnswer(''); }} style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5, padding: '6px 0', background: 'rgba(100,116,139,0.12)', border: '1px solid rgba(100, 116, 139, 0.25)', borderRadius: 8, color: ACCENT, cursor: 'pointer', fontSize: 10, textTransform: 'uppercase' }}>
                <Sparkles size={10} /> Ask
              </button>
              <button onClick={() => doSummarize(d.id)} disabled={summaryFor === d.id} style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5, padding: '6px 0', background: 'rgba(100,116,139,0.12)', border: '1px solid rgba(100, 116, 139, 0.25)', borderRadius: 8, color: ACCENT, cursor: 'pointer', fontSize: 10, textTransform: 'uppercase' }}>
                {summaryFor === d.id ? <Loader size={10} /> : <FileText size={10} />}
                {summaryFor === d.id ? '…' : 'Summarize'}
              </button>
            </div>
          </div>
        ))}

        {/* Ask panel */}
        <div style={{ marginTop: 8, borderTop: '1px solid rgba(100,116,139,0.15)', paddingTop: 10 }}>
          <div style={{ fontSize: 10, color: MUTED, letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 8 }}>
            Ask a question
          </div>
          <select value={askDocId} onChange={(e) => { setAskDocId(e.target.value); setAnswer(''); }} style={{ ...inputStyle, cursor: 'pointer' }}>
            <option value="">Select a document…</option>
            {docs.map((d) => <option key={d.id} value={d.id}>{d.title}{d.ext}</option>)}
          </select>
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && doAsk()}
            placeholder="e.g. What are the key skills mentioned?"
            style={inputStyle}
          />
          <button onClick={doAsk} disabled={!askDocId || !question.trim() || working} style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, padding: '9px 0', background: askDocId && question.trim() && !working ? ACCENT : 'rgba(100,116,139,0.15)', border: 'none', borderRadius: 8, color: '#334155', fontWeight: 700, fontSize: 11, cursor: askDocId && question.trim() && !working ? 'pointer' : 'not-allowed', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            {working ? <Loader size={12} /> : <Sparkles size={12} />}
            {working ? 'Thinking…' : 'Ask'}
          </button>
          {answer && (
            <div style={{ marginTop: 10, background: 'rgba(100,116,139,0.06)', border: '1px solid rgba(100,116,139,0.25)', borderRadius: 10, padding: 12, fontSize: 12, color: TEXT, whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
              {answer}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
