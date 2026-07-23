import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence, useDragControls, useMotionValue, useSpring } from 'framer-motion';
import { Cpu, HardDrive, Battery, Zap, X, GripHorizontal, Activity, Sun, Moon, Volume2, VolumeX, Lock } from 'lucide-react';
import { useOrbState } from '../../hooks/useOrbState';

const API_STATS = 'http://localhost:8000/api/system/stats';
const API_DISPLAY = 'http://localhost:8000/api/system/display';

function MetricBar({ icon: Icon, label, value, color, unit = '%' }) {
    const isHigh = value > 85;
    const barColor = isHigh ? '#ef4444' : color;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 11 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#94a3b8', fontWeight: 500 }}>
                    <Icon size={13} style={{ color: barColor }} />
                    <span>{label}</span>
                </div>
                <span style={{ fontFamily: 'monospace', fontWeight: 700, color: barColor }}>
                    {value}{unit}
                </span>
            </div>
            <div style={{ height: 5, width: '100%', background: '#1e1b4b', borderRadius: 99, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.05)' }}>
                <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(100, Math.max(0, value))}%` }}
                    transition={{ duration: 0.5, ease: 'easeOut' }}
                    style={{
                        height: '100%',
                        borderRadius: 99,
                        background: `linear-gradient(90deg, ${barColor}99, ${barColor})`,
                        boxShadow: `0 0 8px ${barColor}55`
                    }}
                />
            </div>
        </div>
    );
}

export default function SystemMonitorCard() {
    const { workspace } = useOrbState();
    const [isVisible, setIsVisible] = useState(false);
    const [stats, setStats] = useState({
        cpu_percent: 0,
        ram_percent: 0,
        ram_used_gb: 0,
        ram_total_gb: 0,
        disk_percent: 0,
        battery_percent: 100,
        power_plugged: true
    });

    const [displayInfo, setDisplayInfo] = useState({
        brightness: 75,
        dark_mode: true,
        volume: 70,
        muted: false
    });

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
        const vx = info.velocity.x;
        const vy = info.velocity.y;
        rawRotateX.set(Math.max(-24, Math.min(24, -vy * 0.045)));
        rawRotateY.set(Math.max(-24, Math.min(24, vx * 0.045)));
    };

    const handleDragEnd = () => {
        setIsDragging(false);
        rawRotateX.set(0);
        rawRotateY.set(0);
    };

    const fetchStats = async () => {
        try {
            const res = await fetch(API_STATS);
            if (res.ok) setStats(await res.json());
        } catch (_) {}
    };

    const fetchDisplayInfo = async () => {
        try {
            const res = await fetch(API_DISPLAY);
            if (res.ok) setDisplayInfo(await res.json());
        } catch (_) {}
    };

    useEffect(() => {
        fetchStats();
        fetchDisplayInfo();
        const iv1 = setInterval(fetchStats, 3000);
        const iv2 = setInterval(fetchDisplayInfo, 5000);
        return () => { clearInterval(iv1); clearInterval(iv2); };
    }, []);

    const handleBrightnessChange = (newVal) => {
        setDisplayInfo(prev => ({ ...prev, brightness: newVal }));
        fetch(`${API_DISPLAY}/brightness`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ level: newVal })
        }).catch(() => {});
    };

    const handleToggleDarkMode = () => {
        const target = !displayInfo.dark_mode;
        setDisplayInfo(prev => ({ ...prev, dark_mode: target }));
        fetch(`${API_DISPLAY}/dark-mode`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: target })
        }).catch(() => {});
    };

    const handleVolumeChange = (newVal) => {
        setDisplayInfo(prev => ({ ...prev, volume: newVal }));
        fetch(`${API_DISPLAY}/volume`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ level: newVal })
        }).catch(() => {});
    };

    const handleToggleMute = () => {
        const target = !displayInfo.muted;
        setDisplayInfo(prev => ({ ...prev, muted: target }));
        fetch(`${API_DISPLAY}/mute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ muted: target })
        }).catch(() => {});
    };

    const handleLockDisplay = () => {
        fetch(`${API_DISPLAY}/lock`, { method: 'POST' }).catch(() => {});
    };

    if (workspace === 'trading') return null;

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
                style={{
                    position: 'fixed', top: 32, right: 40, zIndex: 50,
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '7px 14px', borderRadius: 99,
                    cursor: 'grab', pointerEvents: 'auto', userSelect: 'none',
                    background: '#0f0f1a', border: '1px solid #1e1b4b',
                    color: '#67e8f9', fontSize: 11, fontFamily: 'monospace',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.6)'
                }}
            >
                <Activity size={13} style={{ animation: 'pulse 2s infinite' }} />
                <span>CPU {stats.cpu_percent}%</span>
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
                    position: 'fixed', top: 32, right: 40, zIndex: 40,
                    width: 310,
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
                {/* Drag handle strips */}
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', top: 0, left: 0, right: 45, height: 10, cursor: 'grab', zIndex: 50 }} />
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', top: 0, bottom: 0, left: 0, width: 10, cursor: 'grab', zIndex: 50 }} />
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', top: 35, bottom: 0, right: 0, width: 10, cursor: 'grab', zIndex: 50 }} />
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 10, cursor: 'grab', zIndex: 50 }} />

                {/* Top glow line */}
                <div style={{ height: 2, background: 'linear-gradient(90deg, transparent, #67e8f9, transparent)', opacity: 0.7 }} />

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
                        <GripHorizontal size={13} style={{ color: '#164e63' }} />
                        <Activity size={14} style={{ color: '#22d3ee' }} />
                        <span style={{ fontSize: 13, fontWeight: 700, color: '#e0f2fe', letterSpacing: '-0.01em' }}>System HUD</span>
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
                            color: '#164e63', padding: 4, display: 'flex',
                            position: 'relative', zIndex: 100
                        }}
                        onMouseEnter={e => e.currentTarget.style.color = '#67e8f9'}
                        onMouseLeave={e => e.currentTarget.style.color = '#164e63'}
                        title="Close System HUD"
                    >
                        <X size={14} />
                    </button>
                </div>

                {/* Metrics & Hardware Controls */}
                <div style={{ padding: '14px 16px 16px', display: 'flex', flexDirection: 'column', gap: 14 }}>
                    <MetricBar icon={Cpu} label="CPU Core" value={stats.cpu_percent} color="#22d3ee" />
                    <MetricBar icon={Activity} label={`RAM (${stats.ram_used_gb}/${stats.ram_total_gb} GB)`} value={stats.ram_percent} color="#818cf8" />
                    <MetricBar icon={HardDrive} label="Disk SSD" value={stats.disk_percent} color="#34d399" />
                    <MetricBar
                        icon={stats.power_plugged ? Zap : Battery}
                        label={stats.power_plugged ? 'Power (AC)' : 'Battery'}
                        value={stats.battery_percent}
                        color={stats.battery_percent <= 20 ? '#ef4444' : '#fbbf24'}
                    />

                    {/* Divider */}
                    <div style={{ height: 1, background: '#1e1b4b', margin: '2px 0' }} />

                    {/* Hardware & Display Quick Controls */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                        <span style={{ fontSize: 10, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', fontFamily: 'monospace', letterSpacing: '0.05em' }}>
                            Display & Audio
                        </span>

                        {/* Brightness Control */}
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#94a3b8', fontSize: 11 }}>
                                <Sun size={13} style={{ color: '#fbbf24' }} />
                                <span>Brightness</span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, maxWidth: 140 }}>
                                <input
                                    type="range"
                                    min="10"
                                    max="100"
                                    value={displayInfo.brightness}
                                    onChange={e => handleBrightnessChange(Number(e.target.value))}
                                    style={{ flex: 1, accentColor: '#fbbf24', cursor: 'pointer', height: 4 }}
                                />
                                <span style={{ fontFamily: 'monospace', fontSize: 11, fontWeight: 700, color: '#fbbf24', width: 30, textAlign: 'right' }}>
                                    {displayInfo.brightness}%
                                </span>
                            </div>
                        </div>

                        {/* Volume Control */}
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                            <button
                                onClick={handleToggleMute}
                                style={{ display: 'flex', alignItems: 'center', gap: 6, color: displayInfo.muted ? '#ef4444' : '#94a3b8', fontSize: 11, background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                                title={displayInfo.muted ? 'Unmute Volume' : 'Mute Volume'}
                            >
                                {displayInfo.muted ? <VolumeX size={13} style={{ color: '#ef4444' }} /> : <Volume2 size={13} style={{ color: '#67e8f9' }} />}
                                <span>{displayInfo.muted ? 'Muted' : 'Volume'}</span>
                            </button>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, maxWidth: 140 }}>
                                <input
                                    type="range"
                                    min="0"
                                    max="100"
                                    value={displayInfo.volume}
                                    onChange={e => handleVolumeChange(Number(e.target.value))}
                                    style={{ flex: 1, accentColor: '#67e8f9', cursor: 'pointer', height: 4 }}
                                />
                                <span style={{ fontFamily: 'monospace', fontSize: 11, fontWeight: 700, color: '#67e8f9', width: 30, textAlign: 'right' }}>
                                    {displayInfo.volume}%
                                </span>
                            </div>
                        </div>

                        {/* Dark Mode & Lock Buttons */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                            <button
                                onClick={handleToggleDarkMode}
                                style={{
                                    flex: 1,
                                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                                    padding: '6px 10px', borderRadius: 8,
                                    background: displayInfo.dark_mode ? 'rgba(34,211,238,0.12)' : 'rgba(255,255,255,0.06)',
                                    border: displayInfo.dark_mode ? '1px solid rgba(34,211,238,0.3)' : '1px solid rgba(255,255,255,0.1)',
                                    color: displayInfo.dark_mode ? '#38bdf8' : '#94a3b8',
                                    fontSize: 11, fontWeight: 600, cursor: 'pointer', transition: 'all 0.2s'
                                }}
                            >
                                <Moon size={13} />
                                <span>{displayInfo.dark_mode ? 'Dark Mode' : 'Light Mode'}</span>
                            </button>

                            <button
                                onClick={handleLockDisplay}
                                style={{
                                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                                    padding: '6px 12px', borderRadius: 8,
                                    background: 'rgba(239,68,68,0.12)',
                                    border: '1px solid rgba(239,68,68,0.3)',
                                    color: '#f87171',
                                    fontSize: 11, fontWeight: 600, cursor: 'pointer', transition: 'all 0.2s'
                                }}
                                title="Lock macOS Display"
                            >
                                <Lock size={13} />
                                <span>Lock</span>
                            </button>
                        </div>
                    </div>
                </div>
            </motion.div>
        </AnimatePresence>
    );
}
