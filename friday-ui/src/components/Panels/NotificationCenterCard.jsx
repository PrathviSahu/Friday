import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence, useDragControls, useMotionValue, useSpring } from 'framer-motion';
import { Bell, BellRing, X, GripHorizontal, Sparkles, Check } from 'lucide-react';
import { useOrbState } from '../../hooks/useOrbState';
import { API_ENDPOINTS } from '../../api/config.js';

const CAT_COLORS = {
    briefing: '#a78bfa',
    career: '#38bdf8',
    market: '#4ade80',
    general: '#94a3b8',
};

export default function NotificationCenterCard() {
    const { workspace } = useOrbState();
    const [isVisible, setIsVisible] = useState(false);
    const [notifications, setNotifications] = useState([]);
    const [unread, setUnread] = useState(0);
    const [briefing, setBriefing] = useState(null);

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
            const res = await fetch(API_ENDPOINTS.notifications);
            if (res.ok) {
                const data = await res.json();
                setNotifications(data.notifications || []);
                setUnread(data.unread_count || 0);
            }
        } catch (_) {}
    };

    useEffect(() => {
        load();
        const iv = setInterval(load, 60000); // refresh every minute
        return () => clearInterval(iv);
    }, []);

    const runBriefing = async () => {
        try {
            const res = await fetch(API_ENDPOINTS.briefing);
            if (res.ok) setBriefing(await res.json());
        } catch (_) {}
    };

    const markRead = async (id) => {
        try {
            await fetch(`${API_ENDPOINTS.notifications}/${id}/read`, { method: 'POST' });
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
                    position: 'fixed', bottom: 32, right: 150, zIndex: 50,
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '7px 14px', borderRadius: 99,
                    cursor: 'grab', pointerEvents: 'auto', userSelect: 'none',
                    background: '#0f172a', border: '1px solid #1e3a8a',
                    color: '#93c5fd', fontSize: 11, fontFamily: 'monospace',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.3)'
                }}
            >
                <Bell size={13} style={{ color: '#60a5fa' }} />
                <span>Inbox{unread ? ` (${unread})` : ''}</span>
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
                    position: 'fixed', bottom: 32, right: 150, zIndex: 40,
                    width: 360, maxHeight: 500,
                    borderRadius: 16, overflow: 'hidden',
                    pointerEvents: 'auto', userSelect: 'none',
                    background: '#0f172a', border: '1px solid #1e3a8a',
                    boxShadow: '0 32px 80px rgba(0,0,0,0.4)',
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
                        {unread ? <BellRing size={14} style={{ color: '#60a5fa' }} /> : <Bell size={14} style={{ color: '#60a5fa' }} />}
                        <span style={{ fontSize: 13, fontWeight: 700, color: '#dbeafe', letterSpacing: '-0.01em' }}>Notifications</span>
                        {unread > 0 && (
                            <span style={{ fontSize: 10, background: '#1e3a8a', color: '#bfdbfe', borderRadius: 99, padding: '1px 7px', fontFamily: 'monospace' }}>{unread}</span>
                        )}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <button type="button" onClick={runBriefing} title="Run daily briefing"
                            style={{ background: 'rgba(96,165,250,0.1)', border: '1px solid rgba(96,165,250,0.4)', color: '#93c5fd', borderRadius: 8, padding: '3px 8px', fontSize: 10, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                            <Sparkles size={11} /> Briefing
                        </button>
                        <button type="button" onClick={() => setIsVisible(false)} title="Close"
                            style={{ background: 'none', border: 'none', color: '#1e3a8a', cursor: 'pointer', padding: 4, display: 'flex' }}>
                            <X size={14} />
                        </button>
                    </div>
                </div>

                {briefing && (
                    <div style={{ padding: '10px 16px', borderBottom: '1px solid #1e293b', background: 'rgba(96,165,250,0.06)' }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: '#93c5fd', marginBottom: 4 }}>{briefing.greeting}</div>
                        {briefing.sections.slice(0, 3).map((s) => (
                            <div key={s.title} style={{ fontSize: 10, color: '#94a3b8', marginBottom: 3 }}>
                                <span style={{ color: '#bfdbfe', fontWeight: 600 }}>{s.title}:</span> {s.lines.slice(0, 2).join(' · ')}
                            </div>
                        ))}
                    </div>
                )}

                <div style={{ padding: '10px 16px', display: 'flex', flexDirection: 'column', gap: 8, overflowY: 'auto', maxHeight: 320 }}>
                    {notifications.length === 0 && (
                        <div style={{ fontSize: 11, color: '#475569', textAlign: 'center', padding: '20px 0' }}>
                            No notifications yet. Automations will post here instead of interrupting.
                        </div>
                    )}
                    {notifications.map((n) => (
                        <div key={n.id} style={{
                            display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8,
                            padding: '9px 10px', borderRadius: 10,
                            background: n.is_read ? '#10101c' : '#1e293b',
                            border: `1px solid ${n.is_read ? '#1e293b' : 'rgba(96,165,250,0.35)'}`
                        }}>
                            <div style={{ minWidth: 0 }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                    <span style={{ width: 7, height: 7, borderRadius: 99, background: CAT_COLORS[n.category] || CAT_COLORS.general, flexShrink: 0 }} />
                                    <span style={{ fontSize: 11, fontWeight: 600, color: '#e2e8f0' }}>{n.title}</span>
                                </div>
                                <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 3, lineHeight: 1.4 }}>{n.body}</div>
                                <div style={{ fontSize: 9, color: '#475569', fontFamily: 'monospace', marginTop: 3 }}>{n.created_at}</div>
                            </div>
                            {!n.is_read && (
                                <button type="button" onClick={() => markRead(n.id)} title="Mark read"
                                    style={{ background: 'none', border: 'none', color: '#1d4ed8', cursor: 'pointer', padding: 2, flexShrink: 0 }}>
                                    <Check size={12} />
                                </button>
                            )}
                        </div>
                    ))}
                </div>
            </motion.div>
        </AnimatePresence>
    );
}
