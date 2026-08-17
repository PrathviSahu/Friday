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
        setStatusMsg(`Launching ${name}...`);
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
            desc: 'Job Match Engine, ATS Resume Scanner & Scraper',
            icon: Briefcase,
            color: '#818cf8',
            action: () => {
                setWorkspace?.('career');
            }
        },
        {
            id: 'trading',
            title: 'Trading Station',
            badge: 'Live Data',
            badgeColor: '#0284c7',
            desc: 'TradingView Candlestick Charts across 7 timeframes',
            icon: TrendingUp,
            color: '#38bdf8',
            action: () => {
                setWorkspace?.('trading');
            }
        },
        {
            id: 'dashboard',
            title: '17-in-1 Dashboard',
            badge: '17 Tools',
            badgeColor: '#16a34a',
            desc: 'Live capsule search, tools & system monitors',
            icon: LayoutGrid,
            color: '#4ade80',
            action: () => {
                window.dispatchEvent(new CustomEvent('friday-open-dashboard'));
            }
        },
        {
            id: 'spotify',
            title: 'Spotify Hub',
            badge: 'Media',
            badgeColor: '#15803d',
            desc: 'Instant music search and mobile app deep link',
            icon: Music,
            color: '#22c55e',
            action: () => {
                window.dispatchEvent(new CustomEvent('friday-open-spotify'));
            }
        },
        {
            id: 'voice_ai',
            title: 'Voice Intelligence',
            badge: 'Llama 3.3 70B',
            badgeColor: '#db2777',
            desc: 'Live LLM reasoning with neural Edge-TTS voice',
            icon: Volume2,
            color: '#f472b6',
            action: async () => {
                const query = "Give me a quick 15-second summary of Prathvi Sahu's profile and F.R.I.D.A.Y.'s capabilities for a tech recruiter.";
                setStatusMsg('Thinking via Groq Llama 3.3 70B...');
                try {
                    const res = await fetchChatText(query, true);
                    const reply = res?.reply || "I am F.R.I.D.A.Y., engineered by Prathvi Sahu. I feature Career OS, real-time trading charts, and autonomous multi-agent intelligence.";
                    await speak(reply);
                } catch (_) {
                    await speak("I am F.R.I.D.A.Y., standing by with Career OS, Quantum Trading, and full system automation.");
                }
            }
        },
        {
            id: 'briefing',
            title: 'Daily Briefing',
            badge: 'Autonomous',
            badgeColor: '#d97706',
            desc: 'Live intelligence report: weather, tasks & market trends',
            icon: Sparkles,
            color: '#fbbf24',
            action: async () => {
                setStatusMsg('Generating Daily Briefing...');
                try {
                    const res = await fetchChatText("what is my daily briefing?", true);
                    const reply = res?.reply || "Here is your daily intelligence briefing, Prem. Markets are active, your job pipeline is synced, and all background services are nominal.";
                    await speak(reply);
                } catch (_) {}
            }
        },
        {
            id: 'resume',
            title: 'ATS Resume Scorer',
            badge: 'AI Scoring',
            badgeColor: '#0891b2',
            desc: 'Inspect resume match scoring and cover letter tools',
            icon: FileText,
            color: '#22d3ee',
            action: () => {
                setWorkspace?.('career');
            }
        },
        {
            id: 'agents',
            title: 'Multi-Agent Team',
            badge: '6 Agents',
            badgeColor: '#9333ea',
            desc: 'Career, Coding, Finance & Research agents',
            icon: Bot,
            color: '#c084fc',
            action: () => {
                window.dispatchEvent(new CustomEvent('friday-open-dashboard'));
            }
        }
    ];

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.97 }}
            className={`w-full max-w-[440px] rounded-2xl bg-[#030712]/90 border border-[#00B7FF]/30 backdrop-blur-2xl shadow-[0_20px_50px_rgba(0,183,255,0.15)] p-4 sm:p-5 flex flex-col font-sans select-none overflow-hidden relative ${
                isDocked ? '' : 'z-50'
            }`}
            style={{ pointerEvents: 'auto' }}
        >
            {/* Subtle Top Glow Accent */}
            <div className="absolute top-0 left-0 right-0 h-[1.5px] bg-gradient-to-r from-transparent via-[#00D9FF] to-transparent shadow-[0_0_10px_#00D9FF]" />

            {/* Clean Header */}
            <div className="flex items-center justify-between pb-3 mb-2.5 border-b border-white/10">
                <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-xl bg-[#00B7FF]/15 border border-[#00B7FF]/30 flex items-center justify-center text-[#00D9FF] shadow-[0_0_12px_rgba(0,183,255,0.25)]">
                        <Sparkles size={16} />
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <h3 className="text-sm font-semibold text-white tracking-tight">
                                Recruiter 1-Click Showcase
                            </h3>
                            <span className="px-1.5 py-0.5 rounded-full text-[9px] font-medium bg-[#22ff99]/15 text-[#22ff99] border border-[#22ff99]/30">
                                Live
                            </span>
                        </div>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                            Tap any capability to test instantly without voice commands
                        </p>
                    </div>
                </div>

                {onClose && (
                    <button
                        onClick={onClose}
                        className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition cursor-pointer"
                        title="Close"
                    >
                        <X size={16} />
                    </button>
                )}
            </div>

            {/* Status Feedback Toast */}
            <AnimatePresence>
                {statusMsg && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mb-2.5 px-3 py-1.5 rounded-xl bg-[#00D9FF]/15 border border-[#00D9FF]/30 text-[#00D9FF] text-xs font-medium flex items-center gap-2"
                    >
                        <span className="w-2 h-2 rounded-full bg-[#00D9FF] animate-ping" />
                        <span>{statusMsg}</span>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Feature Action Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-[300px] overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-white/10">
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
                                    ? 'bg-[#00D9FF]/20 border-[#00D9FF] shadow-[0_0_15px_rgba(0,217,255,0.25)]'
                                    : 'bg-white/[0.03] border-white/[0.08] hover:bg-white/[0.08] hover:border-[#00B7FF]/40 hover:shadow-lg'
                            } disabled:cursor-wait`}
                        >
                            <div className="flex items-center justify-between w-full">
                                <div className="flex items-center gap-2">
                                    <div 
                                        className="w-6 h-6 rounded-lg flex items-center justify-center shrink-0 transition group-hover:scale-105"
                                        style={{ background: `${color}15`, border: `1px solid ${color}30`, color }}
                                    >
                                        <Icon size={13} />
                                    </div>
                                    <span className="text-xs font-semibold text-slate-100 group-hover:text-white transition line-clamp-1">
                                        {title}
                                    </span>
                                </div>
                                <span 
                                    className="text-[9px] px-1.5 py-0.5 rounded-full font-medium shrink-0"
                                    style={{ background: `${badgeColor}18`, color: badgeColor, border: `1px solid ${badgeColor}35` }}
                                >
                                    {badge}
                                </span>
                            </div>

                            <p className="text-[10px] text-slate-400 leading-snug line-clamp-2">
                                {desc}
                            </p>

                            <div className="flex items-center justify-between text-[9.5px] font-medium text-[#00B7FF]/80 group-hover:text-[#00D9FF] pt-1 border-t border-white/[0.05]">
                                <span>{isRunning ? 'Launching...' : '1-Tap Launch'}</span>
                                <ChevronRight size={12} className="transform group-hover:translate-x-0.5 transition" />
                            </div>
                        </button>
                    );
                })}
            </div>

            {/* Clean Footer */}
            <div className="mt-3 pt-2.5 border-t border-white/10 flex items-center justify-between text-[10px] text-slate-400">
                <span className="flex items-center gap-1.5">
                    <CheckCircle2 size={12} className="text-[#22ff99]" />
                    <span>Zero Setup Required</span>
                </span>
                <span className="font-medium text-slate-300">Prathvi Sahu · SDE (Java & React)</span>
            </div>
        </motion.div>
    );
}
