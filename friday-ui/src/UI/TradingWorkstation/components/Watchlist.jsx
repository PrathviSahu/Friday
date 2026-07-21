import React, { useState } from 'react';
import { MARKET_ASSETS } from '../data/marketData';
import { Search, Star, Pin, TrendingUp, TrendingDown, Clock, Filter } from 'lucide-react';

const CATEGORIES = ['All', 'Forex', 'Crypto', 'Stocks', 'Commodities', 'Indices', 'Favorites'];

export default function Watchlist({ selectedSymbol, onSelectSymbol }) {
    const [search, setSearch] = useState('');
    const [category, setCategory] = useState('All');
    const [favorites, setFavorites] = useState(['BTC-USD', 'GC=F', 'RELIANCE.NS']);

    const toggleFav = (symbol, e) => {
        e.stopPropagation();
        setFavorites((prev) =>
            prev.includes(symbol) ? prev.filter((s) => s !== symbol) : [...prev, symbol]
        );
    };

    const filtered = MARKET_ASSETS.filter((item) => {
        const matchesCategory =
            category === 'All'
                ? true
                : category === 'Favorites'
                ? favorites.includes(item.symbol)
                : item.category === category;

        const matchesSearch =
            item.symbol.toLowerCase().includes(search.toLowerCase()) ||
            item.name.toLowerCase().includes(search.toLowerCase());

        return matchesCategory && matchesSearch;
    });

    return (
        <div className="w-64 bg-[#070b14]/90 border-l border-cyan-500/20 flex flex-col h-full select-none backdrop-blur-xl">
            {/* Header & Search */}
            <div className="p-3 border-b border-cyan-500/15 flex flex-col gap-2">
                <div className="flex items-center justify-between">
                    <span className="text-[11px] font-mono font-bold tracking-widest text-cyan-300 uppercase">
                        MARKET WATCHLIST
                    </span>
                    <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                        {filtered.length} ASSETS
                    </span>
                </div>

                <div className="flex items-center gap-1.5 bg-[#0e1626] border border-cyan-500/20 rounded-xl px-2.5 py-1.5 focus-within:border-cyan-400 transition-all">
                    <Search size={12} className="text-cyan-500/60 shrink-0" />
                    <input
                        type="text"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        placeholder="Search symbol, forex, crypto..."
                        className="bg-transparent text-xs text-slate-200 placeholder-slate-500 outline-none w-full font-sans"
                    />
                </div>
            </div>

            {/* Category tabs */}
            <div className="flex gap-1 px-2 py-1.5 border-b border-cyan-500/15 overflow-x-auto scrollbar-none">
                {CATEGORIES.map((cat) => (
                    <button
                        key={cat}
                        onClick={() => setCategory(cat)}
                        className={`text-[9px] font-mono px-2 py-1 rounded-lg shrink-0 transition-all cursor-pointer ${
                            category === cat
                                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/40 font-bold'
                                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                        }`}
                    >
                        {cat}
                    </button>
                ))}
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto pr-0.5 divide-y divide-cyan-500/10 scrollbar-thin scrollbar-thumb-cyan-900">
                {filtered.map((item) => {
                    const isSelected = selectedSymbol === item.symbol;
                    const isPositive = item.changePct >= 0;
                    const isFav = favorites.includes(item.symbol);

                    return (
                        <div
                            key={item.symbol}
                            onClick={() => onSelectSymbol(item.symbol)}
                            className={`p-2.5 flex items-center justify-between cursor-pointer transition-all ${
                                isSelected
                                    ? 'bg-cyan-500/15 border-l-2 border-cyan-400'
                                    : 'hover:bg-cyan-500/5'
                            }`}
                        >
                            {/* Left symbol info */}
                            <div className="flex items-center gap-2 min-w-0">
                                <button
                                    onClick={(e) => toggleFav(item.symbol, e)}
                                    className="text-slate-600 hover:text-amber-400 transition-colors"
                                >
                                    <Star size={11} fill={isFav ? '#f59e0b' : 'none'} color={isFav ? '#f59e0b' : 'currentColor'} />
                                </button>
                                <div className="flex flex-col truncate">
                                    <span className="text-xs font-bold font-mono text-slate-200 truncate">
                                        {item.name}
                                    </span>
                                    <span className="text-[9px] font-mono text-slate-500">
                                        {item.symbol}
                                    </span>
                                </div>
                            </div>

                            {/* Right prices & change */}
                            <div className="flex flex-col items-end shrink-0">
                                <span className="text-xs font-mono font-semibold text-white">
                                    {item.basePrice.toLocaleString()}
                                </span>
                                <div className={`flex items-center gap-0.5 text-[10px] font-mono font-bold ${isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
                                    {isPositive ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
                                    <span>{isPositive ? '+' : ''}{item.changePct}%</span>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
