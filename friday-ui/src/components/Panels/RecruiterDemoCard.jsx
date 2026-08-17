import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Briefcase, TrendingUp, LayoutGrid, Music, 
    Bot, Sparkles, FileText, CheckCircle2, ChevronRight, X, Volume2
} from 'lucide-react';
import { useOrbState } from '../../hooks/useOrbState';
import { speak } from '../../services/ttsService';
import { fetchChatText } from '../../api/chatText';

export default function RecruiterDemoCard({ onClose, isDocked = false }) {
    const { setWorkspace, unlockDemo, locked } = useOrbState();
    const [executing, setExecuting] = useState('');
    const [statusMsg, setStatusMsg] = useState('');

    const runAction = async (id, name, actionFn) => {
        setExecuting(id);
        setStatusMsg(`⚡ Launching ${name}...`);
        try {
            if (locked) {
                unlockDemo?.();
            }
            await actionFn();
        } catch (err) {
            console.warn('[Recruiter Demo] Error running action:', err);
        } finally {
            setTimeout(() => {
                setExecuting('');
                setStatusMsg('');
            }, 1200);
        }
    };

    const DEMO_ACTIONS = [
        {
            id: 'career',
            title: 'Career OS',
            badge: 'Flagship',
            badgeColor: '#6366f1',
            desc: 'Job Match Engine, ATS Resume Scanner, Live LinkedIn Scraper & Interview Center',
            icon: Briefcase,
            color: '#818cf8',
            action: () => {
                setWorkspace?.('career');
            }
        },
        {
            id: 'trading',
            title: 'Quantum Trading Station',
            badge: 'Live Data',
            badgeColor: '#2962ff',
            desc: 'Real-time TradingView Lightweight Charts, 7 Timeframes, Multi-Asset Watchlist',
            icon: TrendingUp,
            color: '#00D9FF',
            action: () => {
                setWorkspace?.('trading');
            }
        },
        {
            id: 'dashboard',
            title: '17-in-1 Stark Dashboard',
            badge: '17 Tools',
            badgeColor: '#22c55e',
            desc: 'Filter & search 17 live AI capsules: System, Productivity, Communication & Security',
            icon: LayoutGrid,
            color: '#22ff99',
            action: () => {
                window.dispatchEvent(new CustomEvent('friday-open-dashboard'));
            }
        },
        {
            id: 'spotify',
            title: 'Spotify Hub & Mobile Deep-Link',
            badge: 'Media',
            badgeColor: '#1DB954',
            desc: 'Anonymous token music search, background playback, and Android native app launch',
            icon: Music,
            color: '#1DB954',
            action: () => {
                window.dispatchEvent(new CustomEvent('friday-open-spotify'));
            }
        },
        {
            id: 'voice_ai',
            title: 'Test Groq Voice Intelligence',
            badge: 'Llama 3.3 70B',
            badgeColor: '#ec4899',
            desc: 'Trigger live LLM reasoning + Indian English female neural Edge-TTS voice',
            icon: Volume2,
            color: '#f472b6',
            action: async () => {
                const query = "F.R.I.D.A.Y., give me a quick 15-second summary of your architecture and capabilities for a tech recruiter.";
                setStatusMsg('🧠 Thinking via Groq Llama 3.3 70B...');
                try {
                    const res = await fetchChatText(query, true);
                    const reply = res?.reply || "I am F.R.I.D.A.Y., an intelligent operating system built with React 19, Python FastAPI, Groq Llama 3.3 70B, and real-time market and career intelligence.";
                    await speak(reply);
                } catch (_) {
                    await speak("I am F.R.I.D.A.Y., standing by with Career OS, Quantum Trading, and full system automation.");
                }
            }
        },
        {
            id: 'briefing',
            title: 'Trigger Daily Briefing',
            badge: 'Autonomous',
            badgeColor: '#f59e0b',
            desc: 'Aggregate weather, active tasks, reminders, market sentiment & career pipeline',
            icon: Sparkles,
            color: '#fbbf24',
            action: async () => {
                setStatusMsg('📋 Generating Daily Briefing...');
                try {
                    const res = await fetchChatText("what is my daily briefing?", true);
                    const reply = res?.reply || "Here is your daily intelligence briefing, Prem. Markets are active, your job pipeline is synced, and all background services are nominal.";
                    await speak(reply);
                } catch (_) {}
            }
        },
        {
            id: 'resume',
            title: 'ATS Resume Intelligence',
            badge: 'AI Scoring',
            badgeColor: '#06b6d4',
            desc: 'Inspect resume tailoring, keyword density, and instant cover letter generator',
            icon: FileText,
            color: '#22d3ee',
            action: () => {
                setWorkspace?.('career');
            }
        },
        {
            id: 'agents',
            title: 'Autonomous Multi-Agent Roster',
            badge: '6 Agents',
            badgeColor: '#a855f7',
            desc: 'Career, Coding, Finance, Research, Automation & Communication agents',
            icon: Bot,
            color: '#c084fc',
            action: () => {
                window.dispatchEvent(new CustomEvent('friday-open-dashboard'));
            }
        }
    ];

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className={`w-full max-w-[460px] rounded-2xl bg-[#030712]/95 border border-[#00B7FF]/35 backdrop-blur-2xl shadow-[0_20px_60px_rgba(0,183,255,0.18)] p-4 sm:p-5 flex flex-col font-sans select-none overflow-hidden relative ${
                isDocked ? '' : 'z-50'
            }`}
            style={{ pointerEvents: 'auto' }}
        >
            {/* Header Glow & Accent */}
            <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#00D9FF] to-transparent shadow-[0_0_12px_#00D9FF]" />

            {/* Header */}
            <div className="flex items-center justify-between pb-3 mb-2 border-b border-white/10">
                <div className="flex items-center gap-2.5">
                    <div className="w-7 h-7 rounded-lg bg-[#00B7FF]/15 border border-[#00B7FF]/40 flex items-center justify-center text-[#00D9FF] shadow-[0_0_10px_rgba(0,183,255,0.3)]">
                        <Sparkles size={15} />
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <h3 className="text-xs font-orbitron font-bold tracking-[0.18em] text-[#00D9FF] uppercase">
                                RECRUITER 1-CLICK DEMO
                            </h3>
                            <span className="px-1.5 py-0.5 rounded text-[8px] font-mono font-bold bg-[#22ff99]/20 text-[#22ff99] border border-[#22ff99]/40 animate-pulse">
                                LIVE
                            </span>
                        </div>
                        <p className="text-[9px] font-grotesk text-slate-400 tracking-wide mt-0.5">
                            Click any capability below to test instantly without voice commands
                        </p>
                    </div>
                </div>

                {onClose && (
                    <button
                        onClick={onClose}
                        className="p-1 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition cursor-pointer"
                        title="Close Demo Card"
                    >
                        <X size={15} />
                    </button>
                )}
            </div>

            {/* Status Toast */}
            <AnimatePresence>
                {statusMsg && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mb-2.5 px-3 py-1.5 rounded-lg bg-[#00D9FF]/15 border border-[#00D9FF]/40 text-[#00D9FF] text-[10px] font-mono font-bold flex items-center gap-2"
                    >
                        <span className="w-1.5 h-1.5 rounded-full bg-[#00D9FF] animate-ping" />
                        <span>{statusMsg}</span>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Feature Action Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-[360px] overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-white/10">
                {DEMO_ACTIONS.map(({ id, title, badge, badgeColor, desc, icon: Icon, color, action }) => {
                    const isRunning = executing === id;
                    return (
                        <button
                            key={id}
                            type="button"
                            onClick={() => runAction(id, title, action)}
                            disabled={Boolean(executing)}
                            className={`group relative p-2.5 rounded-xl border text-left transition-all cursor-pointer flex flex-col justify-between gap-1.5 ${
                                isRunning
                                    ? 'bg-[#00D9FF]/20 border-[#00D9FF] shadow-[0_0_15px_rgba(0,217,255,0.3)]'
                                    : 'bg-white/[0.03] border-white/[0.07] hover:bg-white/[0.08] hover:border-[#00B7FF]/50 hover:shadow-[0_4px_16px_rgba(0,0,0,0.5)]'
                            } disabled:cursor-wait`}
                        >
                            <div className="flex items-center justify-between w-full">
                                <div className="flex items-center gap-2">
                                    <div 
                                        className="w-6 h-6 rounded-lg flex items-center justify-center shrink-0 transition group-hover:scale-110"
                                        style={{ background: `${color}18`, border: `1px solid ${color}35`, color }}
                                    >
                                        <Icon size={12} />
                                    </div>
                                    <span className="text-[11px] font-bold text-slate-200 group-hover:text-white transition line-clamp-1">
                                        {title}
                                    </span>
                                </div>
                                <span 
                                    className="text-[7.5px] font-mono uppercase px-1.5 py-0.5 rounded font-bold shrink-0"
                                    style={{ background: `${badgeColor}20`, color: badgeColor, border: `1px solid ${badgeColor}40` }}
                                >
                                    {badge}
                                </span>
                            </div>

                            <p className="text-[8.5px] text-slate-400 leading-tight line-clamp-2">
                                {desc}
                            </p>

                            <div className="flex items-center justify-between text-[8px] font-mono text-[#00B7FF]/70 group-hover:text-[#00D9FF] pt-1 border-t border-white/[0.05]">
                                <span>{isRunning ? 'EXECUTING...' : '1-TAP LAUNCH'}</span>
                                <ChevronRight size={10} className="transform group-hover:translate-x-0.5 transition" />
                            </div>
                        </button>
                    );
                })}
            </div>

            {/* Footer */}
            <div className="mt-3 pt-2.5 border-t border-white/10 flex items-center justify-between text-[8px] font-mono text-slate-500">
                <span className="flex items-center gap-1">
                    <CheckCircle2 size={10} className="text-[#22ff99]" />
                    <span>Zero Setup Required</span>
                </span>
                <span>Prathvi Sahu · SDE (Java/Spring & React)</span>
            </div>
        </motion.div>
    );
}
