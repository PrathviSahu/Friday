import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence, useDragControls, useMotionValue, useSpring } from 'framer-motion';
import { Zap, X, GripHorizontal, Undo2, ShieldOff, RefreshCw } from 'lucide-react';
import { useOrbState } from '../../hooks/useOrbState';
import { API_ENDPOINTS } from '../../api/config.js';

/**
 * AutonomyCard — Phase 2.1 Autonomy & Trust Engine HUD panel.
 * Shows the per-action trust ledger ("how much FRIDAY trusts herself with X"),
 * today's journal of autonomous executions, one-tap Undo (300s window) and
 * per-action Revoke. Mirrors the NotificationCenterCard interaction pattern.
 */

const TIER_STYLE = {
    silent:   { color: '#4ade80', bg: 'rgba(74,222,128,0.10)',  label: 'SILENT' },
    announce: { color: '#fbbf24', bg: 'rgba(251,191,36,0.10)',  label: 'ANNOUNCE' },
    confirm:  { color: '#94a3b8', bg: 'rgba(148,163,184,0.10)', label: 'ASK FIRST' },
};

const OUTCOME_STYLE = {
    auto_accepted: '#4ade80',
    undone: '#f87171',
    failed: '#f87171',
};

function TierBadge({ tier }) {
    const s = TIER_STYLE[tier] || TIER_STYLE.confirm;
    return (
        <span style={{
            fontSize: 8, fontFamily: 'monospace', fontWeight: 700, letterSpacing: '0.06em',
            color: s.color, background: s.bg, border: `1px solid ${s.color}55`,
            borderRadius: 6, padding: '1px 6px',
        }}>
            {s.label}
        </span>
    );
}

export default function AutonomyCard() {
    const { workspace } = useOrbState();
    const [isVisible, setIsVisible] = useState(false);
    const [status, setStatus] = useState(null);
    const [journal, setJournal] = useState([]);

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
            const [s, j] = await Promise.all([
                fetch(`${API_ENDPOINTS.autonomy}/status`),
                fetch(`${API_ENDPOINTS.autonomy}/journal`),
            ]);
            if (s.ok) setStatus(await s.json());
            if (j.ok) setJournal((await j.json()).entries || []);
        } catch (_) {}
    };

    useEffect(() => {
        load();
        const iv = setInterval(load, 30000); // trust tiers evolve — refresh often
        return () => clearInterval(iv);
    }, []);

    const undo = async (journalId) => {
        try {
            await fetch(`${API_ENDPOINTS.autonomy}/undo`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ journal_id: journalId }),
            });
            load();
        } catch (_) {}
    };

    const revoke = async (actionType) => {
        try {
            await fetch(`${API_ENDPOINTS.autonomy}/revoke`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action_type: actionType }),
            });
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
                    position: 'fixed', bottom: 32, right: 270, zIndex: 50,
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '7px 14px', borderRadius: 99,
                    cursor: 'grab', pointerEvents: 'auto', userSelect: 'none',
                    background: '#0f0f1a', border: '1px solid #1e3a8a',
                    color: '#93c5fd', fontSize: 11, fontFamily: 'monospace',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.6)'
                }}
            >
                <Zap size={13} style={{ color: '#60a5fa' }} />
                <span>Autonomy</span>
            </motion.div>
        );
    }

    const autonomousToday = journal.filter((e) => e.tier !== 'confirm').length;

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
                    position: 'fixed', bottom: 32, right: 270, zIndex: 40,
                    width: 380, maxHeight: 540,
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
                        <Zap size={14} style={{ color: '#60a5fa' }} />
                        <span style={{ fontSize: 13, fontWeight: 700, color: '#dbeafe', letterSpacing: '-0.01em' }}>Autonomy & Trust</span>
                        {autonomousToday > 0 && (
                            <span style={{ fontSize: 10, background: '#1e3a8a', color: '#bfdbfe', borderRadius: 99, padding: '1px 7px', fontFamily: 'monospace' }}>
                                {autonomousToday} today
                            </span>
                        )}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <button type="button" onClick={load} title="Refresh"
                            style={{ background: 'rgba(96,165,250,0.1)', border: '1px solid rgba(96,165,250,0.4)', color: '#93c5fd', borderRadius: 8, padding: '3px 8px', fontSize: 10, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                            <RefreshCw size={11} />
                        </button>
                        <button type="button" onClick={() => setIsVisible(false)} title="Close"
                            style={{ background: 'none', border: 'none', color: '#1e3a8a', cursor: 'pointer', padding: 4, display: 'flex' }}>
                            <X size={14} />
                        </button>
                    </div>
                </div>

                <div style={{ padding: '10px 16px', display: 'flex', flexDirection: 'column', gap: 10, overflowY: 'auto', maxHeight: 440 }}>

                    {/* ── Trust ledger ── */}
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#64748b', letterSpacing: '0.08em' }}>TRUST LEDGER</div>
                    {(!status || status.actions.length === 0) && (
                        <div style={{ fontSize: 11, color: '#475569', textAlign: 'center', padding: '8px 0' }}>
                            No trust earned yet. Accept FRIDAY's suggestions and autonomy grows.
                        </div>
                    )}
                    {status && status.actions.map((a) => (
                        <div key={a.action_type} style={{
                            padding: '8px 10px', borderRadius: 10,
                            background: '#10101c', border: '1px solid #1e293b'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                                <span style={{ fontSize: 11, fontWeight: 600, color: '#e2e8f0' }}>
                                    {a.action_type.replace(/_/g, ' ')}
                                </span>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                    <TierBadge tier={a.tier} />
                                    <button type="button" onClick={() => revoke(a.action_type)} title="Revoke autonomy — back to ask-first"
                                        style={{ background: 'none', border: 'none', color: '#475569', cursor: 'pointer', padding: 2, display: 'flex' }}>
                                        <ShieldOff size={12} />
                                    </button>
                                </div>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
                                <div style={{ flex: 1, height: 4, borderRadius: 99, background: '#1e293b', overflow: 'hidden' }}>
                                    <div style={{
                                        height: '100%', borderRadius: 99, width: `${Math.round(a.trust * 100)}%`,
                                        background: a.tier === 'silent' ? '#4ade80' : a.tier === 'announce' ? '#fbbf24' : '#60a5fa',
                                        transition: 'width 0.4s ease'
                                    }} />
                                </div>
                                <span style={{ fontSize: 9, color: '#64748b', fontFamily: 'monospace', minWidth: 64, textAlign: 'right' }}>
                                    {Math.round(a.trust * 100)}% · ✓{a.accepts} ✗{a.rejects}
                                </span>
                            </div>
                        </div>
                    ))}

                    {/* ── Today's journal ── */}
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#64748b', letterSpacing: '0.08em', marginTop: 4 }}>
                        WHAT FRIDAY DID TODAY
                    </div>
                    {journal.length === 0 && (
                        <div style={{ fontSize: 11, color: '#475569', textAlign: 'center', padding: '8px 0' }}>
                            Nothing autonomous yet today.
                        </div>
                    )}
                    {journal.map((e) => {
                        const undoable = e.undo_payload && !e.undone && !e.outcome;
                        const time = (e.executed_at || '').split('T')[1] || e.executed_at;
                        return (
                            <div key={e.id} style={{
                                display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8,
                                padding: '8px 10px', borderRadius: 10,
                                background: '#10101c',
                                border: `1px solid ${e.undone ? 'rgba(248,113,113,0.35)' : '#1e293b'}`
                            }}>
                                <div style={{ minWidth: 0 }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                                        <span style={{ fontSize: 11, fontWeight: 600, color: '#e2e8f0' }}>
                                            {e.action_type.replace(/_/g, ' ')}
                                        </span>
                                        <TierBadge tier={e.tier} />
                                        {e.outcome && (
                                            <span style={{ fontSize: 9, fontFamily: 'monospace', color: OUTCOME_STYLE[e.outcome] || '#64748b' }}>
                                                {e.outcome.replace('_', ' ')}
                                            </span>
                                        )}
                                    </div>
                                    <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 3, lineHeight: 1.4 }}>
                                        {(e.result_summary || '').slice(0, 90)}
                                    </div>
                                    <div style={{ fontSize: 9, color: '#475569', fontFamily: 'monospace', marginTop: 3 }}>{time}</div>
                                </div>
                                {undoable && (
                                    <button type="button" onClick={() => undo(e.id)} title="Undo (300s window)"
                                        style={{
                                            background: 'rgba(248,113,113,0.10)', border: '1px solid rgba(248,113,113,0.4)',
                                            color: '#fca5a5', borderRadius: 8, padding: '4px 8px', fontSize: 10,
                                            cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0
                                        }}>
                                        <Undo2 size={11} /> Undo
                                    </button>
                                )}
                            </div>
                        );
                    })}

                    {/* ── Budget chips ── */}
                    {status && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginTop: 2 }}>
                            {Object.entries(status.budget).filter(([, v]) => v >= 0).map(([cls, left]) => (
                                <span key={cls} style={{
                                    fontSize: 9, fontFamily: 'monospace', color: left > 0 ? '#64748b' : '#f87171',
                                    background: '#10101c', border: '1px solid #1e293b', borderRadius: 6, padding: '2px 7px'
                                }}>
                                    {cls}: {left}/4
                                </span>
                            ))}
                        </div>
                    )}
                </div>
            </motion.div>
        </AnimatePresence>
    );
}
