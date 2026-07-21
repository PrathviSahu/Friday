import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Globe, X, GripHorizontal, ArrowRight, ExternalLink } from 'lucide-react';

const API = 'http://localhost:8000/api/search';

export default function WebSearchCard() {
    const [isVisible, setIsVisible] = useState(false);
    const [query, setQuery] = useState('');
    const [searching, setSearching] = useState(false);
    const [results, setResults] = useState([]);
    const [searchedQuery, setSearchedQuery] = useState('');
    const inputRef = useRef(null);

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
                className="fixed top-20 left-10 z-50 flex items-center gap-2 px-3.5 py-2 rounded-full cursor-grab active:cursor-grabbing pointer-events-auto select-none bg-[#09111e]/90 border border-indigo-500/30 text-indigo-300 shadow-[0_4px_20px_rgba(99,102,241,0.2)] text-[11px] font-mono"
            >
                <Search size={14} className="text-indigo-400" />
                <span>AI Search</span>
            </motion.div>
        );
    }

    return (
        <AnimatePresence>
            <motion.div
                drag
                dragConstraints={{ left: -400, right: 600, top: -200, bottom: 500 }}
                dragElastic={0.1}
                whileDrag={{ scale: 1.02, cursor: 'grabbing' }}
                initial={{ opacity: 0, y: -20, scale: 0.94 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                className="fixed top-20 left-10 z-40 w-80 rounded-2xl pointer-events-auto select-none overflow-hidden bg-[#070c17]/94 border border-indigo-500/30 shadow-[0_20px_60px_rgba(0,0,0,0.85),0_0_24px_rgba(99,102,241,0.15)] backdrop-blur-2xl cursor-grab active:cursor-grabbing font-sans"
            >
                {/* Top ambient glow line */}
                <div className="h-[2px] w-full bg-gradient-to-r from-transparent via-indigo-500 to-transparent opacity-80" />

                <div className="p-4 flex flex-col gap-3">
                    {/* Header bar */}
                    <div className="flex items-center justify-between pb-2 border-b border-indigo-500/20">
                        <div className="flex items-center gap-2 text-indigo-400/70">
                            <GripHorizontal size={13} />
                            <Globe size={14} className="text-indigo-400" />
                            <span className="text-[11px] font-mono tracking-wider font-bold text-indigo-300 uppercase">
                                INLINE AI SEARCH
                            </span>
                        </div>
                        <button
                            onClick={() => setIsVisible(false)}
                            className="p-1 rounded-md text-indigo-400/50 hover:text-indigo-200 hover:bg-indigo-500/10 transition-colors cursor-pointer"
                        >
                            <X size={13} />
                        </button>
                    </div>

                    {/* Search Input bar */}
                    <form onSubmit={handleSearch} className="flex items-center gap-2">
                        <div className="flex-1 flex items-center gap-2 bg-indigo-950/40 border border-indigo-500/25 rounded-xl px-3 py-2 focus-within:border-indigo-400 focus-within:bg-indigo-950/60 transition-all">
                            <Search size={13} className="text-indigo-400 shrink-0" />
                            <input
                                ref={inputRef}
                                type="text"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder={searching ? 'Searching the web…' : 'Ask anything…'}
                                disabled={searching}
                                className="bg-transparent text-xs text-slate-100 placeholder-indigo-300/40 outline-none w-full font-sans cursor-text"
                            />
                        </div>
                        <motion.button
                            type="submit"
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            disabled={!query.trim() || searching}
                            className="p-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all cursor-pointer shadow-md flex items-center justify-center shrink-0"
                        >
                            <ArrowRight size={13} />
                        </motion.button>
                    </form>

                    {/* Search Results list */}
                    <div className="max-h-60 overflow-y-auto flex flex-col gap-2 pr-1 scrollbar-thin scrollbar-thumb-indigo-900">
                        {searching ? (
                            <div className="py-6 text-center text-xs text-indigo-300/60 font-mono animate-pulse">
                                Fetching web answers…
                            </div>
                        ) : results.length > 0 ? (
                            results.map((res, idx) => (
                                <div key={idx} className="p-2.5 rounded-xl bg-indigo-950/30 border border-indigo-500/15 flex flex-col gap-1 text-left">
                                    <div className="text-xs font-semibold text-indigo-200 flex items-center justify-between gap-2">
                                        <span className="truncate">{res.title}</span>
                                        <ExternalLink size={10} className="text-indigo-400 shrink-0 opacity-60" />
                                    </div>
                                    <p className="text-[11px] text-slate-300 leading-snug font-normal line-clamp-3">
                                        {res.snippet}
                                    </p>
                                </div>
                            ))
                        ) : searchedQuery ? (
                            <div className="py-4 text-center text-xs text-indigo-300/50">
                                No instant snippets found for "{searchedQuery}".
                            </div>
                        ) : (
                            <div className="py-4 text-center text-[11px] text-indigo-300/40 italic">
                                Type any query to search instant web snippets.
                            </div>
                        )}
                    </div>
                </div>
            </motion.div>
        </AnimatePresence>
    );
}
