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
import { FridayProvider } from './context/FridayContext';
import FridaySync from './context/FridaySync';
import { useProactiveSuggestions } from './hooks/useProactiveSuggestions';
import { useOrbState } from './hooks/useOrbState';

function FridayCore() {
    const { workspace, locked } = useOrbState();
    const isCareerWorkspace = workspace === 'career';
    const [proactiveToast, setProactiveToast] = useState(null);
    const pendingActionRef = useRef(null); // holds confirmPendingAction fn when action is pending

    // Lock screen is clean by default: only the Spotify capsule stays visible.
    // All other capsules (coach, weather, permissions, inbox, todos, …) are
    // hidden behind the "ALL WIDGETS" button while locked.
    const [lockExtrasVisible, setLockExtrasVisible] = useState(false);
    const showExtraCapsules = !isCareerWorkspace && (!locked || lockExtrasVisible);

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
            {/* On Job Portal / Career OS, keep ONLY Spotify Card active and hide all other floating capsules.
                On the LOCKED screen the extra capsules are hidden behind the "ALL WIDGETS" button —
                Spotify stays visible as-is. */}
            <SpotifyCard />
            {showExtraCapsules && <TodoCard />}
            {showExtraCapsules && <SystemMonitorCard />}
            {showExtraCapsules && <WeatherCard />}
            {showExtraCapsules && <WebSearchCard />}
            {showExtraCapsules && <PermissionCenterCard />}
            {showExtraCapsules && <NotificationCenterCard />}
            {showExtraCapsules && <LearningCoachCard />}
            {showExtraCapsules && <DevToolsCard />}
            {showExtraCapsules && <KnowledgeCard />}
            {showExtraCapsules && <EmailCard />}
            {showExtraCapsules && <CalendarCard />}

            {/* Lock screen: button to reveal/hide the extra capsules (all except Spotify) */}
            {locked && !isCareerWorkspace && (
                <motion.button
                    onClick={() => setLockExtrasVisible((v) => !v)}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.7, duration: 0.6 }}
                    className="fixed bottom-8 left-10 z-[60] flex cursor-pointer items-center gap-2.5 rounded-full border border-[#00B7FF]/40 bg-[#001018]/85 px-5 py-2.5 font-orbitron text-[9px] uppercase tracking-[0.35em] text-[#00D9FF] shadow-[0_0_24px_rgba(0,183,255,0.15)] backdrop-blur-md transition-all hover:border-[#00B7FF]/70 hover:bg-[#001018] hover:shadow-[0_0_32px_rgba(0,183,255,0.3)]"
                    style={{ pointerEvents: 'auto' }}
                >
                    <span className={`inline-block h-2 w-2 rounded-full ${lockExtrasVisible ? 'bg-[#22ff99] shadow-[0_0_8px_#22ff99]' : 'bg-[#00B7FF] shadow-[0_0_8px_#00B7FF]'}`} />
                    {lockExtrasVisible ? 'HIDE WIDGETS' : 'ALL WIDGETS'}
                </motion.button>
            )}
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
