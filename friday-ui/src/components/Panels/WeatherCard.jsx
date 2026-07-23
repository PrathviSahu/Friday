import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence, useDragControls, useMotionValue, useSpring } from 'framer-motion';
import { Sun, CloudRain, Cloud, Wind, Droplets, MapPin, X, GripHorizontal } from 'lucide-react';
import { useOrbState } from '../../hooks/useOrbState';

const API = 'http://localhost:8000/api/weather';

function AnimatedWeatherIcon({ condition = '', icon = '🌤️', isDragging = false }) {
    const condLower = (condition || '').toLowerCase();

    let animConfig = { y: [0, -6, 0], rotate: [0, 4, -4, 0], scale: [1, 1.04, 1] };

    if (condLower.includes('rain') || condLower.includes('drizzle') || condLower.includes('shower')) {
        animConfig = { y: [0, -4, 2, 0], rotate: [-2, 2, -2], scale: [1, 1.03, 1] };
    } else if (condLower.includes('sun') || condLower.includes('clear')) {
        animConfig = { y: [0, -7, 0], rotate: [0, 12, 0], scale: [1, 1.05, 1] };
    } else if (condLower.includes('cloud') || condLower.includes('overcast')) {
        animConfig = { x: [-4, 4, -4], y: [0, -3, 0], scale: [1, 1.03, 1] };
    }

    return (
        <motion.div
            animate={isDragging ? { scale: 1, y: 0, rotate: 0 } : animConfig}
            transition={{ repeat: Infinity, duration: 4.5, ease: 'easeInOut' }}
            style={{ fontSize: 34, userSelect: 'none', cursor: 'default', lineHeight: 1 }}
        >
            {icon}
        </motion.div>
    );
}

export default function WeatherCard() {
    const { workspace } = useOrbState();
    const [isVisible, setIsVisible] = useState(false);
    const [weather, setWeather] = useState({
        city: 'Locating…',
        temperature: '--',
        feels_like: '--',
        humidity: '--',
        wind_speed: '--',
        condition: 'Fetching weather…',
        icon: '🌤️',
        temp_max: '--',
        temp_min: '--',
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
        rawRotateX.set(Math.max(-24, Math.min(24, -info.velocity.y * 0.045)));
        rawRotateY.set(Math.max(-24, Math.min(24, info.velocity.x * 0.045)));
    };

    const handleDragEnd = () => {
        setIsDragging(false);
        rawRotateX.set(0);
        rawRotateY.set(0);
    };

    const fetchWeather = async () => {
        try {
            const res = await fetch(API);
            if (res.ok) setWeather(await res.json());
        } catch (_) {}
    };

    useEffect(() => {
        fetchWeather();
        const iv = setInterval(fetchWeather, 300000);
        return () => clearInterval(iv);
    }, []);

    if (workspace === 'trading') return null;

    if (!isVisible) {
        return (
            <motion.div
                drag
                dragConstraints={{ left: -100, right: 1000, top: -100, bottom: 800 }}
                dragElastic={0.1}
                whileDrag={{ scale: 1.05 }}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setIsVisible(true)}
                style={{
                    position: 'fixed', top: 32, left: 40, zIndex: 50,
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '7px 14px', borderRadius: 99,
                    cursor: 'grab', pointerEvents: 'auto', userSelect: 'none',
                    background: '#0f0f1a', border: '1px solid #1e1b4b',
                    color: '#7dd3fc', fontSize: 11, fontFamily: 'monospace',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.6)'
                }}
            >
                <Sun size={14} style={{ color: '#fbbf24' }} />
                <span>{weather.city} {weather.temperature}°C</span>
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
                    position: 'fixed', top: 32, left: 40, zIndex: 40,
                    width: 280,
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
                {/* Drag handle strips — 45px clear zone at top-right for X button */}
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', top: 0, left: 0, right: 45, height: 10, cursor: 'grab', zIndex: 50 }} />
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', top: 0, bottom: 0, left: 0, width: 10, cursor: 'grab', zIndex: 50 }} />
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', top: 35, bottom: 0, right: 0, width: 10, cursor: 'grab', zIndex: 50 }} />
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 10, cursor: 'grab', zIndex: 50 }} />

                {/* Top glow line */}
                <div style={{ height: 2, background: 'linear-gradient(90deg, transparent, #7dd3fc, transparent)', opacity: 0.7 }} />

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
                        <GripHorizontal size={13} style={{ color: '#1e3a5f' }} />
                        <MapPin size={14} style={{ color: '#38bdf8' }} />
                        <span style={{ fontSize: 13, fontWeight: 700, color: '#e0f2fe', letterSpacing: '-0.01em' }}>
                            {weather.city}
                        </span>
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
                            color: '#1e3a5f', padding: 4, display: 'flex',
                            position: 'relative', zIndex: 100
                        }}
                        onMouseEnter={e => e.currentTarget.style.color = '#7dd3fc'}
                        onMouseLeave={e => e.currentTarget.style.color = '#1e3a5f'}
                        title="Close Weather"
                    >
                        <X size={14} />
                    </button>
                </div>

                {/* Main temperature section — centered */}
                <div style={{ padding: '14px 16px 12px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                    {/* Icon + temp side by side */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10 }}>
                        <AnimatedWeatherIcon condition={weather.condition} icon={weather.icon} isDragging={isDragging} />
                        <div style={{ display: 'flex', alignItems: 'baseline', gap: 3 }}>
                            <span style={{ fontSize: 50, fontWeight: 900, color: '#fff', letterSpacing: '-3px', lineHeight: 1 }}>
                                {weather.temperature}
                            </span>
                            <span style={{ fontSize: 20, fontWeight: 700, color: '#38bdf8' }}>°C</span>
                        </div>
                    </div>

                    {/* Condition label */}
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                        <span style={{
                            fontSize: 12, fontWeight: 600, color: '#bae6fd',
                            background: 'rgba(56,189,248,0.1)', border: '1px solid rgba(56,189,248,0.2)',
                            padding: '3px 12px', borderRadius: 99
                        }}>
                            {weather.condition}
                        </span>
                        <span style={{ fontSize: 10, color: '#475569', fontFamily: 'monospace', letterSpacing: '0.05em' }}>
                            High {weather.temp_max}° · Low {weather.temp_min}°
                        </span>
                    </div>
                </div>

                {/* Divider */}
                <div style={{ height: 1, background: '#1e1b4b', margin: '0 16px' }} />

                {/* Stats row */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6, padding: '10px 16px 14px' }}>
                    {[
                        { label: 'Feels', value: `${weather.feels_like}°C`, color: '#7dd3fc' },
                        { label: 'Humidity', value: `${weather.humidity}%`, color: '#67e8f9', icon: <Droplets size={12} style={{ color: '#67e8f9' }} /> },
                        { label: 'Wind', value: `${weather.wind_speed} km/h`, color: '#6ee7b7', icon: <Wind size={12} style={{ color: '#6ee7b7' }} /> },
                    ].map(({ label, value, color, icon }) => (
                        <div key={label} style={{
                            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                            gap: 4, padding: '8px 4px',
                            background: '#141428', border: '1px solid #1e1b4b', borderRadius: 12
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 3, color: '#64748b', fontSize: 10, fontWeight: 500 }}>
                                {icon}
                                <span>{label}</span>
                            </div>
                            <span style={{ fontSize: 12, fontWeight: 700, color, fontFamily: 'monospace' }}>{value}</span>
                        </div>
                    ))}
                </div>
            </motion.div>
        </AnimatePresence>
    );
}
