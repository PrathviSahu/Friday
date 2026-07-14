import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { searchSymbols, formatSymbol } from '../../services/market';

// Watchlist: live prices, % change, search-to-add, remove. `quotes` is a map of
// symbol -> { price, changePercent }. `selected` is the active symbol.
export default function Watchlist({ symbols, quotes, selected, onSelect, onRemove, onAdd }) {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [searching, setSearching] = useState(false);
    const [open, setOpen] = useState(false);
    const boxRef = useRef(null);

    useEffect(() => {
        const t = setTimeout(async () => {
            const q = query.trim();
            if (q.length < 1) {
                setResults([]);
                return;
            }
            setSearching(true);
            try {
                const r = await searchSymbols(q);
                setResults(r || []);
            } catch {
                setResults([]);
            } finally {
                setSearching(false);
            }
        }, 350);
        return () => clearTimeout(t);
    }, [query]);

    useEffect(() => {
        const onClick = (e) => {
            if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false);
        };
        document.addEventListener('mousedown', onClick);
        return () => document.removeEventListener('mousedown', onClick);
    }, []);

    const pick = (sym) => {
        onAdd(sym);
        setQuery('');
        setResults([]);
        setOpen(false);
    };

    return (
        <div className="w-60 shrink-0 h-full flex flex-col border-r border-[#1e222d] bg-[#0b0e17]">
            <div className="px-3 pt-3 pb-2 flex items-center justify-between">
                <span className="font-orbitron text-[10px] tracking-[0.3em] uppercase text-[#00B7FF]/70">
                    Watchlist
                </span>
                <span className="text-[9px] text-[#00B7FF]/40 tracking-widest">{symbols.length}</span>
            </div>

            {/* Search + add */}
            <div className="px-3 pb-2 relative" ref={boxRef}>
                <input
                    value={query}
                    onChange={(e) => {
                        setQuery(e.target.value);
                        setOpen(true);
                    }}
                    onFocus={() => setOpen(true)}
                    placeholder="Search symbol…"
                    className="w-full bg-[#131722] border border-[#1e222d] rounded px-2 py-1.5 text-[11px] text-[#DFFAFF] outline-none focus:border-[#00B7FF]/50"
                />
                <AnimatePresence>
                    {open && (query.trim().length > 0) && (
                        <motion.div
                            initial={{ opacity: 0, y: -4 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -4 }}
                            className="absolute z-30 left-3 right-3 mt-1 max-h-56 overflow-y-auto rounded border border-[#1e222d] bg-[#131722] shadow-xl"
                        >
                            {searching && <div className="px-2 py-2 text-[10px] text-[#8b93a5]">Searching…</div>}
                            {!searching && results.length === 0 && (
                                <div className="px-2 py-2 text-[10px] text-[#8b93a5]">No matches</div>
                            )}
                            {results.map((r) => (
                                <button
                                    key={r.symbol}
                                    onClick={() => pick(r.symbol)}
                                    className="w-full text-left px-2 py-1.5 hover:bg-[#00B7FF]/10 flex items-center justify-between gap-2"
                                >
                                    <span className="font-grotesk text-[11px] text-[#DFFAFF]">{formatSymbol(r.symbol)}</span>
                                    <span className="text-[9px] text-[#8b93a5] truncate max-w-[90px]">{r.name}</span>
                                </button>
                            ))}
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto px-2 space-y-0.5">
                {symbols.map((sym) => {
                    const q = quotes[sym];
                    const chg = q?.changePercent;
                    const up = chg != null && chg >= 0;
                    const isSel = sym === selected;
                    return (
                        <motion.div
                            key={sym}
                            layout
                            onClick={() => onSelect(sym)}
                            className={`group cursor-pointer flex items-center justify-between px-2 py-1.5 rounded transition ${
                                isSel ? 'bg-[#00B7FF]/15' : 'hover:bg-white/5'
                            }`}
                        >
                            <div className="min-w-0">
                                <div className="font-grotesk text-[12px] text-[#DFFAFF] truncate">{formatSymbol(sym)}</div>
                                <div className="font-grotesk text-[10px] text-[#8b93a5]">
                                    {q?.price != null ? q.price.toLocaleString() : '—'}
                                </div>
                            </div>
                            <div className="flex items-center gap-1">
                                <span
                                    className={`font-grotesk text-[10px] ${
                                        chg == null ? 'text-[#8b93a5]' : up ? 'text-[#26a69a]' : 'text-[#ef5350]'
                                    }`}
                                >
                                    {chg == null ? '—' : `${up ? '+' : ''}${chg.toFixed(2)}%`}
                                </span>
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onRemove(sym);
                                    }}
                                    className="opacity-0 group-hover:opacity-100 text-[#8b93a5] hover:text-[#ef5350] text-xs px-1"
                                    title="Remove"
                                >
                                    ×
                                </button>
                            </div>
                        </motion.div>
                    );
                })}
            </div>
        </div>
    );
}
