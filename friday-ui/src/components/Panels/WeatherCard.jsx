import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sun, CloudRain, Cloud, Wind, Droplets, MapPin, X, GripHorizontal } from 'lucide-react';

const API = 'http://localhost:8000/api/weather';

export default function WeatherCard() {
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

    const fetchWeather = async () => {
        try {
            const res = await fetch(API);
            if (res.ok) setWeather(await res.json());
        } catch (_) {}
    };

    useEffect(() => {
        fetchWeather();
        const iv = setInterval(fetchWeather, 600000); // refresh every 10 min
        return () => clearInterval(iv);
    }, []);

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
                className="fixed top-8 left-10 z-50 flex items-center gap-2 px-3.5 py-2 rounded-full cursor-grab active:cursor-grabbing pointer-events-auto select-none bg-[#0a101d]/90 border border-sky-500/30 text-sky-400 shadow-[0_4px_20px_rgba(56,189,248,0.2)] text-[11px] font-mono"
            >
                <Sun size={14} className="text-amber-400 animate-spin-slow" />
                <span>{weather.city} {weather.temperature}°C</span>
            </motion.div>
        );
    }

    return (
        <AnimatePresence>
            <motion.div
                drag
                dragConstraints={{ left: -100, right: 900, top: -100, bottom: 600 }}
                dragElastic={0.1}
                whileDrag={{ scale: 1.02, cursor: 'grabbing' }}
                initial={{ opacity: 0, y: -20, scale: 0.94 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                className="fixed top-8 left-10 z-40 w-64 rounded-2xl pointer-events-auto select-none overflow-hidden bg-[#070d18]/92 border border-sky-500/25 shadow-[0_16px_50px_rgba(0,0,0,0.8),0_0_20px_rgba(56,189,248,0.15)] backdrop-blur-xl cursor-grab active:cursor-grabbing font-sans"
            >
                {/* Top ambient glow line */}
                <div className="h-[2px] w-full bg-gradient-to-r from-transparent via-sky-400 to-transparent opacity-70" />

                <div className="p-3.5 flex flex-col gap-3">
                    {/* Header bar */}
                    <div className="flex items-center justify-between pb-2 border-b border-sky-500/15">
                        <div className="flex items-center gap-1.5 text-sky-500/60">
                            <GripHorizontal size={13} />
                            <MapPin size={12} className="text-sky-400" />
                            <span className="text-[11px] font-semibold text-sky-200 tracking-wide uppercase">
                                {weather.city}
                            </span>
                        </div>
                        <button
                            onClick={() => setIsVisible(false)}
                            className="p-1 rounded-md text-sky-500/50 hover:text-sky-300 hover:bg-sky-500/10 transition-colors cursor-pointer"
                        >
                            <X size={13} />
                        </button>
                    </div>

                    {/* Main Temp & Condition */}
                    <div className="flex items-center justify-between px-1">
                        <div className="flex flex-col">
                            <div className="flex items-baseline gap-1">
                                <span className="text-3xl font-extrabold text-white tracking-tight">
                                    {weather.temperature}
                                </span>
                                <span className="text-lg font-bold text-sky-400">°C</span>
                            </div>
                            <span className="text-[11px] font-medium text-slate-300 mt-0.5">
                                {weather.condition}
                            </span>
                            <span className="text-[9px] text-slate-400 font-mono">
                                High {weather.temp_max}° · Low {weather.temp_min}°
                            </span>
                        </div>

                        {/* Large condition emoji / icon */}
                        <div className="text-4xl filter drop-shadow-[0_0_12px_rgba(56,189,248,0.4)]">
                            {weather.icon}
                        </div>
                    </div>

                    {/* Detailed stats grid */}
                    <div className="grid grid-cols-3 gap-1.5 pt-2 border-t border-sky-500/15 text-[10px]">
                        <div className="flex flex-col items-center justify-center p-2 rounded-xl bg-sky-950/40 border border-sky-500/10">
                            <span className="text-slate-400 text-[9px]">Feels</span>
                            <span className="font-bold text-sky-300 mt-0.5">{weather.feels_like}°C</span>
                        </div>
                        <div className="flex flex-col items-center justify-center p-2 rounded-xl bg-sky-950/40 border border-sky-500/10">
                            <div className="flex items-center gap-1 text-slate-400 text-[9px]">
                                <Droplets size={10} className="text-cyan-400" />
                                <span>Humidity</span>
                            </div>
                            <span className="font-bold text-cyan-300 mt-0.5">{weather.humidity}%</span>
                        </div>
                        <div className="flex flex-col items-center justify-center p-2 rounded-xl bg-sky-950/40 border border-sky-500/10">
                            <div className="flex items-center gap-1 text-slate-400 text-[9px]">
                                <Wind size={10} className="text-emerald-400" />
                                <span>Wind</span>
                            </div>
                            <span className="font-bold text-emerald-300 mt-0.5">{weather.wind_speed} <span className="text-[8px]">km/h</span></span>
                        </div>
                    </div>
                </div>
            </motion.div>
        </AnimatePresence>
    );
}
