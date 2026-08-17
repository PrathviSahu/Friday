import './index.css';
import { useState, useEffect, useRef } from 'react';
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
import PermissionCenterCard from './components/Panels/PermissionCenterCard';
import NotificationCenterCard from './components/Panels/NotificationCenterCard';
import LearningCoachCard from './components/Panels/LearningCoachCard';
import DevToolsCard from './components/Panels/DevToolsCard';
import KnowledgeCard from './components/Panels/KnowledgeCard';
import EmailCard from './components/Panels/EmailCard';
import CalendarCard from './components/Panels/CalendarCard';
import MeetingsCard from './components/Panels/MeetingsCard';
import WhatsAppCard from './components/Panels/WhatsAppCard';
import DocumentsCard from './components/Panels/DocumentsCard';
import CodingCard from './components/Panels/CodingCard';
import SlidingDashboard from './components/Panels/SlidingDashboard';
import { FridayProvider } from './context/FridayContext';
import FridaySync from './context/FridaySync';
import { useProactiveSuggestions } from './hooks/useProactiveSuggestions';
import { useOrbState } from './hooks/useOrbState';

function FridayCore() {
    const { workspace, locked } = useOrbState();
    const isCareerWorkspace = workspace === 'career';
    const [proactiveToast, setProactiveToast] = useState(null);
    const pendingActionRef = useRef(null); // holds confirmPendingAction fn when action is pending

    // Clean Screen Design: Only Spotify stays active on the main desktop.
    // All other capsules (coach, weather, permissions, inbox, todos, …) are neatly
    // organized inside the Sliding Dashboard drawer panel.
    const [dashboardOpen, setDashboardOpen] = useState(false);
    const [actionBanner, setActionBanner]   = useState(null); // { title, subtitle, url, label, type }

    useEffect(() => {
        const handleOpen = () => setDashboardOpen(true);
        const handleAction = (e) => {
            if (e.detail?.url) {
                setActionBanner(e.detail);
            }
        };
        window.addEventListener('friday-open-dashboard', handleOpen);
        window.addEventListener('friday-external-action', handleAction);
        return () => {
            window.removeEventListener('friday-open-dashboard', handleOpen);
            window.removeEventListener('friday-external-action', handleAction);
        };
    }, []);

    const { confirmPendingAction } = useProactiveSuggestions({
        enabled: true,
        onSuggestion: ({ message }) => {
            setProactiveToast(message);
            setTimeout(() => setProactiveToast(null), 8000);
        },
        onPendingAction: (action) => {
            // When action goes pending, store the confirm fn; when cleared, null it out
            if (action) {
                pendingActionRef.current = confirmPendingAction;
            } else {
                pendingActionRef.current = null;
            }
        },
    });

    // Expose a global hook so useSpeech can check for pending confirmation BEFORE routing to AI
    useEffect(() => {
        const YES_WORDS = /^(yes|yeah|yep|yup|sure|ok|okay|haan|ha|play it|go ahead|do it)$/i;

        window.fridayCheckPendingConfirmation = async (transcript) => {
            const trimmed = (transcript || '').trim();
            if (pendingActionRef.current && YES_WORDS.test(trimmed)) {
                console.log('[Proactive] Voice confirmation received:', trimmed);
                await pendingActionRef.current();
                pendingActionRef.current = null;
                return true; // signal: handled, don't send to AI
            }
            return false; // not a confirmation, route normally
        };

        return () => {
            delete window.fridayCheckPendingConfirmation;
        };
    }, [confirmPendingAction]);

    return (
        <>
            <FridaySync />
            <LockScreen />
            <Workspace />
            {/* Clean Desktop: Only Spotify Card stays floating on the background screen */}
            <SpotifyCard />

            {/* Button to open the Sliding Dashboard drawer panel */}
            {!isCareerWorkspace && (
                <motion.button
                    onClick={() => setDashboardOpen((v) => !v)}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.7, duration: 0.6 }}
                    className="fixed bottom-4 left-4 sm:bottom-8 sm:left-10 z-[60] flex cursor-pointer items-center gap-2 sm:gap-2.5 rounded-full border border-[#00B7FF]/40 bg-[#001018]/85 px-3.5 sm:px-5 py-2 sm:py-2.5 font-orbitron text-[8.5px] sm:text-[9px] uppercase tracking-[0.25em] sm:tracking-[0.35em] text-[#00D9FF] shadow-[0_0_24px_rgba(0,183,255,0.15)] backdrop-blur-md transition-all hover:border-[#00B7FF]/70 hover:bg-[#001018] hover:shadow-[0_0_32px_rgba(0,183,255,0.3)]"
                    style={{ pointerEvents: 'auto' }}
                >
                    <span className={`inline-block h-2 w-2 rounded-full ${dashboardOpen ? 'bg-[#22ff99] shadow-[0_0_8px_#22ff99]' : 'bg-[#00B7FF] shadow-[0_0_8px_#00B7FF]'}`} />
                    ⚡ DASHBOARD
                </motion.button>
            )}

            <SlidingDashboard isOpen={dashboardOpen} onClose={() => setDashboardOpen(false)} />
            <DebugKeys />

            {/* ── Proactive Suggestion Toast ── */}
            {/* Holographic Action Banner (WhatsApp Web, Links, Quick Actions) */}
            <AnimatePresence>
                {actionBanner && (
                    <motion.div
                        initial={{ opacity: 0, y: -50, scale: 0.9 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: -50, scale: 0.9 }}
                        transition={{ type: 'spring', stiffness: 350, damping: 25 }}
                        style={{
                            position: 'fixed',
                            top: 24,
                            left: '50%',
                            transform: 'translateX(-50%)',
                            zIndex: 10000,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 12,
                            padding: '10px 16px',
                            borderRadius: 14,
                            background: 'rgba(3, 16, 28, 0.96)',
                            border: '1px solid #00B7FF',
                            boxShadow: '0 0 30px rgba(0, 183, 255, 0.35), 0 16px 48px rgba(0,0,0,0.8)',
                            backdropFilter: 'blur(20px)',
                            pointerEvents: 'auto',
                        }}
                    >
                        <div style={{
                            width: 32,
                            height: 32,
                            borderRadius: 8,
                            background: 'rgba(37, 211, 102, 0.2)',
                            border: '1px solid rgba(37, 211, 102, 0.5)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: 16,
                            color: '#25D366',
                            flexShrink: 0
                        }}>
                            💬
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', minWidth: 140 }}>
                            <span style={{ fontFamily: 'Orbitron, sans-serif', fontSize: 11, fontWeight: 700, color: '#DFFAFF', letterSpacing: '0.08em' }}>
                                {actionBanner.title}
                            </span>
                            {actionBanner.subtitle && (
                                <span style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 11, color: '#94a3b8', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 280 }}>
                                    {actionBanner.subtitle}
                                </span>
                            )}
                        </div>
                        <a
                            href={actionBanner.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={() => setActionBanner(null)}
                            style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 6,
                                padding: '6px 14px',
                                borderRadius: 8,
                                background: '#25D366',
                                color: '#052e16',
                                fontFamily: 'Orbitron, sans-serif',
                                fontSize: 10,
                                fontWeight: 800,
                                letterSpacing: '0.08em',
                                textDecoration: 'none',
                                cursor: 'pointer',
                                boxShadow: '0 0 16px rgba(37, 211, 102, 0.4)',
                                whiteSpace: 'nowrap',
                                transition: 'transform 0.15s ease',
                            }}
                        >
                            <span>{actionBanner.label || 'OPEN NOW'}</span>
                            <span style={{ fontSize: 12 }}>↗</span>
                        </a>
                        <button
                            onClick={() => setActionBanner(null)}
                            style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', padding: 4, fontSize: 14, marginLeft: 4 }}
                        >
                            ✕
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>

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
