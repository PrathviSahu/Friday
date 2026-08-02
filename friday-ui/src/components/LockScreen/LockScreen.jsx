import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Background from '../Background/Background';
import AccessCard from '../Panels/AccessCard';
import StatusCard from '../StatusPanel/StatusCard';
import BottomBar from '../Panels/BottomBar';
import Corners from '../Animations/Corners';
import HudOrb from '../AICore/HudOrb';
import Clock from '../Clock/Clock';
import { useOrbState } from '../../hooks/useOrbState';
import { useSpeech } from '../../hooks/useSpeech';
import { useFriday } from '../../context/FridayContext';
import { useFitScale } from '../../hooks/useFitScale';
import { speak, stopSpeaking } from '../../services/ttsService';

export default function LockScreen() {
    const orb = useOrbState();
    const { authStep, responseMessage, audioEnabled, enableAudioFromGesture, ttsLoading, isSpeaking, locked, unlockWithFingerprintFlow, setResponseMessage, workspace, setWorkspace, lockNow } = orb;
    const { micEnabled } = useFriday();
    const scale = useFitScale();
    const isAmbient = !locked && workspace === 'unlocked';

    // FRIDAY's conversation loop: show text on screen when speech is returned.
    const handleConversation = React.useCallback(({ reply, action }) => {
        if (reply) {
            setResponseMessage?.(reply);
        }
        if (action && action !== 'none' && !locked) {
            if (action === 'trading')   setWorkspace?.('trading');
            else if (action === 'dashboard') setWorkspace?.('dashboard');
            else if (action === 'career')    setWorkspace?.('career');
            else if (action === 'lock') lockNow?.();
        }
    }, [setResponseMessage, setWorkspace, locked, lockNow]);

    // ── Local command handler (time, date, what's playing, stop, open/close app)
    const handleLocalCommand = React.useCallback(async (cmd) => {
        // Stop TTS
        if (cmd === 'stop') {
            stopSpeaking();
            setResponseMessage?.('');
            return;
        }

        // Current time
        if (cmd === 'time') {
            const now = new Date();
            const h = now.getHours() % 12 || 12;
            const m = String(now.getMinutes()).padStart(2, '0');
            const ampm = now.getHours() >= 12 ? 'PM' : 'AM';
            const msg = `It's ${h}:${m} ${ampm}.`;
            setResponseMessage?.(msg);
            try { await speak(msg); } catch (_) {}
            setTimeout(() => setResponseMessage?.(''), 5000);
            return;
        }

        // Current date
        if (cmd === 'date') {
            const now = new Date();
            const day = now.toLocaleDateString('en-US', { weekday: 'long' });
            const month = now.toLocaleDateString('en-US', { month: 'long' });
            const date = now.getDate();
            const msg = `Today is ${day}, ${month} ${date}.`;
            setResponseMessage?.(msg);
            try { await speak(msg); } catch (_) {}
            setTimeout(() => setResponseMessage?.(''), 5000);
            return;
        }

        // What's playing on Spotify
        if (cmd === 'what_playing') {
            try {
                const res = await fetch('http://127.0.0.1:8000/api/spotify/current-track');
                const data = await res.json();
                if (data.title) {
                    const msg = `Now playing: ${data.title} by ${data.artist}.`;
                    setResponseMessage?.(msg);
                    try { await speak(msg); } catch (_) {}
                } else {
                    const msg = 'Nothing is playing on Spotify right now.';
                    setResponseMessage?.(msg);
                    try { await speak(msg); } catch (_) {}
                }
                setTimeout(() => setResponseMessage?.(''), 5000);
            } catch (_) {
                setResponseMessage?.('Could not check Spotify.');
                setTimeout(() => setResponseMessage?.(''), 3000);
            }
            return;
        }

        // Open app
        if (cmd && typeof cmd === 'object' && cmd.type === 'open_app') {
            const appName = cmd.app;
            try {
                await fetch('http://127.0.0.1:8000/api/open-app', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ app: appName }),
                });
                const msg = `Opening ${appName}.`;
                setResponseMessage?.(msg);
                try { await speak(msg); } catch (_) {}
                setTimeout(() => setResponseMessage?.(''), 3000);
            } catch (_) {
                setResponseMessage?.(`Failed to open ${appName}.`);
                setTimeout(() => setResponseMessage?.(''), 3000);
            }
            return;
        }

        // Close app
        if (cmd && typeof cmd === 'object' && cmd.type === 'close_app') {
            const appName = cmd.app;
            try {
                await fetch('http://127.0.0.1:8000/api/close-app', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ app: appName }),
                });
                const msg = `Closing ${appName}.`;
                setResponseMessage?.(msg);
                try { await speak(msg); } catch (_) {}
                setTimeout(() => setResponseMessage?.(''), 3000);
            } catch (_) {
                setResponseMessage?.(`Failed to close ${appName}.`);
                setTimeout(() => setResponseMessage?.(''), 3000);
            }
            return;
        }

        // Workspace commands
        if (cmd === 'trading') setWorkspace?.('trading');
        else if (cmd === 'dashboard') setWorkspace?.('dashboard');
        else if (cmd === 'lock') lockNow?.();
    }, [setResponseMessage, setWorkspace, lockNow]);

    // Handle fingerprint unlock
    const [fingerprintState, setFingerprintState] = useState('idle');
    const [fingerprintError, setFingerprintError] = useState('');

    const handleFingerprintClick = async () => {
        setFingerprintState('pending');
        setFingerprintError('');
        try {
            const result = await unlockWithFingerprintFlow();
            if (result.ok) {
                setFingerprintState('success');
            } else {
                setFingerprintState('error');
                setFingerprintError(result.error || result.reason || 'Failed');
            }
        } catch (err) {
            setFingerprintState('error');
            setFingerprintError('exception');
        }
    };

    useSpeech({
        locked,
        workspace,
        enabled: micEnabled,
        onCommand: handleLocalCommand,
        onConversation: handleConversation,
        enabled: micEnabled,
        locked: locked,
    });

    return (
        <div className="w-screen h-screen relative overflow-hidden select-none bg-[#02030A]">
            <Background />

            <div
                className="absolute inset-0 px-10 py-6 flex flex-col justify-between"
                style={{ zIndex: 20, pointerEvents: 'none', transform: `scale(${scale})`, transformOrigin: 'center center' }}
            >
                <div className="flex items-center justify-between">
                    <div className="font-orbitron text-[8px] tracking-[0.45em] text-[#00B7FF]/45 uppercase flex items-center gap-3">
                        <span className="inline-block w-6 h-px bg-[#00B7FF]/40" />
                        STARK INDUSTRIES
                    </div>

                    <div className="text-right">
                        <Clock />
                    </div>
                </div>

                <div className="relative flex flex-col items-center" style={{ transform: 'translateY(-140px)' }}>
                    <motion.div
                        className="text-center"
                        initial={{ opacity: 0, y: -16 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 1, ease: 'easeOut' }}
                    >
                        <h1 className="font-orbitron text-[3.4rem] tracking-[0.8em] text-[#DFFAFF] font-light" style={{ textShadow: '0 0 26px rgba(0,183,255,0.24)' }}>
                            F.R.I.D.A.Y.
                        </h1>
                        <p className="font-grotesk text-[10px] tracking-[0.35em] text-[#00B7FF]/45 mt-2 uppercase">
                            PERSONAL AI ASSISTANT
                        </p>
                        <div className="mx-auto mt-4 h-px w-28 bg-gradient-to-r from-transparent via-[#00B7FF]/80 to-transparent" />
                    </motion.div>

                    <div className="mt-7 text-center">
                        <AnimatePresence mode="wait">
                            {authStep ? (
                                <motion.div
                                    key={authStep.id}
                                    initial={{ opacity: 0, y: 8 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -8 }}
                                    className="flex flex-col items-center gap-2"
                                >
                                    <span className="font-orbitron text-[10px] tracking-[0.4em] text-[#00D9FF] uppercase drop-shadow-[0_0_8px_#00D9FF]">
                                        {authStep.label}
                                    </span>
                                    <div className="h-px w-24 bg-[#00B7FF]/30" />
                                </motion.div>
                            ) : locked ? (
                                <motion.div
                                    key="locked"
                                    initial={{ opacity: 0, y: 8 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="flex flex-col items-center gap-2"
                                >
                                    <h2 className="font-orbitron text-[1.2rem] tracking-[0.5em] text-[#00B7FF] font-light" style={{ textShadow: '0 0 16px rgba(0,183,255,0.35)' }}>
                                        LOCKED
                                    </h2>
                                    <p className="font-grotesk text-[9px] text-[#DFFAFF]/35 tracking-[0.35em] uppercase">
                                        AWAITING FINGERPRINT VERIFICATION
                                    </p>
                                </motion.div>
                            ) : (
                                <motion.div
                                    key="ambient"
                                    initial={{ opacity: 0, y: 8 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="flex flex-col items-center gap-2"
                                >
                                    <h2 className="font-orbitron text-[1.2rem] tracking-[0.5em] text-[#FF8C00] font-light" style={{ textShadow: '0 0 16px rgba(255,140,0,0.45)' }}>
                                        LISTENING...
                                    </h2>
                                    <p className="font-grotesk text-[9px] text-[#DFFAFF]/35 tracking-[0.35em] uppercase">
                                        VOICE ACTIVE · SPEAK FREELY
                                    </p>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        {responseMessage && (
                            <div className="mt-3 text-[11px] text-[#DFFAFF] font-grotesk tracking-[0.08em] uppercase drop-shadow-[0_0_6px_#00D9FF]">
                                {responseMessage}
                            </div>
                        )}

                        {ttsLoading ? (
                            <div className="mt-3 text-[11px] text-[#DFFAFF] font-grotesk tracking-[0.08em] uppercase drop-shadow-[0_0_6px_#00D9FF]">
                                Generating voice...
                            </div>
                        ) : isSpeaking ? (
                            <div className="mt-3 text-[11px] text-[#00D9FF] font-grotesk tracking-[0.08em] uppercase drop-shadow-[0_0_6px_#00D9FF]">
                                Speaking...
                            </div>
                        ) : null}

                        <div className="mt-3 flex items-center justify-center gap-3">
                            {!audioEnabled ? (
                                <button
                                    onClick={() => enableAudioFromGesture({ speakConfirmation: true })}
                                    className="px-4 py-2 rounded bg-[#00B7FF] text-[#001018] text-[11px] uppercase font-bold"
                                    style={{ pointerEvents: 'auto' }}
                                >
                                    Enable Voice
                                </button>
                            ) : (
                                <span className="text-[11px] text-[#DFFAFF]/80 uppercase tracking-[0.2em]">
                                    Voice enabled
                                </span>
                            )}
                        </div>
                    </div>
                </div>

                {locked ? (
                    <div className="relative flex items-center justify-between w-full max-w-[1220px] mx-auto mt-14" style={{ pointerEvents: 'auto' }}>
                        <motion.div
                            initial={{ opacity: 0, x: -28 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.2, duration: 0.9, ease: 'easeOut' }}
                        >
                            <AccessCard
                                onFingerprint={handleFingerprintClick}
                                fingerprintState={fingerprintState}
                                fingerprintError={fingerprintError}
                            />
                        </motion.div>

                        <div className="w-16" />

                        <motion.div
                            initial={{ opacity: 0, x: 28 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.2, duration: 0.9, ease: 'easeOut' }}
                        >
                            <StatusCard />
                        </motion.div>
                    </div>
                ) : (
                    <div className="mt-14" />
                )}

                <motion.div
                    className="flex justify-center pb-6"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5, duration: 0.9 }}
                    style={{ pointerEvents: 'auto' }}
                >
                    <BottomBar />
                </motion.div>
            </div>

            <div className="absolute inset-0 flex items-center justify-center pointer-events-none" style={{ zIndex: 10 }}>
                <HudOrb size={340} />
            </div>



            {!audioEnabled ? (
                <div className="absolute inset-0 z-50 flex items-center justify-center bg-[#02030A]/95 px-6 py-10" style={{ pointerEvents: 'auto' }}>
                    <div className="max-w-2xl w-full rounded-[2rem] border border-[#00B7FF]/30 bg-[#001018]/95 p-10 text-center shadow-[0_0_80px_rgba(0,183,255,0.20)]">
                        <div className="font-orbitron text-[9px] tracking-[0.45em] text-[#00B7FF]/45 uppercase mb-4">
                            VOICE ENGINE OFFLINE
                        </div>
                        <h2 className="font-orbitron text-[2rem] tracking-[0.5em] text-[#DFFAFF] uppercase mb-4">
                            F.R.I.D.A.Y.
                        </h2>
                        <p className="font-grotesk text-sm text-[#DFFAFF]/80 leading-6 mb-8">
                            Voice output requires permission. Click Enable Voice to initialize the speech engine and bring audio online.
                        </p>
                        <button
                            onClick={() => enableAudioFromGesture({ speakConfirmation: true })}
                            className="inline-flex items-center justify-center rounded-full bg-[#00B7FF] px-8 py-3 text-[11px] font-bold uppercase tracking-[0.35em] text-[#001018] transition hover:bg-[#00d1ff]"
                        >
                            Enable Voice
                        </button>
                    </div>
                </div>
            ) : null}

            <div className="absolute inset-0 pointer-events-none" style={{ zIndex: 30 }}>
                <Corners />
            </div>
        </div>
    );
}
