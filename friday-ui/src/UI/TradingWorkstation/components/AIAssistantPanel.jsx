import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { TECHNICAL_INDICATORS, AI_PATTERNS, ECONOMIC_NEWS } from '../data/marketData';
import { Cpu, Brain, Zap, TrendingUp, AlertTriangle, ShieldCheck, Newspaper, Calendar, CheckCircle2 } from 'lucide-react';

export default function AIAssistantPanel({ symbol, currentPrice }) {
    const [tab, setTab] = useState('sentiment'); // sentiment | patterns | trade | news

    return (
        <div className="w-72 bg-[#070b14]/95 border-l border-cyan-500/20 flex flex-col h-full select-none backdrop-blur-xl">
            {/* Header */}
            <div className="p-3 border-b border-cyan-500/15 flex items-center justify-between">
                <div className="flex items-center gap-1.5 font-mono text-[11px] font-bold text-cyan-300">
                    <Brain size={14} className="text-cyan-400 animate-pulse" />
                    <span>F.R.I.D.A.Y. AI ASSISTANT</span>
                </div>
                <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                    LIVE NEURAL
                </span>
            </div>

            {/* Navigation Tabs */}
            <div className="grid grid-cols-4 gap-1 p-2 border-b border-cyan-500/15 text-[9px] font-mono">
                {[
                    { id: 'sentiment', label: 'Sentiment' },
                    { id: 'patterns', label: 'Patterns' },
                    { id: 'trade', label: 'Setup' },
                    { id: 'news', label: 'Calendar' },
                ].map((t) => (
                    <button
                        key={t.id}
                        onClick={() => setTab(t.id)}
                        className={`py-1 rounded-lg text-center transition-all cursor-pointer ${
                            tab === t.id
                                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/40 font-bold'
                                : 'text-slate-400 hover:text-slate-200'
                        }`}
                    >
                        {t.label}
                    </button>
                ))}
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-3 font-sans text-xs scrollbar-thin scrollbar-thumb-cyan-900">
                {/* ── Tab 1: Sentiment & Structure ── */}
                {tab === 'sentiment' && (
                    <div className="flex flex-col gap-3">
                        {/* Overall Sentiment */}
                        <div className="p-3 rounded-xl bg-cyan-950/30 border border-cyan-500/20 flex flex-col gap-2">
                            <div className="flex items-center justify-between text-[10px] font-mono">
                                <span className="text-slate-400 uppercase">AI Market Sentiment</span>
                                <span className="text-emerald-400 font-bold">BULLISH 88%</span>
                            </div>
                            <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                                <div className="h-full bg-gradient-to-r from-emerald-500 to-cyan-400 rounded-full w-[88%]" />
                            </div>
                        </div>

                        {/* Smart Money Concepts (SMC) Structure */}
                        <div className="flex flex-col gap-1.5">
                            <span className="text-[10px] font-mono text-cyan-400 font-bold uppercase">
                                Institutional Market Structure
                            </span>
                            {[
                                { label: 'Order Block (OB)', val: '2,335.5 Demand', color: '#10b981' },
                                { label: 'Fair Value Gap (FVG)', val: '2,341.0 Imbalance', color: '#00B7FF' },
                                { label: 'Liquidity Sweep', val: 'Equal Lows Swept', color: '#eab308' },
                                { label: 'Break of Structure (BOS)', val: 'Confirmed Higher High', color: '#a855f7' },
                            ].map((s, idx) => (
                                <div key={idx} className="p-2 rounded-lg bg-slate-900/60 border border-white/5 flex justify-between text-[11px]">
                                    <span className="text-slate-300 font-medium">{s.label}</span>
                                    <span className="font-mono font-bold" style={{ color: s.color }}>{s.val}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* ── Tab 2: Pattern Recognition ── */}
                {tab === 'patterns' && (
                    <div className="flex flex-col gap-2">
                        <span className="text-[10px] font-mono text-cyan-400 font-bold uppercase">
                            Detected Chart Patterns
                        </span>
                        {AI_PATTERNS.map((pat, idx) => (
                            <div key={idx} className="p-2.5 rounded-xl bg-slate-900/80 border border-cyan-500/15 flex flex-col gap-1">
                                <div className="flex items-center justify-between text-xs font-bold text-slate-100">
                                    <span>{pat.name}</span>
                                    <span className="text-emerald-400 text-[10px] font-mono">{pat.confidence}% Conf.</span>
                                </div>
                                <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                                    <span>Type: {pat.type}</span>
                                    <span className="text-cyan-300">Target: {pat.target}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {/* ── Tab 3: AI Trade Setup Suggestions ── */}
                {tab === 'trade' && (
                    <div className="flex flex-col gap-2.5">
                        <div className="p-3 rounded-xl bg-emerald-950/30 border border-emerald-500/30 flex flex-col gap-2">
                            <div className="flex items-center justify-between font-mono text-[10px]">
                                <span className="text-emerald-400 font-bold uppercase">BUY LONG SETUP</span>
                                <span className="text-slate-300">RR 1:3.4</span>
                            </div>
                            <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
                                <div className="flex flex-col">
                                    <span className="text-slate-500 text-[9px]">Entry Zone</span>
                                    <span className="font-bold text-white">2,342.0</span>
                                </div>
                                <div className="flex flex-col">
                                    <span className="text-slate-500 text-[9px]">Stop Loss</span>
                                    <span className="font-bold text-rose-400">2,336.5</span>
                                </div>
                                <div className="flex flex-col">
                                    <span className="text-slate-500 text-[9px]">Take Profit 1</span>
                                    <span className="font-bold text-emerald-400">2,358.0</span>
                                </div>
                                <div className="flex flex-col">
                                    <span className="text-slate-500 text-[9px]">Take Profit 2</span>
                                    <span className="font-bold text-emerald-400">2,365.0</span>
                                </div>
                            </div>
                            <div className="text-[9px] text-slate-400 italic pt-1 border-t border-emerald-500/20">
                                Reasoning: Confluence of 4H Order Block + FVG fill with 88% bullish sentiment.
                            </div>
                        </div>

                        <div className="text-[9px] text-slate-500 font-mono text-center">
                            ⚠️ Educational analysis only. Never auto-executes trades.
                        </div>
                    </div>
                )}

                {/* ── Tab 4: AI News & Economic Calendar ── */}
                {tab === 'news' && (
                    <div className="flex flex-col gap-2">
                        <span className="text-[10px] font-mono text-cyan-400 font-bold uppercase">
                            Upcoming Macro Events
                        </span>
                        {ECONOMIC_NEWS.map((news) => (
                            <div key={news.id} className="p-2.5 rounded-xl bg-slate-900/60 border border-white/5 flex flex-col gap-1 text-[11px]">
                                <div className="flex items-center justify-between font-bold text-slate-200">
                                    <span>{news.title}</span>
                                    <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/30">
                                        {news.impact}
                                    </span>
                                </div>
                                <div className="flex justify-between text-[10px] font-mono text-slate-400">
                                    <span>Time: {news.time} ({news.currency})</span>
                                    <span className="text-cyan-400">{news.sentiment}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
