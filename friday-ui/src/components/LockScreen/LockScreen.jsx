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
import { approveAndSendWhatsApp, cancelWhatsAppDraft, approveAndSendWhatsAppDesktop } from '../../api/whatsapp';
import PendingApprovalCard from '../Common/PendingApprovalCard';

export default function LockScreen() {
    const orb = useOrbState();
    const { appState, stateLabel, authStep, responseMessage, audioEnabled, enableAudioFromGesture, ttsLoading, isSpeaking, locked, unlockWithFingerprintFlow, setResponseMessage, workspace, setWorkspace, lockNow } = orb;
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

    const [pendingWhatsAppDesktop, setPendingWhatsAppDesktop] = React.useState(null);
    const pendingWhatsAppDesktopRef = React.useRef(null);
    React.useEffect(() => { pendingWhatsAppDesktopRef.current = pendingWhatsAppDesktop; }, [pendingWhatsAppDesktop]);

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
        whatsapp_preview,
        whatsapp_desktop_preview,
    }) => {
        if (reply) {
            setResponseMessage?.(reply);
        }
        if (action === 'email_confirm' && email_draft_id) {
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
        if (action === 'whatsapp_desktop_confirm' && whatsapp_desktop_preview) {
            setPendingWhatsAppDesktop({ preview: whatsapp_desktop_preview });
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

    // ── WhatsApp Desktop approval helpers ──────────────────────────────
    const sendPendingWhatsAppDesktop = React.useCallback(async () => {
        const pending = pendingWhatsAppDesktopRef.current;
        if (!pending) return false;
        try {
            await approveAndSendWhatsAppDesktop(pending.preview);
            setResponseMessage?.('Opening WhatsApp Desktop to send your message...');
        } catch (err) {
            setResponseMessage?.(`WhatsApp Desktop failed: ${err.message || 'unknown error'}`);
        } finally {
            pendingWhatsAppDesktopRef.current = null;
            setPendingWhatsAppDesktop(null);
        }
        return true;
    }, [setResponseMessage]);

    const cancelPendingWhatsAppDesktop = React.useCallback(async () => {
        pendingWhatsAppDesktopRef.current = null;
        setPendingWhatsAppDesktop(null);
        setResponseMessage?.('Message cancelled.');
        return true;
    }, [setResponseMessage]);

    // Voice confirmation for any pending approval (email → calendar →
    // WhatsApp → WhatsApp Desktop): "yes / send it / create it" → confirm; "no / cancel" → discard.
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
            if (pendingWhatsAppDesktopRef.current) {
                if (YES.test(t)) { await sendPendingWhatsAppDesktop(); return true; }
                if (NO.test(t)) { await cancelPendingWhatsAppDesktop(); return true; }
                return false;
            }
            return false;
        };
        return () => { delete window.fridayCheckPendingApproval; };
    }, [sendPendingEmail, cancelPendingEmail, createPendingCalendar, cancelPendingCalendar,
        sendPendingWhatsApp, cancelPendingWhatsApp, sendPendingWhatsAppDesktop, cancelPendingWhatsAppDesktop]);

    useSpeech({
        locked,
        workspace,
        enabled: micEnabled,
        mode: pttMode ? 'ptt' : 'always',
        onCommand: handleLocalCommand,
        onConversation: handleConversation,
    });

    return (
        <div className="w-screen h-screen relative overflow-hidden select-none bg-[#0f172a]">
            <Background />

            <div
                className="absolute inset-0 px-10 py-6 flex flex-col justify-between"
                style={{ zIndex: 20, pointerEvents: 'none', transform: `scale(${scale})`, transformOrigin: 'center center' }}
            >
                <div className="flex items-center justify-between">
                    <div className="font-sans text-[8px] tracking-[0.45em] text-slate-400/60 uppercase flex items-center gap-3">
                        <span className="inline-block w-6 h-px bg-slate-400/30" />
                        F.R.I.D.A.Y. v4
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
                        <h1 className="font-sans text-[3.4rem] tracking-[0.6em] text-slate-100 font-light">
                            F.R.I.D.A.Y.
                        </h1>
                        <p className="font-sans text-[10px] tracking-[0.35em] text-slate-400/70 mt-2 uppercase">
                            Personal AI Assistant
                        </p>
                        <div className="mx-auto mt-4 h-px w-28 bg-gradient-to-r from-transparent via-slate-500/40 to-transparent" />
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
                                            className="absolute inset-0 rounded-full border-2 border-t-[#3b82f6] border-r-transparent border-b-[#60a5fa]/20 border-l-transparent "
                                        />
                                        <motion.div
                                            animate={{ rotate: -360 }}
                                            transition={{ duration: 2.2, repeat: Infinity, ease: "linear" }}
                                            className="absolute inset-1 rounded-full border border-t-[#22ff99]/20 border-r-transparent border-b-[#22ff99] border-l-transparent"
                                        />
                                    </div>
                                    <h2 className="font-sans text-[1rem] tracking-[0.3em] text-blue-400 uppercase">
                                        {stateLabel}
                                    </h2>
                                    <p className="font-sans text-[8px] text-slate-400/40 tracking-[0.3em] uppercase animate-pulse">
                                        Loading...
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
                                    <span className="font-sans text-[10px] tracking-[0.4em] text-blue-400 uppercase">
                                        {authStep.label}
                                    </span>
                                    <div className="h-px w-24 bg-slate-500/20" />
                                </motion.div>
                            ) : locked ? (
                                <motion.div
                                    key="locked"
                                    initial={{ opacity: 0, y: 8 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="flex flex-col items-center gap-2"
                                >
                                    <h2 className="font-sans text-[1.2rem] tracking-[0.5em] text-slate-300 font-light">
                                        LOCKED
                                    </h2>
                                    <p className="font-sans text-[9px] text-slate-400/50 tracking-[0.35em] uppercase">
                                        Awaiting Verification
                                    </p>
                                </motion.div>
                            ) : (
                                <motion.div
                                    key="ambient"
                                    initial={{ opacity: 0, y: 8 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="flex flex-col items-center gap-2"
                                >
                                    <h2 className="font-sans text-[1.2rem] tracking-[0.4em] text-orange-400 font-light">
                                        Listening...
                                    </h2>
                                    <p className="font-sans text-[9px] text-slate-400/50 tracking-[0.35em] uppercase">
                                        Voice Active
                                    </p>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        {responseMessage && (
                            <div className="mt-3 text-[11px] text-slate-200 font-sans tracking-[0.04em]">
                                {responseMessage}
                            </div>
                        )}

                        {ttsLoading ? (
                            <div className="mt-3 text-[11px] text-slate-300 font-sans tracking-[0.04em]">
                                Generating voice...
                            </div>
                        ) : isSpeaking ? (
                            <div className="mt-3 text-[11px] text-blue-400 font-sans tracking-[0.04em]">
                                Speaking...
                            </div>
                        ) : null}

                        {pttMode ? (
                            pttHeld ? (
                                <div className="mt-3 text-[11px] font-sans text-green-400 tracking-[0.3em] uppercase">
                                    🎙 Speaking — Release to Send
                                </div>
                            ) : (
                                <div className="mt-3 text-[10px] font-sans text-slate-400/70 tracking-[0.3em] uppercase animate-pulse">
                                    Hold Space to Talk
                                </div>
                            )
                        ) : (
                            <div className="mt-3 flex items-center justify-center gap-3">
                                {!audioEnabled ? (
                                    <button
                                        onClick={() => enableAudioFromGesture({ speakConfirmation: true })}
                                        className="px-4 py-2 rounded bg-[#60a5fa] text-[#1e293b] text-[11px] uppercase font-bold"
                                        style={{ pointerEvents: 'auto' }}
                                    >
                                        Enable Voice
                                    </button>
                                ) : (
                                    <span className="text-[11px] text-[#f1f5f9]/80 uppercase tracking-[0.2em]">
                                        Voice enabled
                                    </span>
                                )}
                            </div>
                        )}
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
                                onPasswordUnlock={authenticateWithPassword}
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
                <div className="absolute inset-0 z-50 flex items-center justify-center bg-[#0f172a]/95 px-6 py-10" style={{ pointerEvents: 'auto' }}>
                    <div className="max-w-2xl w-full rounded-2xl border border-slate-600/30 bg-slate-900/95 p-10 text-center">
                        <div className="font-sans text-[9px] tracking-[0.45em] text-slate-400/60 uppercase mb-4">
                            Voice Engine Offline
                        </div>
                        <h2 className="font-sans text-[2rem] tracking-[0.5em] text-slate-100 uppercase mb-4">
                            F.R.I.D.A.Y.
                        </h2>
                        <p className="font-sans text-sm text-slate-300/80 leading-6 mb-8">
                            Voice output requires permission. Click Enable Voice to initialize the speech engine and bring audio online.
                        </p>
                        <button
                            onClick={() => enableAudioFromGesture({ speakConfirmation: true })}
                            className="inline-flex items-center justify-center rounded-full bg-blue-500 px-8 py-3 text-[11px] font-bold uppercase tracking-[0.35em] text-white transition hover:bg-blue-400"
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
            {pendingWhatsAppDesktop && (
                <PendingApprovalCard
                    title="💬 WhatsApp Desktop — Send Message"
                    rows={[
                        { label: 'To', value: `+${pendingWhatsAppDesktop.preview?.phone || '—'}` },
                    ]}
                    body={pendingWhatsAppDesktop.preview?.message || '—'}
                    hint='Say "yes" to send via WhatsApp Desktop · "no" to cancel'
                    confirmLabel="Send via WhatsApp"
                    onConfirm={sendPendingWhatsAppDesktop}
                    onCancel={cancelPendingWhatsAppDesktop}
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
