import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence, useDragControls, useMotionValue, useSpring } from 'framer-motion';
import {
    CheckSquare, X, Plus, Trash2, Check,
    GripHorizontal, Flag, ChevronDown, ClipboardList, Pencil
} from 'lucide-react';

const API = 'http://localhost:8000/api/todos';

const PRIORITY_META = {
    high: { color: '#ef4444', label: 'High', dot: 'bg-red-500' },
    normal: { color: '#6366f1', label: 'Normal', dot: 'bg-indigo-400' },
    low: { color: '#6b7280', label: 'Low', dot: 'bg-gray-500' },
};

export default function TodoCard() {
    const [isVisible, setIsVisible] = useState(false);
    const [todos, setTodos] = useState([]);
    const [input, setInput] = useState('');
    const [priority, setPriority] = useState('normal');
    const [showPriority, setShowPriority] = useState(false);
    const [editId, setEditId] = useState(null);
    const [editText, setEditText] = useState('');
    const [filter, setFilter] = useState('all'); // all | active | done
    const inputRef = useRef(null);

    const fetchTodos = async () => {
        try {
            const res = await fetch(API);
            if (res.ok) {
                const data = await res.json();
                setTodos(data.todos);
            }
        } catch (_) { }
    };

    useEffect(() => { fetchTodos(); }, []);

    const addTodo = async (e) => {
        e.preventDefault();
        const text = input.trim();
        if (!text) return;
        try {
            const res = await fetch(API, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, priority }),
            });
            if (res.ok) {
                setInput('');
                fetchTodos();
                inputRef.current?.focus();
            }
        } catch (_) { }
    };

    const toggleTodo = async (id) => {
        try {
            await fetch(`${API}/${id}/toggle`, { method: 'PATCH' });
            fetchTodos();
        } catch (_) { }
    };

    const deleteTodo = async (id) => {
        try {
            await fetch(`${API}/${id}`, { method: 'DELETE' });
            fetchTodos();
        } catch (_) { }
    };

    const clearDone = async () => {
        try {
            await fetch(`${API}/done`, { method: 'DELETE' });
            fetchTodos();
        } catch (_) { }
    };

    const saveEdit = async (id) => {
        const text = editText.trim();
        if (!text) return;
        try {
            await fetch(`${API}/${id}/text`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text }),
            });
            setEditId(null);
            fetchTodos();
        } catch (_) { }
    };

    const filtered = todos.filter(t => {
        if (filter === 'active') return !t.done;
        if (filter === 'done') return t.done;
        return true;
    });

    // ── 3D Liquid Drag & Motion Controls ──
    const [isDragging, setIsDragging] = useState(false);
    const [transformOrigin, setTransformOrigin] = useState('50% 50%');
    const cardRef = useRef(null);

    const dragControls = useDragControls();
    const rawRotateX = useMotionValue(0);
    const rawRotateY = useMotionValue(0);
    const rotateX = useSpring(rawRotateX, { stiffness: 180, damping: 14, mass: 0.35 });
    const rotateY = useSpring(rawRotateY, { stiffness: 180, damping: 14, mass: 0.35 });

    const handlePointerDownHeader = (e) => {
        if (cardRef.current) {
            const rect = cardRef.current.getBoundingClientRect();
            setTransformOrigin(`${e.clientX - rect.left}px ${e.clientY - rect.top}px`);
        }
        setIsDragging(true);
        dragControls.start(e);
    };

    const handleDrag = (_, info) => {
        const vx = info.velocity.x;
        const vy = info.velocity.y;
        const targetTiltX = Math.max(-24, Math.min(24, -vy * 0.045));
        const targetTiltY = Math.max(-24, Math.min(24, vx * 0.045));
        rawRotateX.set(targetTiltX);
        rawRotateY.set(targetTiltY);
    };

    const handleDragEnd = () => {
        setIsDragging(false);
        rawRotateX.set(0);
        rawRotateY.set(0);
    };

    const totalCount = todos.length;
    const doneCount = todos.filter(t => t.done).length;

    if (!isVisible) {
        return (
            <motion.div
                drag
                dragConstraints={{ left: -200, right: 1000, top: -800, bottom: 200 }}
                dragElastic={0.1}
                whileDrag={{ scale: 1.05 }}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setIsVisible(true)}
                className="fixed bottom-8 left-10 z-50 flex items-center gap-2 px-4 py-2.5 rounded-full cursor-grab active:cursor-grabbing pointer-events-auto select-none"
                style={{ background: '#1a1a2e', border: '1px solid #312e81', color: '#a5b4fc', boxShadow: '0 8px 24px rgba(0,0,0,0.5)' }}
            >
                <ClipboardList size={15} />
                <span style={{ fontSize: 12, fontWeight: 600 }}>Tasks{totalCount > 0 ? ` (${totalCount})` : ''}</span>
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
                className="fixed bottom-24 left-10 z-40 w-80 rounded-2xl pointer-events-auto select-none overflow-hidden"
                style={{
                    background: '#0f0f1a',
                    border: '1px solid #1e1b4b',
                    boxShadow: isDragging ? '0 45px 100px rgba(0,0,0,0.9), 0 0 0 1px rgba(255,255,255,0.15)' : '0 32px 80px rgba(0,0,0,0.75)',
                    fontFamily: 'Inter, system-ui, sans-serif',
                    rotateX,
                    rotateY,
                    transformOrigin,
                    transformStyle: 'preserve-3d',
                    perspective: 1000,
                    willChange: 'transform',
                    backfaceVisibility: 'hidden',
                }}
            >
                {/* ── Top edge & side edge drag handle strips ── */}
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 8, cursor: 'grab', zIndex: 50 }} />
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', top: 0, bottom: 0, left: 0, width: 8, cursor: 'grab', zIndex: 50 }} />
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', top: 0, bottom: 0, right: 0, width: 8, cursor: 'grab', zIndex: 50 }} />
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 8, cursor: 'grab', zIndex: 50 }} />

                {/* ── Header ── */}
                <div
                    onPointerDown={handlePointerDownHeader}
                    style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px 10px', borderBottom: '1px solid #1e1b4b', cursor: 'grab', position: 'relative', zIndex: 40 }}
                    className="active:cursor-grabbing"
                >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 7, cursor: 'grab' }}>
                        <GripHorizontal size={13} style={{ color: '#4338ca' }} />
                        <CheckSquare size={15} style={{ color: '#818cf8' }} />
                        <span style={{ fontSize: 13, fontWeight: 700, color: '#e0e7ff', letterSpacing: '-0.01em' }}>Tasks</span>
                        {totalCount > 0 && (
                            <span style={{ fontSize: 10, background: '#312e81', color: '#a5b4fc', borderRadius: 8, padding: '1px 7px', fontWeight: 600 }}>
                                {doneCount}/{totalCount}
                            </span>
                        )}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        {doneCount > 0 && (
                            <motion.button
                                whileHover={{ scale: 1.05 }}
                                onClick={clearDone}
                                title="Clear completed"
                                style={{ fontSize: 10, background: '#1e1b4b', border: '1px solid #312e81', color: '#818cf8', padding: '3px 8px', borderRadius: 6, cursor: 'pointer' }}
                            >
                                Clear done
                            </motion.button>
                        )}
                        <button
                            onClick={() => setIsVisible(false)}
                            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#4338ca', padding: 4, display: 'flex' }}
                            onMouseEnter={e => e.currentTarget.style.color = '#818cf8'}
                            onMouseLeave={e => e.currentTarget.style.color = '#4338ca'}
                        >
                            <X size={14} />
                        </button>
                    </div>
                </div>

                {/* ── Progress bar ── */}
                {totalCount > 0 && (
                    <div style={{ height: 3, background: '#1e1b4b' }}>
                        <motion.div
                            animate={{ width: `${(doneCount / totalCount) * 100}%` }}
                            transition={{ duration: 0.4, ease: 'easeOut' }}
                            style={{ height: '100%', background: 'linear-gradient(90deg, #6366f1, #818cf8)', borderRadius: 2 }}
                        />
                    </div>
                )}

                {/* ── Filter tabs ── */}
                <div style={{ display: 'flex', gap: 4, padding: '8px 16px 0' }}>
                    {['all', 'active', 'done'].map(f => (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            style={{
                                fontSize: 10, fontWeight: 600, padding: '3px 10px', borderRadius: 6, cursor: 'pointer', border: 'none',
                                background: filter === f ? '#312e81' : 'transparent',
                                color: filter === f ? '#a5b4fc' : '#4338ca',
                                textTransform: 'capitalize', transition: 'all 0.15s'
                            }}
                        >
                            {f}
                        </button>
                    ))}
                </div>

                {/* ── Todo List ── */}
                <div style={{ maxHeight: 260, overflowY: 'auto', padding: '8px 12px', scrollbarWidth: 'thin', scrollbarColor: '#312e81 transparent' }}>
                    <AnimatePresence>
                        {filtered.length === 0 ? (
                            <motion.div
                                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                                style={{ textAlign: 'center', padding: '24px 0', color: '#4338ca', fontSize: 12 }}
                            >
                                {filter === 'done' ? 'No completed tasks yet' : 'No tasks yet — add one below!'}
                            </motion.div>
                        ) : filtered.map((todo) => (
                            <motion.div
                                key={todo.id}
                                layout
                                initial={{ opacity: 0, x: -12 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: 12, height: 0, marginBottom: 0 }}
                                transition={{ duration: 0.2 }}
                                style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 8px', borderRadius: 10, marginBottom: 4, background: '#13132a', border: '1px solid #1e1b4b', cursor: 'default' }}
                                onMouseEnter={e => e.currentTarget.style.borderColor = '#312e81'}
                                onMouseLeave={e => e.currentTarget.style.borderColor = '#1e1b4b'}
                            >
                                {/* Checkbox */}
                                <motion.button
                                    whileTap={{ scale: 0.85 }}
                                    onClick={() => toggleTodo(todo.id)}
                                    style={{
                                        width: 18, height: 18, borderRadius: 5, flexShrink: 0, cursor: 'pointer',
                                        border: todo.done ? 'none' : `2px solid ${PRIORITY_META[todo.priority]?.color || '#6366f1'}`,
                                        background: todo.done ? '#6366f1' : 'transparent',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        transition: 'all 0.2s'
                                    }}
                                >
                                    {todo.done && <Check size={11} color="#fff" strokeWidth={3} />}
                                </motion.button>

                                {/* Priority dot */}
                                <div style={{ width: 6, height: 6, borderRadius: '50%', background: PRIORITY_META[todo.priority]?.color || '#6366f1', flexShrink: 0, opacity: todo.done ? 0.3 : 1 }} />

                                {/* Text / Edit */}
                                {editId === todo.id ? (
                                    <input
                                        autoFocus
                                        value={editText}
                                        onChange={e => setEditText(e.target.value)}
                                        onKeyDown={e => { if (e.key === 'Enter') saveEdit(todo.id); if (e.key === 'Escape') setEditId(null); }}
                                        onBlur={() => saveEdit(todo.id)}
                                        style={{ flex: 1, background: '#1e1b4b', border: '1px solid #4338ca', borderRadius: 5, padding: '2px 6px', color: '#e0e7ff', fontSize: 12, outline: 'none' }}
                                    />
                                ) : (
                                    <span
                                        style={{ flex: 1, fontSize: 12, color: todo.done ? '#4338ca' : '#c7d2fe', textDecoration: todo.done ? 'line-through' : 'none', cursor: 'text', transition: 'all 0.2s' }}
                                        onDoubleClick={() => { setEditId(todo.id); setEditText(todo.text); }}
                                    >
                                        {todo.text}
                                    </span>
                                )}

                                {/* Action icons */}
                                <div style={{ display: 'flex', gap: 2, opacity: 0 }} className="todo-actions"
                                    onMouseEnter={e => e.currentTarget.style.opacity = 1}
                                >
                                    <button onClick={() => { setEditId(todo.id); setEditText(todo.text); }}
                                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#4338ca', padding: 3, display: 'flex' }}
                                        onMouseEnter={e => e.currentTarget.style.color = '#818cf8'}
                                        onMouseLeave={e => e.currentTarget.style.color = '#4338ca'}>
                                        <Pencil size={11} />
                                    </button>
                                    <button onClick={() => deleteTodo(todo.id)}
                                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#4338ca', padding: 3, display: 'flex' }}
                                        onMouseEnter={e => e.currentTarget.style.color = '#ef4444'}
                                        onMouseLeave={e => e.currentTarget.style.color = '#4338ca'}>
                                        <Trash2 size={11} />
                                    </button>
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>

                {/* ── Add Task Input ── */}
                <div style={{ padding: '8px 12px 12px', borderTop: '1px solid #1e1b4b' }}>
                    <form onSubmit={addTodo} style={{ display: 'flex', gap: 6 }}>
                        {/* Priority selector */}
                        <div style={{ position: 'relative' }}>
                            <button
                                type="button"
                                onClick={() => setShowPriority(s => !s)}
                                style={{ height: 34, width: 34, borderRadius: 8, background: '#13132a', border: '1px solid #312e81', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}
                            >
                                <div style={{ width: 8, height: 8, borderRadius: '50%', background: PRIORITY_META[priority].color }} />
                            </button>
                            <AnimatePresence>
                                {showPriority && (
                                    <motion.div
                                        initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 6 }}
                                        style={{ position: 'absolute', bottom: 38, left: 0, background: '#13132a', border: '1px solid #312e81', borderRadius: 8, padding: '4px', zIndex: 10, minWidth: 90 }}
                                    >
                                        {Object.entries(PRIORITY_META).map(([k, v]) => (
                                            <button key={k} type="button"
                                                onClick={() => { setPriority(k); setShowPriority(false); }}
                                                style={{ display: 'flex', alignItems: 'center', gap: 6, width: '100%', padding: '5px 8px', background: priority === k ? '#1e1b4b' : 'none', border: 'none', borderRadius: 5, cursor: 'pointer', color: priority === k ? '#a5b4fc' : '#818cf8', fontSize: 11, fontWeight: 600 }}
                                            >
                                                <div style={{ width: 7, height: 7, borderRadius: '50%', background: v.color }} />
                                                {v.label}
                                            </button>
                                        ))}
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>

                        {/* Text input */}
                        <input
                            ref={inputRef}
                            type="text"
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            placeholder="Add a task…"
                            style={{
                                flex: 1, height: 34, background: '#13132a', border: '1px solid #312e81',
                                borderRadius: 8, padding: '0 10px', color: '#e0e7ff', fontSize: 12, outline: 'none',
                                fontFamily: 'inherit'
                            }}
                            onFocus={e => e.target.style.borderColor = '#6366f1'}
                            onBlur={e => e.target.style.borderColor = '#312e81'}
                        />

                        {/* Add button */}
                        <motion.button
                            type="submit"
                            whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                            disabled={!input.trim()}
                            style={{ height: 34, width: 34, borderRadius: 8, background: input.trim() ? '#4f46e5' : '#1e1b4b', border: 'none', cursor: input.trim() ? 'pointer' : 'default', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, transition: 'background 0.2s' }}
                        >
                            <Plus size={16} color={input.trim() ? '#fff' : '#4338ca'} />
                        </motion.button>
                    </form>
                </div>

                {/* Hover-reveal action CSS */}
                <style>{`
                    .todo-actions { opacity: 0 !important; transition: opacity 0.15s; }
                    [style*="background: #13132a"]:hover .todo-actions { opacity: 1 !important; }
                `}</style>
            </motion.div>
        </AnimatePresence>
    );
}
