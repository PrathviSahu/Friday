import { motion } from 'framer-motion';
import AnimatedCard from '../../components/Panels/AnimatedCard';
import Clock from '../../components/Clock/Clock';
import { useOrbState } from '../../hooks/useOrbState';
import { useState, useEffect } from 'react';
import { API_ENDPOINTS } from '../../api/config.js';

async function fetchStats() {
    try {
        const r = await fetch(API_ENDPOINTS.system + '/stats');
        return await r.json();
    } catch { return null; }
}

async function fetchMarket() {
    try {
        const r = await fetch(API_ENDPOINTS.trading + '/live-prices');
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
        { label: 'CPU', val: `${cpu}%`, w: `${cpu}%`, col: cpu > 80 ? 'bg-red-400' : 'bg-blue-400' },
        { label: 'Memory',   val: `${ram}%`, w: `${ram}%`, col: ram > 80 ? 'bg-orange-400' : 'bg-blue-400' },
        { label: `Battery${plug ? ' ⚡' : ''}`, val: `${bat}%`, w: `${bat}%`, col: bat < 20 ? 'bg-red-400' : 'bg-green-400' },
    ];

    const btc = market['BINANCE:BTCUSDT'];

    return (
        <div className="absolute inset-0 w-full h-full flex flex-col justify-between px-8 py-6 pointer-events-auto" style={{ zIndex: 25 }}>
            
            <div className="flex justify-between items-center w-full">
                <div className="flex items-center gap-4">
                    <span className="font-sans text-[9px] tracking-[0.15em] text-slate-400/60 uppercase">F.R.I.D.A.Y.</span>
                    <button onClick={() => setWorkspace('career')}
                        className="border border-indigo-500/30 bg-indigo-500/10 hover:bg-indigo-500/20 px-3 py-1 rounded-lg text-[10px] font-sans font-medium tracking-wide text-indigo-300 transition-all cursor-pointer">
                        Career OS
                    </button>
                    <button onClick={onLock}
                        className="border border-slate-500/30 bg-slate-500/10 hover:bg-slate-500/20 px-3 py-1 rounded-lg text-[10px] font-sans font-medium tracking-wide text-slate-300 transition-all cursor-pointer">
                        Lock
                    </button>
                </div>
                <div className="flex items-center gap-6">
                    <div className="font-sans text-xs tracking-wide text-slate-300 flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                        Active
                    </div>
                    <Clock />
                </div>
            </div>

            <div className="flex-1 flex justify-between items-center my-6 gap-6">
                
                {/* Left — Live Market Feed */}
                <motion.div initial={{ opacity: 0, x: -80, scale: 0.95 }} animate={{ opacity: 1, x: 0, scale: 1 }} transition={{ duration: 1.1, ease: 'easeOut', delay: 0.1 }}>
                    <AnimatedCard width={290} height={420}>
                        <div className="flex flex-col gap-3 h-full">
                            <div className="font-sans text-[10px] tracking-[0.1em] text-slate-400/70 border-b border-slate-600/20 pb-2 font-medium">
                                Live Market Feed
                            </div>

                            {btc ? (
                                <div className="mt-1">
                                    <div className="flex justify-between items-center">
                                        <span className="font-sans text-xs text-slate-200 font-medium">BTC / USDT</span>
                                        <span className={`text-[10px] font-bold font-sans ${btc.isPositive ? 'text-green-400' : 'text-red-400'}`}>{btc.pct_str}</span>
                                    </div>
                                    <div className="text-xl font-bold font-sans text-slate-100 mt-0.5">${btc.price_str}</div>
                                    <div className={`text-[9px] font-sans mt-0.5 ${btc.isPositive ? 'text-green-500' : 'text-red-500'}`}>{btc.change_str} USD</div>
                                </div>
                            ) : (
                                <div className="mt-1 text-[10px] font-sans text-slate-400/40 animate-pulse">Fetching live feed...</div>
                            )}

                            <div className="w-full h-28 relative bg-slate-800/30 border border-slate-600/10 rounded-lg mt-1 overflow-hidden">
                                <svg className="w-full h-full" viewBox="0 0 100 50">
                                    <line x1="0" y1="12" x2="100" y2="12" stroke="rgba(148, 163, 184, 0.06)" strokeWidth="0.5" />
                                    <line x1="0" y1="25" x2="100" y2="25" stroke="rgba(148, 163, 184, 0.06)" strokeWidth="0.5" />
                                    <line x1="0" y1="38" x2="100" y2="38" stroke="rgba(148, 163, 184, 0.06)" strokeWidth="0.5" />
                                    <motion.path d="M 0 42 Q 15 35 25 38 T 50 18 T 75 22 T 100 8"
                                        fill="none" stroke="#60a5fa" strokeWidth="1.5"
                                        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }}
                                        transition={{ duration: 2.2, ease: 'easeInOut', delay: 0.4 }}
                                    />
                                </svg>
                            </div>

                            {/* Resource bars */}
                            <div className="flex flex-col gap-2.5 mt-auto">
                                {resources.map((r) => (
                                    <div key={r.label}>
                                        <div className="flex justify-between text-[9px] text-slate-400 mb-0.5">
                                            <span>{r.label}</span>
                                            <span className="font-medium text-slate-300">{r.val}</span>
                                        </div>
                                        <div className="w-full h-1 bg-slate-700/40 rounded-full overflow-hidden">
                                            <motion.div
                                                className={`h-full rounded-full ${r.col}`}
                                                initial={{ width: 0 }}
                                                animate={{ width: r.w }}
                                                transition={{ duration: 0.8, ease: 'easeOut' }}
                                            />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </AnimatedCard>
                </motion.div>

                {/* Center — Status */}
                <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, delay: 0.3 }} className="text-center">
                    <div className="font-sans text-[10px] tracking-[0.15em] text-slate-400/50 uppercase mb-2">System Online</div>
                </motion.div>

                {/* Right — Quick Actions */}
                <motion.div initial={{ opacity: 0, x: 80, scale: 0.95 }} animate={{ opacity: 1, x: 0, scale: 1 }} transition={{ duration: 1.1, ease: 'easeOut', delay: 0.2 }}>
                    <AnimatedCard width={260} height={420}>
                        <div className="flex flex-col gap-3 h-full">
                            <div className="font-sans text-[10px] tracking-[0.1em] text-slate-400/70 border-b border-slate-600/20 pb-2 font-medium">
                                Quick Actions
                            </div>
                            <div className="flex flex-col gap-2 mt-2">
                                {[
                                    { label: 'Open Trading', action: () => setWorkspace('trading') },
                                    { label: 'Career OS', action: () => setWorkspace('career') },
                                ].map((btn) => (
                                    <button
                                        key={btn.label}
                                        onClick={btn.action}
                                        className="w-full py-2 rounded-lg border border-slate-600/30 bg-slate-700/20 hover:bg-slate-700/40 text-[11px] font-sans font-medium text-slate-300 transition-all cursor-pointer"
                                    >
                                        {btn.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </AnimatedCard>
                </motion.div>
            </div>
        </div>
    );
}
