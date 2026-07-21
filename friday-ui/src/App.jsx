import './index.css';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { OrbProvider } from './hooks/useOrbState';
import LockScreen from './components/LockScreen/LockScreen';
import Workspace from './UI/Workspace';
import DebugKeys from './components/Debug/DebugKeys';
import SpotifyCard from './components/Panels/SpotifyCard';
import TodoCard from './components/Panels/TodoCard';
import SystemMonitorCard from './components/Panels/SystemMonitorCard';
import WeatherCard from './components/Panels/WeatherCard';
import WebSearchCard from './components/Panels/WebSearchCard';
import { FridayProvider } from './context/FridayContext';
import FridaySync from './context/FridaySync';
import { useProactiveSuggestions } from './hooks/useProactiveSuggestions';

function FridayCore() {
    const [proactiveToast, setProactiveToast] = useState(null);

    useProactiveSuggestions({
        enabled: true,
        onSuggestion: ({ message }) => {
            setProactiveToast(message);
            setTimeout(() => setProactiveToast(null), 8000);
        },
    });

    return (
        <>
            <FridaySync />
            <LockScreen />
            <Workspace />
            <SpotifyCard />
            <TodoCard />
            <SystemMonitorCard />
            <WeatherCard />
            <WebSearchCard />
            <DebugKeys />

            {/* ── Proactive Suggestion Toast ── */}
            <AnimatePresence>
                {proactiveToast && (
                    <motion.div
                        initial={{ opacity: 0, y: 20, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 10, scale: 0.95 }}
                        transition={{ type: 'spring', stiffness: 300, damping: 28 }}
                        style={{
                            position: 'fixed', bottom: 28, left: '50%', transform: 'translateX(-50%)',
                            zIndex: 9999, maxWidth: 380, width: 'max-content',
                            background: 'rgba(10, 16, 40, 0.96)',
                            border: '1px solid rgba(99, 102, 241, 0.4)',
                            borderRadius: 14, padding: '12px 18px',
                            boxShadow: '0 16px 48px rgba(0,0,0,0.6), 0 0 0 1px rgba(99,102,241,0.1)',
                            backdropFilter: 'blur(20px)',
                            display: 'flex', alignItems: 'center', gap: 10,
                            pointerEvents: 'none',
                            fontFamily: 'Inter, system-ui, sans-serif',
                        }}
                    >
                        {/* Pulsing orb */}
                        <motion.div
                            animate={{ scale: [1, 1.2, 1], opacity: [0.8, 1, 0.8] }}
                            transition={{ duration: 1.6, repeat: Infinity }}
                            style={{ width: 8, height: 8, borderRadius: '50%', background: '#6366f1', flexShrink: 0, boxShadow: '0 0 10px #6366f1' }}
                        />
                        <div>
                            <div style={{ fontSize: 9, fontWeight: 700, color: '#818cf8', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 3 }}>
                                F.R.I.D.A.Y. · Proactive
                            </div>
                            <div style={{ fontSize: 13, color: '#e0e7ff', lineHeight: 1.4 }}>
                                {proactiveToast}
                            </div>
                        </div>
                        <button
                            onClick={() => setProactiveToast(null)}
                            style={{ background: 'none', border: 'none', color: '#4338ca', cursor: 'pointer', padding: 4, flexShrink: 0, pointerEvents: 'auto' }}
                        >
                            ✕
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
}

export default function App() {
    return (
        <FridayProvider>
            <OrbProvider>
                <FridayCore />
            </OrbProvider>
        </FridayProvider>
    );
}
