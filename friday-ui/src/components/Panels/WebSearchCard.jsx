import React, { useState, useRef } from 'react';
import { motion, AnimatePresence, useDragControls, useMotionValue, useSpring } from 'framer-motion';
import { Search, Globe, X, GripHorizontal, ArrowRight, ExternalLink } from 'lucide-react';
import { useOrbState } from '../../hooks/useOrbState';

const API = 'http://localhost:8000/api/search';

export default function WebSearchCard() {
    const { workspace } = useOrbState();
    const [isVisible, setIsVisible] = useState(false);
    const [query, setQuery] = useState('');
    const [searching, setSearching] = useState(false);
    const [results, setResults] = useState([]);
    const [searchedQuery, setSearchedQuery] = useState('');
    const inputRef = useRef(null);

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
        rawRotateX.set(Math.max(-24, Math.min(24, -info.velocity.y * 0.045)));
        rawRotateY.set(Math.max(-24, Math.min(24, info.velocity.x * 0.045)));
    };

    const handleDragEnd = () => {
        setIsDragging(false);
        rawRotateX.set(0);
        rawRotateY.set(0);
    };

    if (workspace === 'trading') return null;

    const handleSearch = async (e) => {
        if (e) e.preventDefault();
        const q = query.trim();
        if (!q) return;
        setSearching(true);
        setSearchedQuery(q);
        try {
            const res = await fetch(API, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: q }),
            });
            if (res.ok) {
                const data = await res.json();
                setResults(data.results || []);
            }
        } catch (_) {}
        setSearching(false);
    };

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
                    position: 'fixed', top: 80, left: 40, zIndex: 50,
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '7px 14px', borderRadius: 99,
                    cursor: 'grab', pointerEvents: 'auto', userSelect: 'none',
                    background: '#0f0f1a', border: '1px solid #1e1b4b',
                    color: '#a5b4fc', fontSize: 11, fontFamily: 'monospace',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.6)'
                }}
            >
                <Search size={13} style={{ color: '#818cf8' }} />
                <span>AI Search</span>
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
                    position: 'fixed', top: 80, left: 40, zIndex: 40,
                    width: 320,
                    borderRadius: 16,
                    pointerEvents: 'auto',
                    userSelect: 'none',
                    overflow: 'hidden',
                    background: '#0f0f1a',
                    border: '1px solid #1e1b4b',
                    boxShadow: isDragging
                        ? '0 45px 100px rgba(0,0,0,0.9), 0 0 0 1px rgba(255,255,255,0.15)'
                        : '0 32px 80px rgba(0,0,0,0.75)',
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
                {/* Drag handle strips — 45px clear zone at top-right for X button */}
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', top: 0, left: 0, right: 45, height: 10, cursor: 'grab', zIndex: 50 }} />
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', top: 0, bottom: 0, left: 0, width: 10, cursor: 'grab', zIndex: 50 }} />
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', top: 35, bottom: 0, right: 0, width: 10, cursor: 'grab', zIndex: 50 }} />
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 10, cursor: 'grab', zIndex: 50 }} />

                {/* Top glow line */}
                <div style={{ height: 2, background: 'linear-gradient(90deg, transparent, #818cf8, transparent)', opacity: 0.7 }} />

                {/* Header */}
                <div
                    onPointerDown={handlePointerDownHeader}
                    style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                        padding: '12px 16px 10px',
                        borderBottom: '1px solid #1e1b4b',
                        cursor: 'grab',
                        position: 'relative', zIndex: 40
                    }}
                    className="active:cursor-grabbing"
                >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                        <GripHorizontal size={13} style={{ color: '#312e81' }} />
                        <Globe size={14} style={{ color: '#818cf8' }} />
                        <span style={{ fontSize: 13, fontWeight: 700, color: '#e0e7ff', letterSpacing: '-0.01em' }}>AI Search</span>
                    </div>
                    <button
                        type="button"
                        onPointerDown={(e) => e.stopPropagation()}
                        onPointerUp={(e) => e.stopPropagation()}
                        onClick={(e) => {
                            e.stopPropagation();
                            e.preventDefault();
                            setIsVisible(false);
                        }}
                        style={{
                            background: 'none', border: 'none', cursor: 'pointer',
                            color: '#312e81', padding: 4, display: 'flex',
                            position: 'relative', zIndex: 100
                        }}
                        onMouseEnter={e => e.currentTarget.style.color = '#818cf8'}
                        onMouseLeave={e => e.currentTarget.style.color = '#312e81'}
                        title="Close AI Search"
                    >
                        <X size={14} />
                    </button>
                </div>

                {/* Body */}
                <div style={{ padding: '14px 16px 16px', display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {/* Search input */}
                    <form onSubmit={handleSearch} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{
                            flex: 1, display: 'flex', alignItems: 'center', gap: 8,
                            background: '#141428', border: '1px solid #1e1b4b',
                            borderRadius: 10, padding: '8px 12px'
                        }}>
                            <Search size={13} style={{ color: '#6366f1', flexShrink: 0 }} />
                            <input
                                ref={inputRef}
                                type="text"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder={searching ? 'Searching…' : 'Ask anything…'}
                                disabled={searching}
                                style={{
                                    background: 'transparent', border: 'none', outline: 'none',
                                    color: '#e0e7ff', fontSize: 12, fontFamily: 'Inter, system-ui',
                                    width: '100%', cursor: 'text'
                                }}
                            />
                        </div>
                        <motion.button
                            type="submit"
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            disabled={!query.trim() || searching}
                            style={{
                                padding: '8px 10px', borderRadius: 10,
                                background: '#4338ca', border: 'none', color: '#fff',
                                cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                                flexShrink: 0, opacity: (!query.trim() || searching) ? 0.3 : 1,
                            }}
                        >
                            <ArrowRight size={13} />
                        </motion.button>
                    </form>

                    {/* Results */}
                    <div style={{ maxHeight: 220, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
                        {searching ? (
                            <div style={{ padding: '20px 0', textAlign: 'center', fontSize: 11, color: '#6366f1', fontFamily: 'monospace' }}>
                                Searching the web…
                            </div>
                        ) : results.length > 0 ? (
                            results.map((res, idx) => (
                                <div key={idx} style={{
                                    padding: '10px 12px', borderRadius: 10,
                                    background: '#141428', border: '1px solid #1e1b4b',
                                    display: 'flex', flexDirection: 'column', gap: 4
                                }}>
                                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                                        <span style={{ fontSize: 12, fontWeight: 600, color: '#c7d2fe', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                            {res.title}
                                        </span>
                                        <ExternalLink size={10} style={{ color: '#6366f1', flexShrink: 0, opacity: 0.6 }} />
                                    </div>
                                    <p style={{ fontSize: 11, color: '#94a3b8', lineHeight: 1.5, margin: 0,
                                        display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                                        {res.snippet}
                                    </p>
                                </div>
                            ))
                        ) : searchedQuery ? (
                            <div style={{ padding: '16px 0', textAlign: 'center', fontSize: 11, color: '#4338ca' }}>
                                No results found for "{searchedQuery}".
                            </div>
                        ) : (
                            <div style={{ padding: '16px 0', textAlign: 'center', fontSize: 11, color: '#312e81', fontStyle: 'italic' }}>
                                Type any query to search the web.
                            </div>
                        )}
                    </div>
                </div>
            </motion.div>
        </AnimatePresence>
    );
}
