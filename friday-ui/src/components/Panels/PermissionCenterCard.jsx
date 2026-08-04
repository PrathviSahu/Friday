import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence, useDragControls, useMotionValue, useSpring } from 'framer-motion';
import { Shield, ShieldCheck, ShieldOff, Clock, X, GripHorizontal, RefreshCw } from 'lucide-react';
import { useOrbState } from '../../hooks/useOrbState';
import { API_ENDPOINTS } from '../../api/config.js';

const MODE_META = {
    enabled:  { label: 'Enabled',  color: '#22c55e', Icon: ShieldCheck },
    ask:      { label: 'Ask',      color: '#f59e0b', Icon: Clock },
    disabled: { label: 'Disabled', color: '#ef4444', Icon: ShieldOff },
};

export default function PermissionCenterCard() {
    const { workspace } = useOrbState();
    const [isVisible, setIsVisible] = useState(false);
    const [permissions, setPermissions] = useState([]);
    const [audit, setAudit] = useState([]);
    const [loading, setLoading] = useState(false);

    const [isDragging, setIsDragging] = useState(false);
    const [transformOrigin, setTransformOrigin] = useState('50% 50%');
    const cardRef = React.useRef(null);
    const dragControls = useDragControls();
    const rawRotateX = useMotionValue(0);
    const rawRotateY = useMotionValue(0);
    const rotateX = useSpring(rawRotateX, { stiffness: 180, damping: 14, mass: 0.35 });
    const rotateY = useSpring(rawRotateY, { stiffness: 180, damping: 14, mass: 0.35 });

    const load = async () => {
        setLoading(true);
        try {
            const res = await fetch(API_ENDPOINTS.permissions);
            if (res.ok) {
                const data = await res.json();
                setPermissions(data.permissions || []);
                setAudit(data.audit || []);
            }
        } catch (_) {}
        setLoading(false);
    };

    useEffect(() => { load(); }, []);

    const cycleMode = async (cap, current) => {
        const next = current === 'enabled' ? 'ask' : current === 'ask' ? 'disabled' : 'enabled';
        try {
            await fetch(API_ENDPOINTS.permissions, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ capability: cap, mode: next }),
            });
            load();
        } catch (_) {}
    };

    const grantApproval = async (cap) => {
        try {
            await fetch(`${API_ENDPOINTS.permissions}/approve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ capability: cap, seconds: 300 }),
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
                    position: 'fixed', bottom: 32, right: 220, zIndex: 50,
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '7px 14px', borderRadius: 99,
                    cursor: 'grab', pointerEvents: 'auto', userSelect: 'none',
                    background: '#0f0f1a', border: '1px solid #14532d',
                    color: '#86efac', fontSize: 11, fontFamily: 'monospace',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.6)'
                }}
            >
                <Shield size={13} style={{ color: '#4ade80' }} />
                <span>Permissions</span>
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
                    position: 'fixed', bottom: 32, right: 220, zIndex: 40,
                    width: 380, maxHeight: 480,
                    borderRadius: 16, overflow: 'hidden',
                    pointerEvents: 'auto', userSelect: 'none',
                    background: '#0f0f1a', border: '1px solid #14532d',
                    boxShadow: '0 32px 80px rgba(0,0,0,0.75)',
                    fontFamily: 'Inter, system-ui, sans-serif',
                    rotateX, rotateY, transformOrigin, transformStyle: 'preserve-3d',
                    perspective: 1000, willChange: 'transform', backfaceVisibility: 'hidden',
                }}
            >
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', top: 0, left: 0, right: 45, height: 10, cursor: 'grab', zIndex: 50 }} />
                <div style={{ height: 2, background: 'linear-gradient(90deg, transparent, #4ade80, transparent)', opacity: 0.7 }} />

                <div onPointerDown={handlePointerDownHeader} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '12px 16px 10px', borderBottom: '1px solid #14532d',
                    cursor: 'grab', position: 'relative', zIndex: 40
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                        <GripHorizontal size={13} style={{ color: '#166534' }} />
                        <Shield size={14} style={{ color: '#4ade80' }} />
                        <span style={{ fontSize: 13, fontWeight: 700, color: '#dcfce7', letterSpacing: '-0.01em' }}>Permission Center</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <button type="button" onClick={() => { load(); }} title="Refresh"
                            style={{ background: 'none', border: 'none', color: '#166534', cursor: 'pointer', padding: 4, display: 'flex' }}>
                            <RefreshCw size={13} />
                        </button>
                        <button type="button" onClick={() => setIsVisible(false)} title="Close"
                            style={{ background: 'none', border: 'none', color: '#166534', cursor: 'pointer', padding: 4, display: 'flex' }}>
                            <X size={14} />
                        </button>
                    </div>
                </div>

                <div style={{ padding: '10px 16px', display: 'flex', flexDirection: 'column', gap: 8, overflowY: 'auto', maxHeight: 320 }}>
                    {loading && <div style={{ fontSize: 11, color: '#4ade80', fontFamily: 'monospace' }}>Loading…</div>}
                    {permissions.map((p) => {
                        const meta = MODE_META[p.mode] || MODE_META.disabled;
                        const Icon = meta.Icon;
                        return (
                            <div key={p.capability} style={{
                                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                gap: 8, padding: '8px 10px', borderRadius: 10,
                                background: '#141428', border: '1px solid #1e293b'
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                                    <Icon size={13} style={{ color: meta.color, flexShrink: 0 }} />
                                    <div style={{ minWidth: 0 }}>
                                        <div style={{ fontSize: 11, fontWeight: 600, color: '#e2e8f0' }}>{p.label}</div>
                                        <div style={{ fontSize: 10, color: '#64748b', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.description}</div>
                                    </div>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
                                    {p.mode === 'ask' && (
                                        <button type="button" onClick={() => grantApproval(p.capability)} title="Grant 5-min approval"
                                            style={{ background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.4)', color: '#fbbf24', borderRadius: 8, padding: '3px 8px', fontSize: 10, cursor: 'pointer' }}>
                                            Approve 5m
                                        </button>
                                    )}
                                    <button type="button" onClick={() => cycleMode(p.capability, p.mode)} title={`Click to change (now: ${p.mode})`}
                                        style={{ background: 'rgba(74,222,128,0.08)', border: `1px solid ${meta.color}55`, color: meta.color, borderRadius: 8, padding: '3px 8px', fontSize: 10, cursor: 'pointer', fontFamily: 'monospace' }}>
                                        {meta.label}
                                    </button>
                                </div>
                            </div>
                        );
                    })}
                </div>

                <div style={{ padding: '8px 16px 12px', borderTop: '1px solid #1e293b' }}>
                    <div style={{ fontSize: 10, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>Recent activity</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 3, maxHeight: 80, overflowY: 'auto' }}>
                        {audit.length === 0 && <div style={{ fontSize: 10, color: '#475569' }}>No enforcement events yet.</div>}
                        {audit.slice(0, 4).map((a, i) => (
                            <div key={i} style={{ fontSize: 10, color: '#94a3b8', fontFamily: 'monospace' }}>
                                {a.created_at} · {a.capability} · {a.decision}
                            </div>
                        ))}
                    </div>
                </div>
            </motion.div>
        </AnimatePresence>
    );
}
