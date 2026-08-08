import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence, useDragControls, useMotionValue, useSpring } from 'framer-motion';
import { Workflow, X, GripHorizontal, Play, Trash2, Plus, RefreshCw } from 'lucide-react';
import { useOrbState } from '../../hooks/useOrbState';
import { API_ENDPOINTS } from '../../api/config.js';

/**
 * MacrosCard — Phase 2.4 Voice Macro & Workflow Composer HUD panel.
 * Create voice-triggered tool chains ("when I say X, do A then B"), run them
 * manually (owner-approved force), delete, and inspect recent run history.
 * Follows the NotificationCenterCard interaction pattern.
 */

const DEFAULT_STEPS = '[\n  {"tool": "open_trading", "params": {}},\n  {"tool": "get_weather", "params": {}}\n]';

export default function MacrosCard() {
    const { workspace } = useOrbState();
    const [isVisible, setIsVisible] = useState(false);
    const [macrosList, setMacrosList] = useState([]);
    const [trigger, setTrigger] = useState('');
    const [stepsText, setStepsText] = useState(DEFAULT_STEPS);
    const [formError, setFormError] = useState('');
    const [runningId, setRunningId] = useState(null);

    const [isDragging, setIsDragging] = useState(false);
    const [transformOrigin, setTransformOrigin] = useState('50% 50%');
    const cardRef = React.useRef(null);
    const dragControls = useDragControls();
    const rawRotateX = useMotionValue(0);
    const rawRotateY = useMotionValue(0);
    const rotateX = useSpring(rawRotateX, { stiffness: 180, damping: 14, mass: 0.35 });
    const rotateY = useSpring(rawRotateY, { stiffness: 180, damping: 14, mass: 0.35 });

    const load = async () => {
        try {
            const res = await fetch(API_ENDPOINTS.macros);
            if (res.ok) setMacrosList((await res.json()).macros || []);
        } catch (_) {}
    };

    useEffect(() => {
        load();
        const iv = setInterval(load, 45000);
        return () => clearInterval(iv);
    }, []);

    const createMacro = async () => {
        setFormError('');
        let steps;
        try {
            steps = JSON.parse(stepsText);
        } catch (_) {
            setFormError('Steps must be valid JSON — e.g. [{"tool": "get_weather"}]');
            return;
        }
        try {
            const res = await fetch(API_ENDPOINTS.macros, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ trigger_phrase: trigger.trim(), steps }),
            });
            const data = await res.json();
            if (!res.ok) {
                setFormError(data.detail || 'Could not create macro.');
                return;
            }
            setTrigger('');
            load();
        } catch (_) {
            setFormError('Network error creating macro.');
        }
    };

    const runMacro = async (id) => {
        setRunningId(id);
        try {
            await fetch(`${API_ENDPOINTS.macros}/${id}/run`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ force: true }),
            });
            load();
        } catch (_) {}
        setRunningId(null);
    };

    const deleteMacro = async (id) => {
        try {
            await fetch(`${API_ENDPOINTS.macros}/${id}`, { method: 'DELETE' });
            load();
        } catch (_) {}
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
                    position: 'fixed', bottom: 32, right: 390, zIndex: 50,
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '7px 14px', borderRadius: 99,
                    cursor: 'grab', pointerEvents: 'auto', userSelect: 'none',
                    background: '#0f0f1a', border: '1px solid #1e3a8a',
                    color: '#93c5fd', fontSize: 11, fontFamily: 'monospace',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.6)'
                }}
            >
                <Workflow size={13} style={{ color: '#60a5fa' }} />
                <span>Macros</span>
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
                    position: 'fixed', bottom: 32, right: 390, zIndex: 40,
                    width: 400, maxHeight: 560,
                    borderRadius: 16, overflow: 'hidden',
                    pointerEvents: 'auto', userSelect: 'none',
                    background: '#0f0f1a', border: '1px solid #1e3a8a',
                    boxShadow: '0 32px 80px rgba(0,0,0,0.75)',
                    fontFamily: 'Inter, system-ui, sans-serif',
                    rotateX, rotateY, transformOrigin, transformStyle: 'preserve-3d',
                    perspective: 1000, willChange: 'transform', backfaceVisibility: 'hidden',
                }}
            >
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', top: 0, left: 0, right: 45, height: 10, cursor: 'grab', zIndex: 50 }} />
                <div style={{ height: 2, background: 'linear-gradient(90deg, transparent, #60a5fa, transparent)', opacity: 0.7 }} />

                <div onPointerDown={handlePointerDownHeader} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '12px 16px 10px', borderBottom: '1px solid #1e3a8a',
                    cursor: 'grab', position: 'relative', zIndex: 40
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                        <GripHorizontal size={13} style={{ color: '#1e3a8a' }} />
                        <Workflow size={14} style={{ color: '#60a5fa' }} />
                        <span style={{ fontSize: 13, fontWeight: 700, color: '#dbeafe', letterSpacing: '-0.01em' }}>Voice Macros</span>
                        {macrosList.length > 0 && (
                            <span style={{ fontSize: 10, background: '#1e3a8a', color: '#bfdbfe', borderRadius: 99, padding: '1px 7px', fontFamily: 'monospace' }}>
                                {macrosList.length}
                            </span>
                        )}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <button type="button" onClick={load} title="Refresh"
                            style={{ background: 'rgba(96,165,250,0.1)', border: '1px solid rgba(96,165,250,0.4)', color: '#93c5fd', borderRadius: 8, padding: '3px 8px', fontSize: 10, cursor: 'pointer', display: 'flex' }}>
                            <RefreshCw size={11} />
                        </button>
                        <button type="button" onClick={() => setIsVisible(false)} title="Close"
                            style={{ background: 'none', border: 'none', color: '#1e3a8a', cursor: 'pointer', padding: 4, display: 'flex' }}>
                            <X size={14} />
                        </button>
                    </div>
                </div>

                <div style={{ padding: '10px 16px', display: 'flex', flexDirection: 'column', gap: 10, overflowY: 'auto', maxHeight: 470 }}>

                    {/* ── Create form ── */}
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#64748b', letterSpacing: '0.08em' }}>NEW MACRO</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        <input
                            value={trigger}
                            onChange={(e) => setTrigger(e.target.value)}
                            placeholder='Trigger phrase — "start my morning"'
                            style={{
                                background: '#10101c', border: '1px solid #1e293b', borderRadius: 8,
                                color: '#e2e8f0', fontSize: 11, padding: '7px 10px', outline: 'none',
                                fontFamily: 'inherit'
                            }}
                        />
                        <textarea
                            value={stepsText}
                            onChange={(e) => setStepsText(e.target.value)}
                            rows={4}
                            spellCheck={false}
                            style={{
                                background: '#10101c', border: '1px solid #1e293b', borderRadius: 8,
                                color: '#94a3b8', fontSize: 10, padding: '7px 10px', outline: 'none',
                                fontFamily: 'monospace', resize: 'vertical'
                            }}
                        />
                        {formError && (
                            <div style={{ fontSize: 10, color: '#f87171', lineHeight: 1.4 }}>{formError}</div>
                        )}
                        <button type="button" onClick={createMacro} disabled={!trigger.trim()}
                            style={{
                                background: trigger.trim() ? 'rgba(96,165,250,0.15)' : '#10101c',
                                border: '1px solid rgba(96,165,250,0.4)', color: trigger.trim() ? '#93c5fd' : '#475569',
                                borderRadius: 8, padding: '6px 10px', fontSize: 11, fontWeight: 600,
                                cursor: trigger.trim() ? 'pointer' : 'default',
                                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5
                            }}>
                            <Plus size={12} /> Create Macro (voice: "when I say …, do …")
                        </button>
                    </div>

                    {/* ── Macro list ── */}
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#64748b', letterSpacing: '0.08em', marginTop: 4 }}>SAVED MACROS</div>
                    {macrosList.length === 0 && (
                        <div style={{ fontSize: 11, color: '#475569', textAlign: 'center', padding: '10px 0' }}>
                            No macros yet. Create one above or tell FRIDAY: "when I say X, do A then B".
                        </div>
                    )}
                    {macrosList.map((m) => (
                        <div key={m.id} style={{
                            padding: '8px 10px', borderRadius: 10,
                            background: '#10101c', border: '1px solid #1e293b'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                                <span style={{ fontSize: 11, fontWeight: 700, color: '#e2e8f0' }}>
                                    “{m.trigger_phrase}”
                                </span>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                                    <button type="button" onClick={() => runMacro(m.id)} disabled={runningId === m.id}
                                        title="Run now (owner-approved)"
                                        style={{
                                            background: 'rgba(74,222,128,0.10)', border: '1px solid rgba(74,222,128,0.4)',
                                            color: '#86efac', borderRadius: 8, padding: '3px 8px', fontSize: 10,
                                            cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4
                                        }}>
                                        <Play size={10} /> {runningId === m.id ? 'Running…' : 'Run'}
                                    </button>
                                    <button type="button" onClick={() => deleteMacro(m.id)} title="Delete macro"
                                        style={{ background: 'none', border: 'none', color: '#475569', cursor: 'pointer', padding: 2, display: 'flex' }}>
                                        <Trash2 size={12} />
                                    </button>
                                </div>
                            </div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
                                {m.steps.map((s, i) => (
                                    <span key={i} style={{
                                        fontSize: 9, fontFamily: 'monospace', color: '#93c5fd',
                                        background: 'rgba(96,165,250,0.08)', border: '1px solid rgba(96,165,250,0.25)',
                                        borderRadius: 6, padding: '1px 6px'
                                    }}>
                                        {i + 1}. {s.tool}
                                    </span>
                                ))}
                            </div>
                            {(m.recent_runs || []).length > 0 && (
                                <div style={{ fontSize: 9, color: '#475569', fontFamily: 'monospace', marginTop: 5 }}>
                                    Last run: ✓{m.recent_runs[0].steps_ok} ✗{m.recent_runs[0].steps_failed} · {(m.recent_runs[0].ran_at || '').split('T')[1] || m.recent_runs[0].ran_at}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </motion.div>
        </AnimatePresence>
    );
}
