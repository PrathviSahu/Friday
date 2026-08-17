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
import { API_ENDPOINTS } from '../../api/config.js';
import { approveAndSendEmail, cancelEmailDraft } from '../../api/email';
import { approveAndCreateEvent, cancelEventDraft } from '../../api/calendar';
import { approveAndSendWhatsApp, cancelWhatsAppDraft } from '../../api/whatsapp';
import PendingApprovalCard from '../Common/PendingApprovalCard';

export default function LockScreen() {
    const orb = useOrbState();
    const { appState, stateLabel, authStep, responseMessage, audioEnabled, enableAudioFromGesture, ttsLoading, isSpeaking, locked, unlockWithFingerprintFlow, authenticateWithPassword, unlockDemo, setResponseMessage, workspace, setWorkspace, lockNow } = orb;
    const { micEnabled, pttMode } = useFriday();
    const scale = useFitScale();

    // Approval-first email flow: holds the pending draft + preview shown to
    // the user until they explicitly confirm ("yes") or cancel ("no").
    const [pendingEmail, setPendingEmail] = React.useState(null);
    const pendingEmailRef = React.useRef(null);
    React.useEffect(() => { pendingEmailRef.current = pendingEmail; }, [pendingEmail]);

    const [pendingCalendar, setPendingCalendar] = React.useState(null);
    const pendingCalendarRef = React.useRef(null);
    React.useEffect(() => { pendingCalendarRef.current = pendingCalendar; }, [pendingCalendar]);

    const [pendingWhatsApp, setPendingWhatsApp] = React.useState(null);
    const pendingWhatsAppRef = React.useRef(null);
    React.useEffect(() => { pendingWhatsAppRef.current = pendingWhatsApp; }, [pendingWhatsApp]);

    // Push-to-talk HUD: shows a live "speaking" state while Space is held.
    const [pttHeld, setPttHeld] = React.useState(false);
    React.useEffect(() => {
        const onPtt = (e) => setPttHeld(Boolean(e.detail?.held));
        window.addEventListener('friday-ptt', onPtt);
        return () => window.removeEventListener('friday-ptt', onPtt);
    }, []);

    // FRIDAY's conversation loop: show text on screen when speech is returned.
    const handleConversation = React.useCallback(({
        reply,
        action,
        email_draft_id,
        email_preview,
        calendar_draft_id,
        calendar_preview,
        whatsapp_draft_id,
        whatsapp_preview
    }) => {
        if (reply) {
            setResponseMessage?.(reply);
            setTimeout(() => {
                setResponseMessage?.((curr) => (curr === reply ? '' : curr));
            }, 4500);
        }
        if (action === 'email_confirm' && email_draft_id) {
            // Approval-first email flow: show the preview, wait for explicit confirm.
            setPendingEmail({ draftId: email_draft_id, preview: email_preview || {} });
            return;
        }
        if (action === 'calendar_confirm' && calendar_draft_id) {
            setPendingCalendar({ draftId: calendar_draft_id, preview: calendar_preview || {} });
            return;
        }
        if (action === 'whatsapp_confirm' && whatsapp_draft_id) {
            setPendingWhatsApp({ draftId: whatsapp_draft_id, preview: whatsapp_preview || {} });
            return;
        }
        if (action && action !== 'none' && !locked) {
            if (action === 'trading')   setWorkspace?.('trading');
            else if (action === 'dashboard') setWorkspace?.('dashboard');
            else if (action === 'career')    setWorkspace?.('career');
            else if (action === 'lock' || action === 'lock_screen') lockNow?.();
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
                const res = await fetch(`${API_ENDPOINTS.spotify}/current-track`);
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
                await fetch(API_ENDPOINTS.openApp, {
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
                await fetch(API_ENDPOINTS.closeApp, {
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

        // Workspace / app commands
        if (cmd === 'trading') setWorkspace?.('trading');
        else if (cmd === 'dashboard' || cmd === 'unlocked') setWorkspace?.('unlocked');
        else if (cmd === 'engineering' || cmd === 'vscode') {
            // "engineering console" / "open vscode" → launch VS Code
            fetch(API_ENDPOINTS.openApp, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ app: 'Visual Studio Code' }),
            }).catch(() => {});
            const msg = 'Opening Visual Studio Code, Boss.';
            setResponseMessage?.(msg);
            try { await speak(msg); } catch (_) {}
            setTimeout(() => setResponseMessage?.(''), 3000);
        }
        else if (cmd === 'browser') {
            // "open browser" → launch Brave (falls back to default browser)
            fetch(API_ENDPOINTS.openApp, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ app: 'Brave Browser' }),
            }).catch(() => {});
            const msg = 'Opening the browser, Boss.';
            setResponseMessage?.(msg);
            try { await speak(msg); } catch (_) {}
            setTimeout(() => setResponseMessage?.(''), 3000);
        }
        else if (cmd === 'lock' || cmd === 'lock_screen') lockNow?.();
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
        } catch (_err) {
            setFingerprintState('error');
            setFingerprintError('exception');
        }
    };

    // ── Email approval helpers (voice + UI) ──────────────────────────────
    const sendPendingEmail = React.useCallback(async () => {
        const pending = pendingEmailRef.current;
        if (!pending) return false;
        try {
            await approveAndSendEmail(pending.draftId);
            setResponseMessage?.('Email sent.');
        } catch (err) {
            setResponseMessage?.(`Email failed: ${err.message || 'unknown error'}`);
        } finally {
            pendingEmailRef.current = null;
            setPendingEmail(null);
        }
        return true;
    }, [setResponseMessage]);

    const cancelPendingEmail = React.useCallback(async () => {
        const pending = pendingEmailRef.current;
        if (!pending) return false;
        await cancelEmailDraft(pending.draftId).catch(() => {});
        pendingEmailRef.current = null;
        setPendingEmail(null);
        setResponseMessage?.('Email cancelled.');
        return true;
    }, [setResponseMessage]);

    // ── Calendar approval helpers ────────────────────────────────────────
    const createPendingCalendar = React.useCallback(async () => {
        const pending = pendingCalendarRef.current;
        if (!pending) return false;
        try {
            await approveAndCreateEvent(pending.draftId);
            setResponseMessage?.('Event created on your calendar.');
        } catch (err) {
            setResponseMessage?.(`Calendar failed: ${err.message || 'unknown error'}`);
        } finally {
            pendingCalendarRef.current = null;
            setPendingCalendar(null);
        }
        return true;
    }, [setResponseMessage]);

    const cancelPendingCalendar = React.useCallback(async () => {
        const pending = pendingCalendarRef.current;
        if (!pending) return false;
        await cancelEventDraft(pending.draftId).catch(() => {});
        pendingCalendarRef.current = null;
        setPendingCalendar(null);
        setResponseMessage?.('Event cancelled.');
        return true;
    }, [setResponseMessage]);

    // ── WhatsApp approval helpers ────────────────────────────────────────
    const sendPendingWhatsApp = React.useCallback(async () => {
        const pending = pendingWhatsAppRef.current;
        if (!pending) return false;
        try {
            await approveAndSendWhatsApp(pending.draftId);
            setResponseMessage?.('WhatsApp message sent.');
        } catch (err) {
            setResponseMessage?.(`WhatsApp failed: ${err.message || 'unknown error'}`);
        } finally {
            pendingWhatsAppRef.current = null;
            setPendingWhatsApp(null);
        }
        return true;
    }, [setResponseMessage]);

    const cancelPendingWhatsApp = React.useCallback(async () => {
        const pending = pendingWhatsAppRef.current;
        if (!pending) return false;
        await cancelWhatsAppDraft(pending.draftId).catch(() => {});
        pendingWhatsAppRef.current = null;
        setPendingWhatsApp(null);
        setResponseMessage?.('Message cancelled.');
        return true;
    }, [setResponseMessage]);

    // Voice confirmation for any pending approval (email → calendar →
    // WhatsApp): "yes / send it / create it" → confirm; "no / cancel" → discard.
    React.useEffect(() => {
        window.fridayCheckPendingApproval = async (transcript) => {
            const t = (transcript || '').trim().toLowerCase();
            const YES = /^(yes|yeah|yep|yup|sure|ok|okay|confirm|send|send it|send it now|create|create it|go ahead|do it|haan|ha)$/i;
            const NO = /^(no|nope|nah|cancel|cancel it|never mind|don'?t send|don'?t create|skip|mat bhejo)$/i;

            if (pendingEmailRef.current) {
                if (YES.test(t)) { await sendPendingEmail(); return true; }
                if (NO.test(t)) { await cancelPendingEmail(); return true; }
                return false; // pending approval exists — don't route elsewhere
            }
            if (pendingCalendarRef.current) {
                if (YES.test(t)) { await createPendingCalendar(); return true; }
                if (NO.test(t)) { await cancelPendingCalendar(); return true; }
                return false;
            }
            if (pendingWhatsAppRef.current) {
                if (YES.test(t)) { await sendPendingWhatsApp(); return true; }
                if (NO.test(t)) { await cancelPendingWhatsApp(); return true; }
                return false;
            }
            return false;
        };
        return () => { delete window.fridayCheckPendingApproval; };
    }, [sendPendingEmail, cancelPendingEmail, createPendingCalendar, cancelPendingCalendar,
        sendPendingWhatsApp, cancelPendingWhatsApp]);

    useSpeech({
        locked,
        workspace,
        enabled: micEnabled,
        mode: pttMode ? 'ptt' : 'always',
        onCommand: handleLocalCommand,
        onConversation: handleConversation,
        onStateChange: (state) => orb.transitionTo?.(state),
    });

    return (
        <div className="w-screen h-screen relative overflow-hidden select-none bg-[#02030A]">
            <Background />

            <div
                className="absolute inset-0 px-8 py-4 flex flex-col justify-between items-center"
                style={{ zIndex: 20, pointerEvents: 'none', transform: `scale(${scale})`, transformOrigin: 'top center' }}
            >
                <div className="flex items-center justify-between w-full">
                    <div className="font-orbitron text-[8px] tracking-[0.45em] text-[#00B7FF]/45 uppercase flex items-center gap-3">
                        <span className="inline-block w-6 h-px bg-[#00B7FF]/40" />
                        STARK INDUSTRIES
                    </div>

                    <div className="text-right">
                        <Clock />
                    </div>
                </div>

                <div className="relative flex flex-col items-center mt-1" style={{ transform: 'translateY(-20px)' }}>
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
                            {appState === 'BOOTING' ? (
                                <motion.div
                                    key="booting"
                                    initial={{ opacity: 0, scale: 0.95 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={{ opacity: 0 }}
                                    className="flex flex-col items-center gap-3"
                                >
                                    <div className="relative w-8 h-8">
                                        <motion.div
                                            animate={{ rotate: 360 }}
                                            transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                                            className="absolute inset-0 rounded-full border-2 border-t-[#00D9FF] border-r-transparent border-b-[#00B7FF]/20 border-l-transparent shadow-[0_0_12px_rgba(0,183,255,0.4)]"
                                        />
                                        <motion.div
                                            animate={{ rotate: -360 }}
                                            transition={{ duration: 2.2, repeat: Infinity, ease: "linear" }}
                                            className="absolute inset-1 rounded-full border border-t-[#22ff99]/20 border-r-transparent border-b-[#22ff99] border-l-transparent"
                                        />
                                    </div>
                                    <h2 className="font-orbitron text-[1rem] tracking-[0.4em] text-[#00D9FF] uppercase drop-shadow-[0_0_8px_rgba(0,183,255,0.6)]">
                                        {stateLabel}
                                    </h2>
                                    <p className="font-grotesk text-[8px] text-[#DFFAFF]/30 tracking-[0.3em] uppercase animate-pulse">
                                        POWERING COGNITIVE CORES
                                    </p>
                                </motion.div>
                            ) : authStep ? (
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

                        {pttMode ? (
                            pttHeld ? (
                                <div className="mt-3 text-[11px] font-orbitron text-[#22ff99] tracking-[0.4em] uppercase drop-shadow-[0_0_10px_rgba(34,255,153,0.6)]">
                                    🎙 SPEAKING — RELEASE TO SEND
                                </div>
                            ) : (
                                <div className="mt-3 text-[10px] font-orbitron text-[#00B7FF]/70 tracking-[0.35em] uppercase animate-pulse">
                                    HOLD SPACE TO TALK
                                </div>
                            )
                        ) : (
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
                        )}
                    </div>
                </div>

                {locked ? (
                    <div className="relative flex flex-col md:flex-row items-center justify-center md:justify-between w-full max-w-[1280px] mx-auto mt-2 px-4 gap-6" style={{ pointerEvents: 'auto' }}>
                        <motion.div
                            initial={{ opacity: 0, x: -28 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.2, duration: 0.9, ease: 'easeOut' }}
                            className="w-full md:w-auto flex justify-center"
                        >
                            <AccessCard
                                onFingerprint={handleFingerprintClick}
                                fingerprintState={fingerprintState}
                                fingerprintError={fingerprintError}
                                onPasswordUnlock={authenticateWithPassword}
                                onDemoUnlock={unlockDemo}
                            />
                        </motion.div>

                        <div className="hidden md:block w-16" />

                        <motion.div
                            initial={{ opacity: 0, x: 28 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.2, duration: 0.9, ease: 'easeOut' }}
                            className="w-full md:w-auto flex justify-center"
                        >
                            <StatusCard />
                        </motion.div>
                    </div>
                ) : (
                    <div className="mt-2" />
                )}

                <motion.div
                    className="flex justify-center pb-2"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5, duration: 0.9 }}
                    style={{ pointerEvents: 'auto' }}
                >
                    <BottomBar />
                </motion.div>
            </div>

            <div className="absolute inset-0 flex items-center justify-center pointer-events-none" style={{ zIndex: 10, transform: `scale(${scale})`, transformOrigin: 'top center' }}>
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

            {/* ── Pending approval cards (approval-first: email + calendar) ── */}
            {pendingEmail && (
                <PendingApprovalCard
                    title="✉ Email Approval Required"
                    rows={[
                        { label: 'To', value: pendingEmail.preview?.to || '—' },
                        { label: 'Subject', value: pendingEmail.preview?.subject || '(none)' },
                    ]}
                    body={pendingEmail.preview?.body || '—'}
                    hint='Say "yes" to send · "no" to cancel'
                    confirmLabel="Send"
                    onConfirm={sendPendingEmail}
                    onCancel={cancelPendingEmail}
                />
            )}
            {pendingWhatsApp && (
                <PendingApprovalCard
                    title="💬 WhatsApp Approval Required"
                    rows={[
                        { label: 'To', value: `+${pendingWhatsApp.preview?.phone || '—'}` },
                    ]}
                    body={pendingWhatsApp.preview?.message || '—'}
                    hint='Say "yes" to send · "no" to cancel'
                    confirmLabel="Send"
                    onConfirm={sendPendingWhatsApp}
                    onCancel={cancelPendingWhatsApp}
                />
            )}
            {pendingCalendar && (
                <PendingApprovalCard
                    title="📅 Calendar Approval Required"
                    rows={[
                        { label: 'Event', value: pendingCalendar.preview?.summary || '—' },
                        {
                            label: 'When',
                            value: pendingCalendar.preview?.start
                                ? `${new Date(pendingCalendar.preview.start).toLocaleString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit', hour12: true })} → ${new Date(pendingCalendar.preview.end).toLocaleString('en-IN', { hour: 'numeric', minute: '2-digit', hour12: true })}`
                                : '—',
                        },
                    ]}
                    body={pendingCalendar.preview?.description || ''}
                    hint='Say "yes" to create · "no" to cancel'
                    confirmLabel="Create"
                    onConfirm={createPendingCalendar}
                    onCancel={cancelPendingCalendar}
                />
            )}

            <div className="absolute inset-0 pointer-events-none" style={{ zIndex: 30 }}>
                <Corners />
            </div>
        </div>
    );
}
