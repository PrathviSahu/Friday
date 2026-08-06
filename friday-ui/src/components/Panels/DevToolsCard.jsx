import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence, useDragControls, useMotionValue, useSpring } from 'framer-motion';
import { Terminal, X, GripHorizontal, Database, ScrollText, SlidersHorizontal, Play, RefreshCw, Settings, Activity } from 'lucide-react';
import { useOrbState } from '../../hooks/useOrbState';
import { API_ENDPOINTS } from '../../api/config.js';

const TABS = [
    { key: 'overview', label: 'Overview', Icon: SlidersHorizontal },
    { key: 'metrics',  label: 'Latency',  Icon: Activity },
    { key: 'memory',   label: 'Memory',   Icon: Database },
    { key: 'logs',     label: 'Logs',     Icon: ScrollText },
    { key: 'tester',   label: 'API Tester', Icon: Play },
    { key: 'config',   label: 'Config',     Icon: Settings },
];

export default function DevToolsCard() {
    const { workspace } = useOrbState();
    const [isVisible, setIsVisible] = useState(false);
    const [tab, setTab] = useState('overview');
    const [overview, setOverview] = useState(null);
    const [memory, setMemory] = useState(null);
    const [logs, setLogs] = useState([]);
    const [config, setConfig] = useState(null);
    const [metrics, setMetrics] = useState(null);
    const [testMethod, setTestMethod] = useState('GET');
    const [testPath, setTestPath] = useState('/api/system/stats');
    const [testBody, setTestBody] = useState('');
    const [testResult, setTestResult] = useState('');

    const [isDragging, setIsDragging] = useState(false);
    const [transformOrigin, setTransformOrigin] = useState('50% 50%');
    const cardRef = React.useRef(null);
    const dragControls = useDragControls();
    const rawRotateX = useMotionValue(0);
    const rawRotateY = useMotionValue(0);
    const rotateX = useSpring(rawRotateX, { stiffness: 180, damping: 14, mass: 0.35 });
    const rotateY = useSpring(rawRotateY, { stiffness: 180, damping: 14, mass: 0.35 });

    const loadOverview = async () => {
        try {
            const res = await fetch(`${API_ENDPOINTS.dev}/overview`);
            if (res.ok) setOverview(await res.json());
        } catch (_) {}
    };

    const loadMemory = async () => {
        try {
            const res = await fetch(`${API_ENDPOINTS.dev}/memory`);
            if (res.ok) setMemory(await res.json());
        } catch (_) {}
    };

    const loadLogs = async () => {
        try {
            const res = await fetch(`${API_ENDPOINTS.dev}/logs?lines=150`);
            if (res.ok) setLogs((await res.json()).logs || []);
        } catch (_) {}
    };

    const loadMetrics = async () => {
        try {
            const res = await fetch(`${API_ENDPOINTS.dev}/metrics`);
            if (res.ok) setMetrics(await res.json());
        } catch (_) {}
    };

    const loadConfig = async () => {
        try {
            const res = await fetch(`${API_ENDPOINTS.dev}/config`);
            if (res.ok) setConfig(await res.json());
        } catch (_) {}
    };

    useEffect(() => {
        loadOverview();
    }, []);

    const switchTab = (key) => {
        setTab(key);
        if (key === 'memory' && !memory) loadMemory();
        if (key === 'logs') loadLogs();
        if (key === 'overview') loadOverview();
        if (key === 'config' && !config) loadConfig();
        if (key === 'tester') setTestResult('');
    };

    const runTest = async () => {
        setTestResult('Running…');
        let body = null;
        if (testBody.trim()) {
            try { body = JSON.parse(testBody); } catch (_) {
                setTestResult('Invalid JSON body.');
                return;
            }
        }
        try {
            const res = await fetch(`${API_ENDPOINTS.dev}/test`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ method: testMethod, path: testPath, body }),
            });
            const data = await res.json();
            setTestResult(JSON.stringify({ status: data.status, data: data.data }, null, 2));
        } catch (e) {
            setTestResult('Error: ' + e.message);
        }
    };

    const handlePointerDownHeader = (e) => {
        if (cardRef.current) {
            const rect = cardRef.current.getBoundingClientRect();
            setTransformOrigin(`${e.clientX - rect.left}px ${e.clientY - rect.top}px`);
        }
        setIsDragging(true);
        dragControls.start(e);
    };

    const handleDrag = (_, info) => {
        rawRotateX.set(Math.max(-24, Math.min(24, -info.velocity.y * 0.045)));
        rawRotateY.set(Math.max(-24, Math.min(24, info.velocity.x * 0.045)));
    };

    const handleDragEnd = () => {
        setIsDragging(false);
        rawRotateX.set(0);
        rawRotateY.set(0);
    };

    // NOTE: guard must stay after every hook call (rules-of-hooks).
    if (workspace === 'career' || workspace === 'trading') return null;

    if (!isVisible) {
        return (
            <motion.div
                drag
                dragConstraints={{ left: -600, right: 600, top: -400, bottom: 400 }}
                dragElastic={0.1}
                whileDrag={{ scale: 1.05 }}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setIsVisible(true)}
                style={{
                    position: 'fixed', top: 80, right: 40, zIndex: 50,
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '7px 14px', borderRadius: 99,
                    cursor: 'grab', pointerEvents: 'auto', userSelect: 'none',
                    background: '#0f0f1a', border: '1px solid #1e293b',
                    color: '#94a3b8', fontSize: 11, fontFamily: 'monospace',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.6)'
                }}
            >
                <Terminal size={13} style={{ color: '#64748b' }} />
                <span>Dev</span>
            </motion.div>
        );
    }

    return (
        <AnimatePresence>
            <motion.div
                ref={cardRef}
                drag
                dragControls={dragControls}
                dragListener={false}
                dragMomentum={false}
                dragElastic={0.2}
                dragConstraints={{ left: -3000, right: 3000, top: -3000, bottom: 3000 }}
                onDrag={handleDrag}
                onDragEnd={handleDragEnd}
                initial={{ opacity: 0, scale: 0.93 }}
                animate={{ opacity: 1, scale: isDragging ? 1.06 : 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ type: 'spring', stiffness: 320, damping: 30 }}
                style={{
                    position: 'fixed', top: 80, right: 40, zIndex: 40,
                    width: 420, maxHeight: 520,
                    borderRadius: 16, overflow: 'hidden',
                    pointerEvents: 'auto', userSelect: 'none',
                    background: '#0f0f1a', border: '1px solid #1e293b',
                    boxShadow: '0 32px 80px rgba(0,0,0,0.75)',
                    fontFamily: 'Inter, system-ui, sans-serif',
                    rotateX, rotateY, transformOrigin, transformStyle: 'preserve-3d',
                    perspective: 1000, willChange: 'transform', backfaceVisibility: 'hidden',
                }}
            >
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', top: 0, left: 0, right: 45, height: 10, cursor: 'grab', zIndex: 50 }} />
                <div style={{ height: 2, background: 'linear-gradient(90deg, transparent, #64748b, transparent)', opacity: 0.7 }} />

                <div onPointerDown={handlePointerDownHeader} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '12px 16px 10px', borderBottom: '1px solid #1e293b',
                    cursor: 'grab', position: 'relative', zIndex: 40
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                        <GripHorizontal size={13} style={{ color: '#334155' }} />
                        <Terminal size={14} style={{ color: '#94a3b8' }} />
                        <span style={{ fontSize: 13, fontWeight: 700, color: '#e2e8f0', letterSpacing: '-0.01em' }}>Developer Mode</span>
                    </div>
                    <button type="button" onClick={() => setIsVisible(false)} title="Close"
                        style={{ background: 'none', border: 'none', color: '#475569', cursor: 'pointer', padding: 4, display: 'flex' }}>
                        <X size={14} />
                    </button>
                </div>

                {/* Tabs */}
                <div style={{ display: 'flex', gap: 4, padding: '8px 12px 0', borderBottom: '1px solid #1e293b' }}>
                    {TABS.map(({ key, label, Icon }) => (
                        <button key={key} type="button" onClick={() => switchTab(key)}
                            style={{
                                display: 'flex', alignItems: 'center', gap: 5, padding: '6px 10px',
                                border: 'none', borderRadius: '8px 8px 0 0', cursor: 'pointer',
                                background: tab === key ? '#141428' : 'transparent',
                                color: tab === key ? '#e2e8f0' : '#64748b', fontSize: 10.5, fontWeight: 600,
                            }}>
                            <Icon size={11} /> {label}
                        </button>
                    ))}
                </div>

                <div style={{ padding: '12px 16px', overflowY: 'auto', maxHeight: 400, minHeight: 120 }}>

                    {tab === 'overview' && (
                        <div>
                            {overview && (
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6 }}>
                                    {Object.entries(overview).map(([k, v]) => (
                                        <div key={k} style={{ background: '#141428', border: '1px solid #1e293b', borderRadius: 10, padding: '8px', textAlign: 'center' }}>
                                            <div style={{ fontSize: 15, fontWeight: 800, color: '#94a3b8' }}>{typeof v === 'number' ? v : String(v)}</div>
                                            <div style={{ fontSize: 9, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{k.replace(/_/g, ' ')}</div>
                                        </div>
                                    ))}
                                </div>
                            )}
                            <button type="button" onClick={loadOverview}
                                style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 5, padding: '6px 10px', borderRadius: 8, border: '1px solid #334155', background: 'transparent', color: '#94a3b8', fontSize: 10, cursor: 'pointer' }}>
                                <RefreshCw size={11} /> Refresh
                            </button>
                        </div>
                    )}

                    {tab === 'metrics' && (
                        <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                                <span style={{ fontSize: 10, fontWeight: 700, color: '#94a3b8', letterSpacing: '0.1em', textTransform: 'uppercase' }}>Live latencies (avg / last)</span>
                                <button onClick={() => { loadMetrics(); }} style={{ display: 'flex', alignItems: 'center', gap: 4, background: 'none', border: 'none', color: '#38bdf8', cursor: 'pointer', fontSize: 10, textTransform: 'uppercase' }}>
                                    <RefreshCw size={10} /> Refresh
                                </button>
                            </div>

                            {metrics?.last && (
                                <div style={{ background: '#141428', border: '1px solid #1e293b', borderRadius: 10, padding: 10, marginBottom: 10 }}>
                                    <div style={{ fontSize: 10, color: '#64748b', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 6 }}>Last action</div>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                                        {metrics.last.agent && <span style={{ fontSize: 11, color: '#e2e8f0' }}>Agent: <b style={{ color: '#38bdf8' }}>{metrics.last.agent}</b></span>}
                                        {metrics.last.tool && <span style={{ fontSize: 11, color: '#e2e8f0' }}>Tool: <b style={{ color: '#a78bfa' }}>{metrics.last.tool}</b></span>}
                                        {metrics.last.action && <span style={{ fontSize: 11, color: '#e2e8f0' }}>Action: <b style={{ color: '#f472b6' }}>{metrics.last.action}</b></span>}
                                    </div>
                                </div>
                            )}

                            {metrics?.averages && Object.keys(metrics.averages).length === 0 && (
                                <div style={{ color: '#64748b', fontSize: 11, textAlign: 'center', padding: 14 }}>
                                    No activity recorded yet — talk to Friday or run a tool.
                                </div>
                            )}

                            {metrics?.averages && Object.entries(metrics.averages).map(([op, a]) => (
                                <div key={op} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#141428', border: '1px solid #1e293b', borderRadius: 10, padding: '9px 12px', marginBottom: 6 }}>
                                    <div>
                                        <div style={{ fontSize: 12, fontWeight: 700, color: '#e2e8f0', textTransform: 'capitalize' }}>{op}</div>
                                        <div style={{ fontSize: 10, color: '#64748b' }}>{a.count} call(s)</div>
                                    </div>
                                    <div style={{ textAlign: 'right' }}>
                                        <div style={{ fontSize: 14, fontWeight: 800, color: a.avg_ms < 400 ? '#4ade80' : a.avg_ms < 1500 ? '#facc15' : '#f87171' }}>{a.avg_ms} ms</div>
                                        <div style={{ fontSize: 10, color: '#64748b' }}>last {a.last_ms} ms</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {tab === 'memory' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                            <button type="button" onClick={loadMemory}
                                style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '6px 10px', borderRadius: 8, border: '1px solid #334155', background: 'transparent', color: '#94a3b8', fontSize: 10, cursor: 'pointer', alignSelf: 'flex-start' }}>
                                <RefreshCw size={11} /> Reload
                            </button>
                            {!memory && <div style={{ fontSize: 11, color: '#475569' }}>Load to view memory…</div>}
                            {memory && (
                                <>
                                    <Section title={`Facts (${memory.facts.length})`}>
                                        {memory.facts.map((f, i) => (
                                            <div key={i} style={{ fontSize: 10.5, color: '#94a3b8', fontFamily: 'monospace' }}>
                                                <span style={{ color: '#cbd5e1' }}>{f.key}</span> = {f.value}
                                            </div>
                                        ))}
                                        {!memory.facts.length && <div style={{ fontSize: 10.5, color: '#475569' }}>none</div>}
                                    </Section>
                                    <Section title={`Life Memory (${memory.life_memories.length})`}>
                                        {memory.life_memories.map((m, i) => (
                                            <div key={i} style={{ fontSize: 10.5, color: '#94a3b8' }}>
                                                <span style={{ color: '#fdba74' }}>{m.subject}</span> → <span style={{ color: '#93c5fd' }}>{m.relation}</span> → <span style={{ color: '#cbd5e1' }}>{m.target}</span>
                                            </div>
                                        ))}
                                        {!memory.life_memories.length && <div style={{ fontSize: 10.5, color: '#475569' }}>none</div>}
                                    </Section>
                                </>
                            )}
                        </div>
                    )}

                    {tab === 'logs' && (
                        <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                                <div style={{ fontSize: 10, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Recent log tail</div>
                                <button type="button" onClick={loadLogs}
                                    style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 8px', borderRadius: 6, border: '1px solid #334155', background: 'transparent', color: '#94a3b8', fontSize: 9.5, cursor: 'pointer' }}>
                                    <RefreshCw size={10} /> Reload
                                </button>
                            </div>
                            <pre style={{ margin: 0, background: '#0a0a12', border: '1px solid #1e293b', borderRadius: 10, padding: 10, fontSize: 9.5, fontFamily: 'monospace', color: '#7dd3fc', lineHeight: 1.5, maxHeight: 300, overflowY: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                                {logs.length ? logs.join('\n') : 'No logs captured yet.'}
                            </pre>
                        </div>
                    )}

                    {tab === 'config' && config && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                            <div style={{ fontSize: 10, color: '#475569' }}>Version <span style={{ color: '#94a3b8', fontFamily: 'monospace' }}>{config.version}</span></div>
                            <Section title="Environment keys (set? — values never shown)">
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '4px 12px' }}>
                                    {Object.entries(config.env).map(([k, v]) => (
                                        <React.Fragment key={k}>
                                            <span style={{ fontSize: 10.5, fontFamily: 'monospace', color: '#cbd5e1' }}>{k}</span>
                                            <span style={{ fontSize: 10.5, fontFamily: 'monospace', color: v ? '#4ade80' : '#ef4444' }}>{v ? '✓ set' : '—'}</span>
                                        </React.Fragment>
                                    ))}
                                </div>
                            </Section>
                            <Section title="Permission modes">
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '4px 12px' }}>
                                    {Object.entries(config.permissions).map(([k, v]) => (
                                        <React.Fragment key={k}>
                                            <span style={{ fontSize: 10.5, fontFamily: 'monospace', color: '#cbd5e1' }}>{k}</span>
                                            <span style={{ fontSize: 10.5, fontFamily: 'monospace', color: v === 'enabled' ? '#4ade80' : v === 'ask' ? '#f59e0b' : '#ef4444' }}>{v}</span>
                                        </React.Fragment>
                                    ))}
                                </div>
                            </Section>
                        </div>
                    )}

                    {tab === 'tester' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                            <div style={{ display: 'flex', gap: 6 }}>
                                <select value={testMethod} onChange={(e) => setTestMethod(e.target.value)}
                                    style={{ background: '#141428', border: '1px solid #1e293b', borderRadius: 8, padding: '6px 8px', color: '#cbd5e1', fontSize: 10, fontFamily: 'monospace' }}>
                                    {['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map((m) => <option key={m}>{m}</option>)}
                                </select>
                                <input type="text" value={testPath} onChange={(e) => setTestPath(e.target.value)}
                                    placeholder="/api/system/stats"
                                    style={{ flex: 1, background: '#141428', border: '1px solid #1e293b', borderRadius: 8, padding: '6px 10px', color: '#e2e8f0', fontSize: 11, fontFamily: 'monospace', outline: 'none' }} />
                                <button type="button" onClick={runTest}
                                    style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '6px 12px', borderRadius: 8, border: 'none', background: '#1d4ed8', color: '#dbeafe', fontSize: 10.5, fontWeight: 600, cursor: 'pointer' }}>
                                    <Play size={11} /> Run
                                </button>
                            </div>
                            <textarea value={testBody} onChange={(e) => setTestBody(e.target.value)}
                                placeholder='Optional JSON body: {"text": "hello"}'
                                rows={2}
                                style={{ background: '#141428', border: '1px solid #1e293b', borderRadius: 8, padding: '7px 10px', color: '#e2e8f0', fontSize: 10.5, fontFamily: 'monospace', outline: 'none', resize: 'vertical' }} />
                            <pre style={{ margin: 0, background: '#0a0a12', border: '1px solid #1e293b', borderRadius: 10, padding: 10, fontSize: 10, fontFamily: 'monospace', color: '#86efac', lineHeight: 1.5, maxHeight: 220, overflowY: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                                {testResult || 'Run a request to see the response.'}
                            </pre>
                        </div>
                    )}
                </div>
            </motion.div>
        </AnimatePresence>
    );
}

function Section({ title, children }) {
    return (
        <div style={{ background: '#10101c', border: '1px solid #1e293b', borderRadius: 10, padding: 10 }}>
            <div style={{ fontSize: 10, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>{title}</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>{children}</div>
        </div>
    );
}
