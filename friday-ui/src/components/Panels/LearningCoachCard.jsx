import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence, useDragControls, useMotionValue, useSpring } from 'framer-motion';
import { Flame, X, GripHorizontal, Plus } from 'lucide-react';
import { useOrbState } from '../../hooks/useOrbState';
import { API_ENDPOINTS } from '../../api/config.js';

const CATEGORIES = ['dsa', 'java', 'system_design', 'aws', 'interview_prep', 'general'];

export default function LearningCoachCard() {
    const { workspace } = useOrbState();
    const [isVisible, setIsVisible] = useState(false);
    const [dashboard, setDashboard] = useState(null);
    const [title, setTitle] = useState('');
    const [category, setCategory] = useState('dsa');
    const [minutes, setMinutes] = useState(30);
    const [solved, setSolved] = useState(0);

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
            const res = await fetch(API_ENDPOINTS.learning);
            if (res.ok) setDashboard(await res.json());
        } catch (_) {}
    };

    useEffect(() => { load(); }, []);

    const logSession = async (e) => {
        e.preventDefault();
        if (!title.trim()) return;
        try {
            await fetch(`${API_ENDPOINTS.learning}/log`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, category, minutes: Number(minutes), solved: Number(solved) }),
            });
            setTitle('');
            setSolved(0);
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
                    position: 'fixed', bottom: 32, left: 40, zIndex: 50,
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '7px 14px', borderRadius: 99,
                    cursor: 'grab', pointerEvents: 'auto', userSelect: 'none',
                    background: '#0f0f1a', border: '1px solid #7c2d12',
                    color: '#fdba74', fontSize: 11, fontFamily: 'monospace',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.6)'
                }}
            >
                <Flame size={13} style={{ color: '#fb923c' }} />
                <span>Coach{dashboard?.streak ? ` 🔥${dashboard.streak}` : ''}</span>
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
                    position: 'fixed', bottom: 32, left: 40, zIndex: 40,
                    width: 320, maxHeight: 520,
                    borderRadius: 16, overflow: 'hidden',
                    pointerEvents: 'auto', userSelect: 'none',
                    background: '#0f0f1a', border: '1px solid #7c2d12',
                    boxShadow: '0 32px 80px rgba(0,0,0,0.75)',
                    fontFamily: 'Inter, system-ui, sans-serif',
                    rotateX, rotateY, transformOrigin, transformStyle: 'preserve-3d',
                    perspective: 1000, willChange: 'transform', backfaceVisibility: 'hidden',
                }}
            >
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', top: 0, left: 0, right: 45, height: 10, cursor: 'grab', zIndex: 50 }} />
                <div style={{ height: 2, background: 'linear-gradient(90deg, transparent, #fb923c, transparent)', opacity: 0.7 }} />

                <div onPointerDown={handlePointerDownHeader} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '12px 16px 10px', borderBottom: '1px solid #7c2d12',
                    cursor: 'grab', position: 'relative', zIndex: 40
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                        <GripHorizontal size={13} style={{ color: '#7c2d12' }} />
                        <Flame size={14} style={{ color: '#fb923c' }} />
                        <span style={{ fontSize: 13, fontWeight: 700, color: '#ffedd5', letterSpacing: '-0.01em' }}>Learning Coach</span>
                        {dashboard?.streak > 0 && (
                            <span style={{ fontSize: 10, background: '#7c2d12', color: '#fed7aa', borderRadius: 99, padding: '1px 7px', fontFamily: 'monospace' }}>{dashboard.streak}-day</span>
                        )}
                    </div>
                    <button type="button" onClick={() => setIsVisible(false)} title="Close"
                        style={{ background: 'none', border: 'none', color: '#7c2d12', cursor: 'pointer', padding: 4, display: 'flex' }}>
                        <X size={14} />
                    </button>
                </div>

                <div style={{ padding: '10px 16px', display: 'flex', flexDirection: 'column', gap: 10, overflowY: 'auto', maxHeight: 420 }}>
                    {/* Today summary */}
                    {dashboard && (
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6 }}>
                            {[
                                { label: 'Today', value: `${dashboard.today_minutes}m` },
                                { label: 'Solved', value: dashboard.today_solved },
                                { label: 'Week', value: `${dashboard.week_minutes}m` },
                            ].map((s) => (
                                <div key={s.label} style={{ background: '#141428', border: '1px solid #1e293b', borderRadius: 10, padding: '8px', textAlign: 'center' }}>
                                    <div style={{ fontSize: 15, fontWeight: 800, color: '#fdba74' }}>{s.value}</div>
                                    <div style={{ fontSize: 9, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{s.label}</div>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Weekly goals */}
                    {dashboard?.weekly_goals?.map((g) => (
                        <div key={g.category}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#94a3b8', marginBottom: 3 }}>
                                <span style={{ fontWeight: 600, color: '#cbd5e1' }}>{g.label}</span>
                                <span style={{ fontFamily: 'monospace' }}>{g.done}/{g.target}</span>
                            </div>
                            <div style={{ height: 4, background: '#1e293b', borderRadius: 99, overflow: 'hidden' }}>
                                <div style={{ height: '100%', width: `${g.pct}%`, background: 'linear-gradient(90deg,#fb923c,#fdba74)', borderRadius: 99 }} />
                            </div>
                        </div>
                    ))}

                    {/* Quick log */}
                    <form onSubmit={logSession} style={{ display: 'flex', flexDirection: 'column', gap: 6, borderTop: '1px solid #1e293b', paddingTop: 10 }}>
                        <div style={{ fontSize: 10, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Log a session</div>
                        <input
                            type="text"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            placeholder="e.g. Two Sum, Spring Boot CRUD…"
                            style={{ background: '#141428', border: '1px solid #1e293b', borderRadius: 8, padding: '7px 10px', color: '#e2e8f0', fontSize: 11, outline: 'none' }}
                        />
                        <div style={{ display: 'flex', gap: 6 }}>
                            <select value={category} onChange={(e) => setCategory(e.target.value)}
                                style={{ background: '#141428', border: '1px solid #1e293b', borderRadius: 8, padding: '6px 8px', color: '#cbd5e1', fontSize: 10, flex: 1 }}>
                                {CATEGORIES.map((c) => <option key={c} value={c}>{c.replace('_', ' ')}</option>)}
                            </select>
                            <input type="number" min={1} value={minutes} onChange={(e) => setMinutes(e.target.value)}
                                title="Minutes" style={{ background: '#141428', border: '1px solid #1e293b', borderRadius: 8, padding: '6px 8px', color: '#cbd5e1', fontSize: 10, width: 56 }} />
                            <input type="number" min={0} value={solved} onChange={(e) => setSolved(e.target.value)}
                                title="Problems solved" style={{ background: '#141428', border: '1px solid #1e293b', borderRadius: 8, padding: '6px 8px', color: '#cbd5e1', fontSize: 10, width: 56 }} />
                        </div>
                        <button type="submit" disabled={!title.trim()}
                            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5, padding: '7px', borderRadius: 8, border: 'none', background: '#9a3412', color: '#fed7aa', fontSize: 11, fontWeight: 600, cursor: 'pointer', opacity: title.trim() ? 1 : 0.4 }}>
                            <Plus size={12} /> Log session
                        </button>
                    </form>

                    {/* Last 7 days */}
                    {dashboard?.last7 && (
                        <div>
                            <div style={{ fontSize: 10, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>Last 7 days</div>
                            <div style={{ display: 'flex', gap: 3, alignItems: 'flex-end', height: 34 }}>
                                {dashboard.last7.map((d) => (
                                    <div key={d.date} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                                        <div style={{ width: '100%', height: Math.max(3, Math.min(26, d.count * 9)), background: d.count ? '#fb923c' : '#1e293b', borderRadius: 3 }} />
                                        <div style={{ fontSize: 8, color: '#475569', fontFamily: 'monospace' }}>{d.date.slice(5)}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </motion.div>
        </AnimatePresence>
    );
}
