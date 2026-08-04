import { motion } from 'framer-motion';
import AnimatedCard from '../../components/Panels/AnimatedCard';
import Clock from '../../components/Clock/Clock';
import { useOrbState } from '../../hooks/useOrbState';
import { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:8000';

async function fetchStats() {
    try {
        const r = await fetch(`${API_BASE}/api/system/stats`);
        return await r.json();
    } catch { return null; }
}

async function fetchMarket() {
    try {
        const r = await fetch(`${API_BASE}/api/trading/live-prices`);
        return await r.json();
    } catch { return null; }
}

const DASH_SYMBOLS = [
    { key: 'BINANCE:BTCUSDT', label: 'BTC/USDT' },
    { key: 'BINANCE:ETHUSDT', label: 'ETH/USDT' },
    { key: 'OANDA:XAUUSD',   label: 'GOLD (XAU)' },
];

export default function Dashboard({ onLock }) {
    const { setWorkspace } = useOrbState();
    const [stats, setStats] = useState({ cpu_percent: 0, ram_percent: 0, battery_percent: 0, power_plugged: false, disk_percent: 0, ram_used_gb: 0, ram_total_gb: 0 });
    const [market, setMarket] = useState({});

    useEffect(() => {
        let alive = true;
        const poll = async () => { const s = await fetchStats(); if (alive && s) setStats(s); };
        poll();
        const t = setInterval(poll, 3000);
        return () => { alive = false; clearInterval(t); };
    }, []);

    useEffect(() => {
        let alive = true;
        const poll = async () => { const m = await fetchMarket(); if (alive && m) setMarket(m); };
        poll();
        const t = setInterval(poll, 10000);
        return () => { alive = false; clearInterval(t); };
    }, []);

    const cpu = Math.round(stats.cpu_percent  || 0);
    const ram = Math.round(stats.ram_percent  || 0);
    const bat = Math.round(stats.battery_percent || 0);
    const dsk = Math.round(stats.disk_percent || 0);
    const plug = stats.power_plugged;

    const resources = [
        { label: 'CPU LOAD', val: `${cpu}%`, w: `${cpu}%`, col: cpu > 80 ? 'bg-red-400' : 'bg-cyan-400' },
        { label: 'MEMORY',   val: `${ram}%`, w: `${ram}%`, col: ram > 80 ? 'bg-orange-400' : 'bg-cyan-400' },
        { label: `BATTERY${plug ? ' ⚡' : ''}`, val: `${bat}%`, w: `${bat}%`, col: bat < 20 ? 'bg-red-400' : 'bg-green-400' },
    ];

    const btc = market['BINANCE:BTCUSDT'];

    return (
        <div className="absolute inset-0 w-full h-full flex flex-col justify-between px-8 py-6 pointer-events-auto" style={{ zIndex: 25 }}>
            
            <div className="flex justify-between items-center w-full">
                <div className="flex items-center gap-4">
                    <span className="font-orbitron text-[9px] tracking-[0.25em] text-[#00B7FF]/40 uppercase">STARK INDUSTRIES /</span>
                    <button onClick={() => setWorkspace('career')}
                        className="border border-[#6366f1]/30 bg-[#6366f1]/5 hover:bg-[#6366f1]/15 px-3 py-1 rounded text-[8px] font-orbitron tracking-widest text-[#818cf8] transition-all uppercase cursor-pointer"
                        style={{ boxShadow: '0 0 6px rgba(99, 102, 241, 0.15)' }}>
                        Career OS
                    </button>
                    <button onClick={onLock}
                        className="border border-[#ff4444]/30 bg-[#ff4444]/5 hover:bg-[#ff4444]/15 px-3 py-1 rounded text-[8px] font-orbitron tracking-widest text-[#ff6666] transition-all uppercase cursor-pointer"
                        style={{ boxShadow: '0 0 6px rgba(255, 68, 68, 0.15)' }}>
                        Secure Console [Lock]
                    </button>
                </div>
                <div className="flex items-center gap-6">
                    <div className="font-orbitron text-xs tracking-widest text-[#00B7FF] flex items-center gap-2 drop-shadow-[0_0_8px_rgba(0,183,255,0.4)]">
                        <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" style={{ boxShadow: '0 0 6px #00ff00' }} />
                        CONSOLE LEVEL 4 ACTIVE
                    </div>
                    <Clock />
                </div>
            </div>

            <div className="flex-1 flex justify-between items-center my-6 gap-6">
                
                {/* Left — Live Market Feed */}
                <motion.div initial={{ opacity: 0, x: -80, scale: 0.95 }} animate={{ opacity: 1, x: 0, scale: 1 }} transition={{ duration: 1.1, ease: 'easeOut', delay: 0.1 }}>
                    <AnimatedCard width={290} height={420}>
                        <div className="flex flex-col gap-3 h-full">
                            <div className="font-orbitron text-[9px] tracking-[0.2em] text-[#00B7FF]/60 border-b border-[#00B7FF]/10 pb-2">
                                LIVE MARKET FEED
                            </div>

                            {btc ? (
                                <div className="mt-1">
                                    <div className="flex justify-between items-center">
                                        <span className="font-orbitron text-xs text-[#DFFAFF]">BTC / USDT</span>
                                        <span className={`text-[10px] font-bold font-orbitron ${btc.isPositive ? 'text-green-400' : 'text-red-400'}`}>{btc.pct_str}</span>
                                    </div>
                                    <div className="text-xl font-bold font-orbitron text-[#DFFAFF] mt-0.5">${btc.price_str}</div>
                                    <div className={`text-[9px] font-orbitron mt-0.5 ${btc.isPositive ? 'text-green-500' : 'text-red-500'}`}>{btc.change_str} USD</div>
                                </div>
                            ) : (
                                <div className="mt-1 text-[10px] font-orbitron text-[#DFFAFF]/30 animate-pulse">FETCHING LIVE FEED…</div>
                            )}

                            <div className="w-full h-28 relative bg-cyan-950/20 border border-cyan-800/10 rounded mt-1 overflow-hidden">
                                <svg className="w-full h-full" viewBox="0 0 100 50">
                                    <line x1="0" y1="12" x2="100" y2="12" stroke="rgba(0, 183, 255, 0.05)" strokeWidth="0.5" />
                                    <line x1="0" y1="25" x2="100" y2="25" stroke="rgba(0, 183, 255, 0.05)" strokeWidth="0.5" />
                                    <line x1="0" y1="38" x2="100" y2="38" stroke="rgba(0, 183, 255, 0.05)" strokeWidth="0.5" />
                                    <motion.path d="M 0 42 Q 15 35 25 38 T 50 18 T 75 22 T 100 8"
                                        fill="none" stroke="#00D9FF" strokeWidth="1.5"
                                        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }}
                                        transition={{ duration: 2.2, ease: 'easeInOut', delay: 0.4 }}
                                        style={{ filter: 'drop-shadow(0 0 4px rgba(0, 217, 255, 0.8))' }} />
                                    <path d="M 0 42 Q 15 35 25 38 T 50 18 T 75 22 T 100 8 L 100 50 L 0 50 Z" fill="url(#chartGrad)" opacity="0.12" />
                                    <defs>
                                        <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="0%" stopColor="#00D9FF" />
                                            <stop offset="100%" stopColor="transparent" />
                                        </linearGradient>
                                    </defs>
                                </svg>
                            </div>

                            <div className="space-y-2 mt-2">
                                {DASH_SYMBOLS.slice(1).map(({ key, label }) => {
                                    const d = market[key];
                                    return (
                                        <div key={key} className="flex justify-between items-center text-[9px] font-orbitron border-b border-[#00B7FF]/5 pb-1">
                                            <span className="text-[#DFFAFF]/60">{label}</span>
                                            {d ? (
                                                <div className="flex gap-2">
                                                    <span className="text-[#DFFAFF]">{d.price_str}</span>
                                                    <span className={`font-bold ${d.isPositive ? 'text-green-400' : 'text-red-400'}`}>{d.pct_str}</span>
                                                </div>
                                            ) : <span className="text-[#DFFAFF]/20 animate-pulse">—</span>}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </AnimatedCard>
                </motion.div>

                {/* Center */}
                <div className="flex-1 self-stretch flex flex-col justify-between items-center pointer-events-none">
                    <motion.div className="text-center" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }}>
                        <h2 className="font-orbitron text-xs tracking-[0.3em] text-[#00B7FF]/70">TACTICAL OVERVIEW</h2>
                        <div className="w-12 h-px bg-[#00B7FF]/30 mx-auto mt-1" />
                    </motion.div>
                    <div className="flex-1" />
                    <div className="text-center pb-4">
                        <span className="font-orbitron text-[9px] tracking-[0.2em] text-[#00D9FF] font-bold uppercase drop-shadow-[0_0_6px_#00D9FF]">
                            CORE INTERACTION ONLINE
                        </span>
                    </div>
                </div>

                {/* Right — Live System Monitor */}
                <motion.div initial={{ opacity: 0, x: 80, scale: 0.95 }} animate={{ opacity: 1, x: 0, scale: 1 }} transition={{ duration: 1.1, ease: 'easeOut', delay: 0.1 }}>
                    <AnimatedCard width={290} height={420}>
                        <div className="flex flex-col gap-3 h-full justify-between">
                            <div>
                                <div className="font-orbitron text-[9px] tracking-[0.2em] text-[#00B7FF]/60 border-b border-[#00B7FF]/10 pb-2 mb-3">
                                    SYSTEM VITALS — LIVE
                                </div>
                                <div className="space-y-3">
                                    {resources.map((r, i) => (
                                        <div key={i} className="text-[9px] font-orbitron">
                                            <div className="flex justify-between text-[#DFFAFF]/60 mb-1">
                                                <span>{r.label}</span>
                                                <span>{r.val}</span>
                                            </div>
                                            <div className="w-full h-1 bg-[#00B7FF]/10 rounded-full overflow-hidden">
                                                <motion.div className={`h-full ${r.col} transition-all duration-700`}
                                                    animate={{ width: r.w }}
                                                    transition={{ duration: 0.7, ease: 'easeOut' }} />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="border-t border-[#00B7FF]/10 pt-3">
                                <div className="font-orbitron text-[8px] tracking-[0.2em] text-[#00B7FF]/40 mb-2">STORAGE</div>
                                <div className="text-[9px] font-orbitron">
                                    <div className="flex justify-between text-[#DFFAFF]/60 mb-1">
                                        <span>DISK USED</span><span>{dsk}%</span>
                                    </div>
                                    <div className="w-full h-1 bg-[#00B7FF]/10 rounded-full overflow-hidden">
                                        <motion.div className={`h-full transition-all duration-700 ${dsk > 85 ? 'bg-red-400' : 'bg-purple-400'}`}
                                            animate={{ width: `${dsk}%` }} transition={{ duration: 0.7, ease: 'easeOut' }} />
                                    </div>
                                </div>
                            </div>

                            <div className="border-t border-[#00B7FF]/10 pt-3">
                                <div className="font-orbitron text-[8px] tracking-[0.2em] text-[#00B7FF]/40 mb-1">MEMORY DETAIL</div>
                                <div className="text-[9px] font-orbitron text-[#DFFAFF]/50">
                                    {stats.ram_used_gb?.toFixed(1) || '—'} GB / {stats.ram_total_gb?.toFixed(0) || '—'} GB RAM
                                </div>
                            </div>
                        </div>
                    </AnimatedCard>
                </motion.div>

            </div>

            <div className="flex justify-center w-full">
                <div className="border-t border-[#00B7FF]/15 pt-2 w-full text-center">
                    <span className="font-grotesk text-[8px] tracking-[0.3em] text-[#00B7FF]/35 uppercase">
                        STARK CONSOLE LEVEL 4 / ENCRYPTED SECURE FEED
                    </span>
                </div>
            </div>
        </div>
    );
}
