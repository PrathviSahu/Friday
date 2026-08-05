import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence, useDragControls, useMotionValue, useSpring } from 'framer-motion';
import { BookOpen, X, GripHorizontal, Search, Plus, Trash2, Flame, Target } from 'lucide-react';
import { useOrbState } from '../../hooks/useOrbState';
import { API_ENDPOINTS } from '../../api/config.js';

const TABS = [
    { key: 'notes',    label: 'Notes',    Icon: BookOpen },
    { key: 'timeline', label: 'Timeline', Icon: Flame },
    { key: 'goals',    label: 'Goals',    Icon: Target },
];

export default function KnowledgeCard() {
    const { workspace } = useOrbState();
    const [isVisible, setIsVisible] = useState(false);
    const [tab, setTab] = useState('notes');

    // Notes
    const [notes, setNotes] = useState([]);
    const [noteTypes, setNoteTypes] = useState([]);
    const [noteTitle, setNoteTitle] = useState('');
    const [noteContent, setNoteContent] = useState('');
    const [noteType, setNoteType] = useState('');
    const [noteQuery, setNoteQuery] = useState('');
    const [searchAnswer, setSearchAnswer] = useState('');

    // Timeline
    const [timeline, setTimeline] = useState([]);
    const [tlEvent, setTlEvent] = useState('');
    const [tlCategory, setTlCategory] = useState('milestone');
    const [tlSummary, setTlSummary] = useState('');

    // Goals
    const [goals, setGoals] = useState([]);
    const [goalTitle, setGoalTitle] = useState('');
    const [goalTarget, setGoalTarget] = useState(100);

    const [isDragging, setIsDragging] = useState(false);
    const [transformOrigin, setTransformOrigin] = useState('50% 50%');
    const cardRef = React.useRef(null);
    const dragControls = useDragControls();
    const rawRotateX = useMotionValue(0);
    const rawRotateY = useMotionValue(0);
    const rotateX = useSpring(rawRotateX, { stiffness: 180, damping: 14, mass: 0.35 });
    const rotateY = useSpring(rawRotateY, { stiffness: 180, damping: 14, mass: 0.35 });

    const loadNotes = async () => {
        try {
            const res = await fetch(API_ENDPOINTS.knowledge);
            if (res.ok) {
                const d = await res.json();
                setNotes(d.notes || []);
                setNoteTypes(d.types || []);
            }
        } catch (_) {}
    };

    const loadTimeline = async () => {
        try {
            const res = await fetch(API_ENDPOINTS.timeline);
            if (res.ok) setTimeline((await res.json()).events || []);
        } catch (_) {}
    };

    const loadGoals = async () => {
        try {
            const res = await fetch(API_ENDPOINTS.goals);
            if (res.ok) setGoals((await res.json()).goals || []);
        } catch (_) {}
    };

    useEffect(() => { loadNotes(); }, []);

    const switchTab = (key) => {
        setTab(key);
        if (key === 'notes' && !notes.length) loadNotes();
        if (key === 'timeline') loadTimeline();
        if (key === 'goals') loadGoals();
    };

    const addNote = async (e) => {
        e.preventDefault();
        if (!noteTitle.trim()) return;
        try {
            await fetch(API_ENDPOINTS.knowledge, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: noteTitle, content: noteContent, note_type: noteType || null }),
            });
            setNoteTitle(''); setNoteContent(''); setNoteType('');
            loadNotes();
        } catch (_) {}
    };

    const searchNotes = async (e) => {
        e.preventDefault();
        if (!noteQuery.trim()) return;
        try {
            const res = await fetch(`${API_ENDPOINTS.knowledge}/search?q=${encodeURIComponent(noteQuery)}`);
            if (res.ok) {
                const d = await res.json();
                setSearchAnswer(d.answer || '');
                if (d.matches?.length) setNotes(d.matches);
            }
        } catch (_) {}
    };

    const deleteNote = async (id) => {
        try {
            await fetch(`${API_ENDPOINTS.knowledge}/${id}`, { method: 'DELETE' });
            setSearchAnswer('');
            loadNotes();
        } catch (_) {}
    };

    const addTimelineEvent = async (e) => {
        e.preventDefault();
        if (!tlEvent.trim()) return;
        try {
            await fetch(API_ENDPOINTS.timeline, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ event: tlEvent, category: tlCategory }),
            });
            setTlEvent('');
            loadTimeline();
        } catch (_) {}
    };

    const runTimelineSummary = async (q) => {
        try {
            const res = await fetch(`${API_ENDPOINTS.timeline}/summary?query=${encodeURIComponent(q)}`);
            if (res.ok) setTlSummary((await res.json()).summary || '');
        } catch (_) {}
    };

    const addGoal = async (e) => {
        e.preventDefault();
        if (!goalTitle.trim()) return;
        try {
            await fetch(API_ENDPOINTS.goals, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: goalTitle, target_value: Number(goalTarget), unit: '%' }),
            });
            setGoalTitle(''); setGoalTarget(100);
            loadGoals();
        } catch (_) {}
    };

    const bumpGoal = async (id) => {
        try {
            await fetch(`${API_ENDPOINTS.goals}/${id}/progress?amount=1`, { method: 'POST' });
            loadGoals();
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
                    position: 'fixed', top: 80, left: 220, zIndex: 50,
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '7px 14px', borderRadius: 99,
                    cursor: 'grab', pointerEvents: 'auto', userSelect: 'none',
                    background: '#0f172a', border: '1px solid #475569',
                    color: '#cbd5e1', fontSize: 11, fontFamily: 'monospace',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.3)'
                }}
            >
                <BookOpen size={13} style={{ color: '#94a3b8' }} />
                <span>Knowledge</span>
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
                    position: 'fixed', top: 80, left: 220, zIndex: 40,
                    width: 400, maxHeight: 540,
                    borderRadius: 16, overflow: 'hidden',
                    pointerEvents: 'auto', userSelect: 'none',
                    background: '#0f172a', border: '1px solid #475569',
                    boxShadow: '0 32px 80px rgba(0,0,0,0.4)',
                    fontFamily: 'Inter, system-ui, sans-serif',
                    rotateX, rotateY, transformOrigin, transformStyle: 'preserve-3d',
                    perspective: 1000, willChange: 'transform', backfaceVisibility: 'hidden',
                }}
            >
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', top: 0, left: 0, right: 45, height: 10, cursor: 'grab', zIndex: 50 }} />
                <div style={{ height: 2, background: 'linear-gradient(90deg, transparent, #818cf8, transparent)', opacity: 0.7 }} />

                <div onPointerDown={handlePointerDownHeader} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '12px 16px 10px', borderBottom: '1px solid #475569',
                    cursor: 'grab', position: 'relative', zIndex: 40
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                        <GripHorizontal size={13} style={{ color: '#475569' }} />
                        <BookOpen size={14} style={{ color: '#94a3b8' }} />
                        <span style={{ fontSize: 13, fontWeight: 700, color: '#e2e8f0', letterSpacing: '-0.01em' }}>Knowledge OS</span>
                    </div>
                    <button type="button" onClick={() => setIsVisible(false)} title="Close"
                        style={{ background: 'none', border: 'none', color: '#475569', cursor: 'pointer', padding: 4, display: 'flex' }}>
                        <X size={14} />
                    </button>
                </div>

                {/* Tabs */}
                <div style={{ display: 'flex', gap: 4, padding: '8px 12px 0', borderBottom: '1px solid #334155' }}>
                    {TABS.map(({ key, label, Icon }) => (
                        <button key={key} type="button" onClick={() => switchTab(key)}
                            style={{
                                display: 'flex', alignItems: 'center', gap: 5, padding: '6px 10px',
                                border: 'none', borderRadius: '8px 8px 0 0', cursor: 'pointer',
                                background: tab === key ? '#1e293b' : 'transparent',
                                color: tab === key ? '#e2e8f0' : '#6366f1', fontSize: 10.5, fontWeight: 600,
                            }}>
                            <Icon size={11} /> {label}
                        </button>
                    ))}
                </div>

                <div style={{ padding: '12px 16px', overflowY: 'auto', maxHeight: 420, minHeight: 140 }}>

                    {tab === 'notes' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                            {/* Search */}
                            <form onSubmit={searchNotes} style={{ display: 'flex', gap: 6 }}>
                                <input type="text" value={noteQuery} onChange={(e) => setNoteQuery(e.target.value)}
                                    placeholder='"where did I save that Kafka idea?"'
                                    style={{ flex: 1, background: '#1e293b', border: '1px solid #475569', borderRadius: 8, padding: '7px 10px', color: '#e2e8f0', fontSize: 11, outline: 'none' }} />
                                <button type="submit" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0 12px', borderRadius: 8, border: 'none', background: '#475569', color: '#e2e8f0', cursor: 'pointer' }}>
                                    <Search size={12} />
                                </button>
                            </form>
                            {searchAnswer && (
                                <div style={{ fontSize: 11, color: '#cbd5e1', background: 'rgba(100,116,139,0.12)', border: '1px solid #475569', borderRadius: 8, padding: '8px 10px' }}>
                                    {searchAnswer}
                                </div>
                            )}

                            {/* Add note */}
                            <form onSubmit={addNote} style={{ display: 'flex', flexDirection: 'column', gap: 5, borderTop: '1px solid #334155', paddingTop: 10 }}>
                                <div style={{ fontSize: 10, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Capture / idea</div>
                                <div style={{ display: 'flex', gap: 6 }}>
                                    <input type="text" value={noteTitle} onChange={(e) => setNoteTitle(e.target.value)}
                                        placeholder="Title"
                                        style={{ flex: 1, background: '#1e293b', border: '1px solid #475569', borderRadius: 8, padding: '6px 10px', color: '#e2e8f0', fontSize: 11, outline: 'none' }} />
                                    <select value={noteType} onChange={(e) => setNoteType(e.target.value)}
                                        style={{ background: '#1e293b', border: '1px solid #475569', borderRadius: 8, padding: '6px 8px', color: '#cbd5e1', fontSize: 10 }}>
                                        <option value="">auto</option>
                                        {noteTypes.map((t) => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
                                    </select>
                                </div>
                                <textarea value={noteContent} onChange={(e) => setNoteContent(e.target.value)} rows={2}
                                    placeholder="Content… (FRIDAY auto-categorizes)"
                                    style={{ background: '#1e293b', border: '1px solid #475569', borderRadius: 8, padding: '6px 10px', color: '#e2e8f0', fontSize: 11, outline: 'none', resize: 'vertical' }} />
                                <button type="submit" disabled={!noteTitle.trim()}
                                    style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5, padding: '7px', borderRadius: 8, border: 'none', background: '#475569', color: '#e2e8f0', fontSize: 11, fontWeight: 600, cursor: 'pointer', opacity: noteTitle.trim() ? 1 : 0.4 }}>
                                    <Plus size={12} /> Save note
                                </button>
                            </form>

                            {/* Note list */}
                            {notes.map((n) => (
                                <div key={n.id} style={{ background: '#10101c', border: '1px solid #334155', borderRadius: 10, padding: '9px 10px' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                                        <span style={{ fontSize: 11.5, fontWeight: 600, color: '#e2e8f0' }}>{n.title}</span>
                                        <button type="button" onClick={() => deleteNote(n.id)} title="Delete"
                                            style={{ background: 'none', border: 'none', color: '#475569', cursor: 'pointer', padding: 2 }}>
                                            <Trash2 size={11} />
                                        </button>
                                    </div>
                                    {n.content && <div style={{ fontSize: 10.5, color: '#94a3b8', marginTop: 3, lineHeight: 1.4 }}>{n.content.slice(0, 140)}</div>}
                                    <div style={{ display: 'flex', gap: 5, marginTop: 5 }}>
                                        <span style={{ fontSize: 9, color: '#94a3b8', background: 'rgba(129,140,248,0.12)', borderRadius: 99, padding: '1px 7px', fontFamily: 'monospace' }}>{n.type}</span>
                                        {n.project && <span style={{ fontSize: 9, color: '#cbd5e1', background: 'rgba(99,102,241,0.12)', borderRadius: 99, padding: '1px 7px', fontFamily: 'monospace' }}>{n.project}</span>}
                                        {n.tags?.map((t) => <span key={t} style={{ fontSize: 9, color: '#64748b', fontFamily: 'monospace' }}>#{t}</span>)}
                                    </div>
                                </div>
                            ))}
                            {!notes.length && !searchAnswer && (
                                <div style={{ fontSize: 11, color: '#475569', textAlign: 'center', padding: '16px 0' }}>
                                    Second brain is empty. Capture ideas — "Friday, remember this idea…"
                                </div>
                            )}
                        </div>
                    )}

                    {tab === 'timeline' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                            <div style={{ display: 'flex', gap: 6 }}>
                                <button type="button" onClick={() => runTimelineSummary('last month')}
                                    style={{ flex: 1, padding: '6px 8px', borderRadius: 8, border: '1px solid #475569', background: 'transparent', color: '#cbd5e1', fontSize: 10, cursor: 'pointer' }}>What changed last month?</button>
                                <button type="button" onClick={() => runTimelineSummary('this year')}
                                    style={{ flex: 1, padding: '6px 8px', borderRadius: 8, border: '1px solid #475569', background: 'transparent', color: '#cbd5e1', fontSize: 10, cursor: 'pointer' }}>Progress this year</button>
                            </div>
                            {tlSummary && (
                                <div style={{ fontSize: 11, color: '#cbd5e1', background: 'rgba(100,116,139,0.12)', border: '1px solid #475569', borderRadius: 8, padding: '8px 10px', lineHeight: 1.5 }}>
                                    {tlSummary}
                                </div>
                            )}

                            <form onSubmit={addTimelineEvent} style={{ display: 'flex', gap: 6, borderTop: '1px solid #334155', paddingTop: 10 }}>
                                <input type="text" value={tlEvent} onChange={(e) => setTlEvent(e.target.value)}
                                    placeholder="e.g. Finished AI Attendance System"
                                    style={{ flex: 1, background: '#1e293b', border: '1px solid #475569', borderRadius: 8, padding: '6px 10px', color: '#e2e8f0', fontSize: 11, outline: 'none' }} />
                                <select value={tlCategory} onChange={(e) => setTlCategory(e.target.value)}
                                    style={{ background: '#1e293b', border: '1px solid #475569', borderRadius: 8, padding: '6px 8px', color: '#cbd5e1', fontSize: 10 }}>
                                    {['career', 'learning', 'project', 'skill', 'milestone', 'personal'].map((c) => <option key={c}>{c}</option>)}
                                </select>
                                <button type="submit" disabled={!tlEvent.trim()}
                                    style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0 12px', borderRadius: 8, border: 'none', background: '#475569', color: '#e2e8f0', cursor: 'pointer', opacity: tlEvent.trim() ? 1 : 0.4 }}>
                                    <Plus size={12} />
                                </button>
                            </form>

                            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                {timeline.slice(0, 15).map((e) => (
                                    <div key={e.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 10.5 }}>
                                        <span style={{ color: '#6366f1', fontFamily: 'monospace', width: 78, flexShrink: 0 }}>{e.event_date}</span>
                                        <span style={{ color: '#94a3b8', fontSize: 9, fontFamily: 'monospace', width: 70, flexShrink: 0 }}>{e.category}</span>
                                        <span style={{ color: '#cbd5e1' }}>{e.event}</span>
                                    </div>
                                ))}
                                {!timeline.length && <div style={{ fontSize: 11, color: '#475569', textAlign: 'center', padding: '12px 0' }}>No milestones yet — log your wins and FRIDAY remembers them.</div>}
                            </div>
                        </div>
                    )}

                    {tab === 'goals' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                            <form onSubmit={addGoal} style={{ display: 'flex', gap: 6, borderBottom: '1px solid #334155', paddingBottom: 10 }}>
                                <input type="text" value={goalTitle} onChange={(e) => setGoalTitle(e.target.value)}
                                    placeholder="e.g. Get 8 LPA job"
                                    style={{ flex: 1, background: '#1e293b', border: '1px solid #475569', borderRadius: 8, padding: '6px 10px', color: '#e2e8f0', fontSize: 11, outline: 'none' }} />
                                <input type="number" min={1} value={goalTarget} onChange={(e) => setGoalTarget(e.target.value)}
                                    title="Target"
                                    style={{ background: '#1e293b', border: '1px solid #475569', borderRadius: 8, padding: '6px 8px', color: '#cbd5e1', fontSize: 11, width: 60 }} />
                                <button type="submit" disabled={!goalTitle.trim()}
                                    style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0 12px', borderRadius: 8, border: 'none', background: '#475569', color: '#e2e8f0', cursor: 'pointer', opacity: goalTitle.trim() ? 1 : 0.4 }}>
                                    <Plus size={12} />
                                </button>
                            </form>
                            {goals.map((g) => (
                                <div key={g.id} style={{ background: '#10101c', border: '1px solid #334155', borderRadius: 10, padding: '10px' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                                        <div>
                                            <span style={{ fontSize: 12, fontWeight: 600, color: '#e2e8f0' }}>{g.title}</span>
                                            {g.deadline && <span style={{ fontSize: 9, color: '#64748b', marginLeft: 6, fontFamily: 'monospace' }}>by {g.deadline}</span>}
                                        </div>
                                        <span style={{ fontSize: 11, fontWeight: 700, color: g.progress_pct >= 100 ? '#4ade80' : '#94a3b8', fontFamily: 'monospace' }}>{g.progress_pct}%</span>
                                    </div>
                                    <div style={{ height: 5, background: '#334155', borderRadius: 99, overflow: 'hidden', marginTop: 7 }}>
                                        <div style={{ height: '100%', width: `${g.progress_pct}%`, background: g.progress_pct >= 100 ? '#22c55e' : 'linear-gradient(90deg,#6366f1,#a5b4fc)', borderRadius: 99 }} />
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 7 }}>
                                        <div style={{ display: 'flex', gap: 5 }}>
                                            {g.skill_gaps?.slice(0, 3).map((s) => (
                                                <span key={s} style={{ fontSize: 9, color: '#f59e0b', background: 'rgba(245,158,11,0.1)', borderRadius: 99, padding: '1px 7px', fontFamily: 'monospace' }}>{s}</span>
                                            ))}
                                        </div>
                                        <button type="button" onClick={() => bumpGoal(g.id)} disabled={g.progress_pct >= 100}
                                            style={{ padding: '3px 10px', borderRadius: 8, border: 'none', background: g.progress_pct >= 100 ? '#14532d' : '#475569', color: g.progress_pct >= 100 ? '#4ade80' : '#e2e8f0', fontSize: 10, fontWeight: 600, cursor: g.progress_pct >= 100 ? 'default' : 'pointer' }}>
                                            {g.progress_pct >= 100 ? '✓ Done' : '+1 progress'}
                                        </button>
                                    </div>
                                </div>
                            ))}
                            {!goals.length && (
                                <div style={{ fontSize: 11, color: '#475569', textAlign: 'center', padding: '12px 0' }}>
                                    Set a goal — "Friday, add goal: Get 8 LPA job". Then track progress by voice.
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </motion.div>
        </AnimatePresence>
    );
}
