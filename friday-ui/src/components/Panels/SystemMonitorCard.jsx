import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Cpu, HardDrive, Battery, Zap, X, GripHorizontal, Activity } from 'lucide-react';
import { useOrbState } from '../../hooks/useOrbState';

const API = 'http://localhost:8000/api/system/stats';

function MetricBar({ icon: Icon, label, value, color, unit = '%' }) {
    const isHigh = value > 85;
    const barColor = isHigh ? '#ef4444' : color;

    return (
        <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between text-[11px]">
                <div className="flex items-center gap-1.5 font-medium text-slate-300">
                    <Icon size={13} style={{ color: barColor }} />
                    <span>{label}</span>
                </div>
                <span className="font-mono font-bold" style={{ color: barColor }}>
                    {value}{unit}
                </span>
            </div>
            <div className="h-1.5 w-full bg-slate-800/80 rounded-full overflow-hidden p-[1px] border border-white/5">
                <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(100, Math.max(0, value))}%` }}
                    transition={{ duration: 0.5, ease: 'easeOut' }}
                    className="h-full rounded-full"
                    style={{
                        background: `linear-gradient(90deg, ${barColor}aa, ${barColor})`,
                        boxShadow: `0 0 8px ${barColor}66`
                    }}
                />
            </div>
        </div>
    );
}

export default function SystemMonitorCard() {
    const { workspace } = useOrbState();
    const [isVisible, setIsVisible] = useState(false);

    if (workspace === 'trading') return null;
    const [stats, setStats] = useState({
        cpu_percent: 0,
        ram_percent: 0,
        ram_used_gb: 0,
        ram_total_gb: 0,
        disk_percent: 0,
        battery_percent: 100,
        power_plugged: true
    });

    const fetchStats = async () => {
        try {
            const res = await fetch(API);
            if (res.ok) setStats(await res.json());
        } catch (_) {}
    };

    useEffect(() => {
        fetchStats();
        const iv = setInterval(fetchStats, 3000);
        return () => clearInterval(iv);
    }, []);

    if (!isVisible) {
        return (
            <motion.div
                drag
                dragConstraints={{ left: -1200, right: 200, top: -100, bottom: 800 }}
                dragElastic={0.1}
                whileDrag={{ scale: 1.05 }}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setIsVisible(true)}
                className="fixed top-8 right-10 z-50 flex items-center gap-2 px-3.5 py-2 rounded-full cursor-grab active:cursor-grabbing pointer-events-auto select-none bg-[#090d16]/90 border border-cyan-500/30 text-cyan-400 shadow-[0_4px_20px_rgba(0,183,255,0.2)] text-[11px] font-mono"
            >
                <Activity size={13} className="animate-pulse text-cyan-400" />
                <span>CPU {stats.cpu_percent}%</span>
            </motion.div>
        );
    }

    return (
        <AnimatePresence>
            <motion.div
                drag
                dragConstraints={{ left: -1200, right: 200, top: -100, bottom: 800 }}
                dragElastic={0.1}
                whileDrag={{ scale: 1.02, cursor: 'grabbing' }}
                initial={{ opacity: 0, y: -20, scale: 0.94 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                className="fixed top-8 right-10 z-40 w-64 rounded-2xl pointer-events-auto select-none overflow-hidden bg-[#070b12]/92 border border-cyan-500/25 shadow-[0_16px_50px_rgba(0,0,0,0.8),0_0_20px_rgba(0,183,255,0.15)] backdrop-blur-xl cursor-grab active:cursor-grabbing"
            >
                {/* Top glow indicator */}
                <div className="h-[2px] w-full bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-70" />

                <div className="p-3.5 flex flex-col gap-3">
                    {/* Header */}
                    <div className="flex items-center justify-between pb-2 border-b border-cyan-500/15">
                        <div className="flex items-center gap-1.5 cursor-grab text-cyan-500/60">
                            <GripHorizontal size={13} />
                            <Activity size={13} className="text-cyan-400 animate-pulse" />
                            <span className="text-[10px] font-mono tracking-widest text-cyan-300 font-bold uppercase">
                                SYSTEM HUD
                            </span>
                        </div>
                        <button
                            onClick={() => setIsVisible(false)}
                            className="p-1 rounded-md text-cyan-500/50 hover:text-cyan-300 hover:bg-cyan-500/10 transition-colors cursor-pointer"
                        >
                            <X size={13} />
                        </button>
                    </div>

                    {/* Metrics grid */}
                    <div className="flex flex-col gap-3">
                        <MetricBar icon={Cpu} label="CPU Core" value={stats.cpu_percent} color="#00B7FF" />
                        <MetricBar icon={Activity} label={`RAM (${stats.ram_used_gb}/${stats.ram_total_gb}GB)`} value={stats.ram_percent} color="#818cf8" />
                        <MetricBar icon={HardDrive} label="Disk SSD" value={stats.disk_percent} color="#34d399" />
                        <MetricBar
                            icon={stats.power_plugged ? Zap : Battery}
                            label={stats.power_plugged ? "Power (AC Connected)" : "Battery"}
                            value={stats.battery_percent}
                            color={stats.battery_percent <= 20 ? "#ef4444" : "#fbbf24"}
                        />
                    </div>
                </div>
            </motion.div>
        </AnimatePresence>
    );
}
