import React, { useState, useCallback, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Background from '../Background/Background';
import StatusCard from '../StatusPanel/StatusCard';
import BottomBar from '../Panels/BottomBar';
import Corners from '../Animations/Corners';
import HudOrb from '../AICore/HudOrb';
import { useOrbState } from '../../hooks/useOrbState';
import { useSpeech } from '../../hooks/useSpeech';
import { useFriday } from '../../context/FridayContext';
import { vault } from '../../services/secureVault';

const DEV_PASSWORD = 'friday';
const IS_DEV = typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.DEV;

export default function LockScreen() {
    const {
        authStep,
        runAuthSequence,
        responseMessage,
        appState,
        audioEnabled,
        enableAudioFromGesture,
        ttsLoading,
        isSpeaking,
        locked,
        mode,
        setMode,
        adminAuthed,
        unlockWithFingerprintFlow,
        authenticateWithPassword,
        lockNow,
    } = useOrbState();
    const { micEnabled } = useFriday();

    const [fpState, setFpState] = useState('idle');
    const [fpError, setFpError] = useState('');
    const [password, setPassword] = useState('');
    const [pwError, setPwError] = useState('');
    const [pwBusy, setPwBusy] = useState(false);
    const [resetMsg, setResetMsg] = useState('');
    const [showAdminCard, setShowAdminCard] = useState(false);
    const [cardPosition, setCardPosition] = useState({ x: 0, y: 0 });
    const [isDragging, setIsDragging] = useState(false);
    const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

    const handleCommand = useCallback((cmd) => {
        if (locked && cmd !== 'wake') return;
        if (!locked && cmd === 'lock') { lockNow(); return; }
        runAuthSequence(cmd);
    }, [locked, lockNow, runAuthSequence]);

    const onSubmitPassword = useCallback(async (e) => {
        e?.preventDefault?.();
        setPwError('');
        setResetMsg('');
        setPwBusy(true);
        const res = await authenticateWithPassword(password);
        setPwBusy(false);
        if (res?.ok) {
            setPassword('');
        } else {
            setPwError(
                res?.reason === 'empty' ? 'Enter a password'
                    : res?.reason === 'crypto' ? 'Crypto unavailable — open at http://localhost'
                        : 'Incorrect password',
            );
        }
    }, [authenticateWithPassword, password]);

    const onReset = useCallback(() => {
        try { vault.reset(); } catch { /* ignore */ }
        setPassword('');
        setPwError('');
        setFpState('idle');
        setFpError('');
        setResetMsg('Access reset. Type a new password to set it.');
    }, []);

    const onFingerprint = useCallback(async () => {
        setFpState('pending');
        setFpError('');
        const res = await unlockWithFingerprintFlow();
        if (!res || !res.ok) {
            setFpState('error');
            setFpError(
                res?.reason === 'cancelled' ? 'Cancelled'
                    : res?.reason === 'use-localhost' ? 'Open at http://localhost'
                        : res?.reason === 'insecure' ? 'Insecure context'
                            : res?.reason === 'unsupported' ? 'Not supported here'
                                : 'Unavailable',
            );
        }
    }, [unlockWithFingerprintFlow]);

    const closeAdminCard = useCallback(() => {
        setShowAdminCard(false);
        // Reset position when closing? keep last position maybe
    }, []);

    const openAdminCard = useCallback(() => {
        setShowAdminCard(true);
    }, []);

    // Drag handling
    const handleDragStart = (e) => {
        e.preventDefault();
        setIsDragging(true);
        // Calculate offset from mouse to element top-left
        const rect = e.currentTarget.getBoundingClientRect();
        setDragStart({
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        });
    };

    const handleDragMove = (e) => {
        if (isDragging) {
            setCardPosition({
                x: e.clientX - dragStart.x,
                y: e.clientY - dragStart.y
            });
        }
    };

    const handleDragEnd = () => {
        setIsDragging(false);
    };

    useEffect(() => {
        if (isDragging) {
            window.addEventListener('mousemove', handleDragMove);
            window.addEventListener('mouseup', handleDragEnd);
            return () => {
                window.removeEventListener('mousemove', handleDragMove);
                window.removeEventListener('mouseup', handleDragEnd);
            };
        }
    }, [isDragging]);

    useSpeech({ onCommand: handleCommand, enabled: micEnabled });

    const isAdminLocked = locked && mode === 'admin' && !adminAuthed;

    return (
        <div className="w-screen h-screen relative overflow-hidden select-none bg-[#02030A]">
            <Background />

            <div className="absolute inset-0 px-10 py-6 flex flex-col justify-between" style={{ zIndex: 20, pointerEvents: 'none' }}>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-6">
                        <div className="font-orbitron text-[8px] tracking-[0.45em] text-[#00B7FF]/45 uppercase flex items-center gap-3">
                            <span className="inline-block w-6 h-px bg-[#00B7FF]/40" />
                            STARK INDUSTRIES
                        </div>
                        <div className="flex items-center rounded-full border border-[#00B7FF]/30 overflow-hidden" style={{ pointerEvents: 'auto' }}>
                            {['normal', 'admin'].map((m) => (
                                <button
                                    key={m}
                                    onClick={() => setMode(m)}
                                    className={`px-3 py-1 text-[9px] font-orbitron uppercase tracking-[0.3em] transition ${
                                        mode === m ? 'bg-[#00B7FF] text-[#001018]' : 'text-[#00B7FF]/70 hover:text-[#00D9FF]'
                                    }`}
                                >
                                    {m === 'admin' ? '🛡 Admin' : '👤 Normal'}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="text-right">
                        <div className="flex items-center justify-end gap-3 text-[#DFFAFF]">
                            <span className="font-orbitron text-[11px] tracking-[0.35em] uppercase">10:42 PM</span>
                            <span className="inline-flex h-5 w-5 items-center justify-center rounded border border-[#00B7FF]/30 text-[#00B7FF] text-[10px]">🔒</span>
                        </div>
                        <div className="font-grotesk text-[8px] tracking-[0.35em] text-[#00B7FF]/35 uppercase mt-1">
                            FRIDAY, MAY 16, 2025
                        </div>
                    </div>
                </div>

                <div className="relative flex flex-col items-center mt-4">
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
                                        AWAITING FINGERPRINT OR PASSWORD
                                    </p>
                                </motion.div>
                            ) : (
                                <motion.div
                                    key="ambient"
                                    initial={{ opacity: 0, y: 8 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="flex flex-col items-center gap-2"
                                >
                                    <h2 className="font-orbitron text-[1.2rem] tracking-[0.5em] text-[#00B7FF] font-light" style={{ textShadow: '0 0 16px rgba(0,183,255,0.35)' }}>
                                        AMBIENT MODE
                                    </h2>
                                    <p className="font-grotesk text-[9px] text-[#DFFAFF]/35 tracking-[0.35em] uppercase">
                                        LISTENING — VOICE COMMANDS ACTIVE
                                    </p>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        {responseMessage && appState === 'SPEAKING' ? (
                            <div className="mt-3 text-[11px] text-[#DFFAFF] font-grotesk tracking-[0.08em] uppercase drop-shadow-[0_0_6px_#00D9FF]">
                                {responseMessage}
                            </div>
                        ) : null}

                        <div className="mt-3 flex items-center justify-center gap-3">
                            <button
                                onClick={() => runAuthSequence('wake', { speakImmediately: true })}
                                className="px-3 py-2 rounded bg-[#00B7FF]/10 border border-[#00B7FF]/30 text-[#00D9FF] text-[10px] uppercase"
                                style={{ pointerEvents: 'auto' }}
                            >
                                Test Response
                            </button>
                        </div>

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

                <div className="relative flex items-center justify-between w-full max-w-[1220px] mx-auto mt-14" style={{ pointerEvents: 'auto' }}>
                    {/* Left side: Status or Admin Login */}
                    <motion.div
                        className="relative" /* make it relative for absolute positioning of card */
                        initial={{ opacity: 0, x: -28 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.2, duration: 0.9, ease: 'easeOut' }}
                    >
                        {isAdminLocked && !showAdminCard ? (
                            <motion.button
                                onClick={openAdminCard}
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -20 }}
                                transition={{ duration: 0.3, ease: 'easeOut' }}
                                className="group flex items-center gap-3 px-4 py-3 rounded-2xl bg-gradient-to-r from-[#001018]/60 to-[#001018]/30 border border-[#00B7FF]/20 hover:border-[#00B7FF]/40 hover:from-[#001018]/80 transition-all duration-300"
                                style={{ pointerEvents: 'auto' }}
                                onMouseDown={handleDragStart}
                            >
                                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#00B7FF]/20 to-[#00B7FF]/5 flex items-center justify-center group-hover:from-[#00B7FF]/30 group-hover:to-[#00B7FF]/10 transition-all duration-300">
                                    <svg className="w-5 h-5 text-[#00D9FF]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2-2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                                    </svg>
                                </div>
                                <div className="flex flex-col items-start">
                                    <span className="font-orbitron text-[9px] tracking-[0.2em] text-[#00D9FF] uppercase">Admin Access</span>
                                    <span className="font-grotesk text-[8px] text-[#DFFAFF]/40">Tap to authenticate</span>
                                </div>
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    className="ml-auto w-6 h-6 rounded-lg bg-gradient-to-br from-[#00B7FF]/10 to-transparent flex items-center justify-center group-hover:from-[#00B7FF]/20 transition-all duration-300"
                                >
                                    <svg className="w-4 h-4 text-[#00B7FF]/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                    </svg>
                                </motion.div>
                            </motion.button>
                        ) : showAdminCard ? (
                            <motion.div
                                initial={{ opacity: 0, y: 20, scale: 0.96 }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={{ opacity: 0, y: -10, scale: 0.96 }}
                                transition={{ delay: 0.1, duration: 0.4, ease: 'easeOut' }}
                                className="w-80 h-80 rounded-2xl border border-[#00B7FF]/20 bg-gradient-to-b from-[#001018]/90 to-[#000814]/90 p-6 shadow-[0_0_50px_rgba(0,183,255,0.12),0_20px_40px_rgba(0,0,0,0.4)] backdrop-blur-md"
                                style={{
                                    transform: `translate3d(${cardPosition.x}px, ${cardPosition.y}px, 0)`,
                                    // Ensure it stays within viewport (simple clamping)
                                    // We'll rely on user not dragging too far; could add bounds logic
                                }}
                                onMouseDown={handleDragStart}
                            >
                                {/* Subtle glow border */}
                                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-[#00B7FF]/10 to-transparent opacity-50" />

                                {/* Close button */}
                                <button
                                    onClick={closeAdminCard}
                                    className="absolute top-3 right-3 w-8 h-8 rounded-xl bg-[#001018]/50 border border-[#00B7FF]/10 hover:border-[#00B7FF]/30 hover:bg-[#001018]/70 flex items-center justify-center transition-all duration-200"
                                    style={{ pointerEvents: 'auto' }}
                                >
                                    <svg className="w-4 h-4 text-[#DFFAFF]/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                </button>

                                <div className="flex items-center gap-2 mb-2">
                                    <div className="w-2 h-2 rounded-full bg-[#00B7FF]/60 animate-pulse" />
                                    <span className="font-orbitron text-[9px] tracking-[0.3em] text-[#00D9FF] uppercase">Admin Access</span>
                                </div>
                                <p className="font-grotesk text-[9px] text-[#DFFAFF]/40 tracking-[0.15em] uppercase mb-6">Authenticate to command FRIDAY</p>

                                {/* Fingerprint Button */}
                                <button
                                    onClick={onFingerprint}
                                    disabled={fpState === 'pending'}
                                    className="w-full px-4 py-3 rounded-2xl bg-gradient-to-r from-[#00B7FF]/15 to-[#00B7FF]/5 border border-[#00B7FF]/20 text-[#00D9FF] text-[10px] uppercase font-medium transition-all duration-300 hover:from-[#00B7FF]/25 hover:to-[#00B7FF]/10 hover:border-[#00D9FF]/40 hover:shadow-[0_0_20px_rgba(0,183,255,0.15)] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed group"
                                >
                                    {fpState === 'pending' ? (
                                        <span className="flex items-center justify-center gap-2">
                                            <span className="w-5 h-5 border-2 border-[#00D9FF] border-t-transparent rounded-full animate-spin" />
                                            Scanning…
                                        </span>
                                    ) : (
                                        <span className="flex items-center justify-center gap-2">
                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 002-2H6a2 2 0 00-2-2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                                            </svg>
                                            Use Fingerprint
                                        </span>
                                    )}
                                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none rounded-2xl" />
                                </button>
                                {fpError ? (
                                    <motion.div
                                        initial={{ opacity: 0, x: -10 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        className="mt-3 text-[9px] text-[#ff6b81] uppercase tracking-[0.1em] animate-shake"
                                    >{fpError}</motion.div>
                                ) : null}

                                {/* Divider */}
                                <div className="my-5 flex items-center gap-3 text-[#00B7FF]/20 text-[7px] uppercase tracking-[0.25em]">
                                    <span className="h-px flex-1 bg-gradient-to-r from-transparent via-[#00B7FF]/20 to-transparent" />
                                    <span className="px-2 text-[#DFFAFF]/30">or</span>
                                    <span className="h-px flex-1 bg-gradient-to-r from-transparent via-[#00B7FF]/20 to-transparent" />
                                </div>

                                {/* Password Form */}
                                <form onSubmit={onSubmitPassword} className="flex flex-col gap-3">
                                    <label className="relative group">
                                        <span className="absolute left-4 top-1/2 -translate-y-1/2 text-[#8b93a5] transition-all duration-300 peer-placeholder-shown:text-[12px] peer-focus:text-[#00D9FF]/60 peer-focus:-translate-y-6 peer-focus:text-[9px] peer-focus:-translate-y-7">
                                            Written password
                                        </span>
                                        <input
                                            type="password"
                                            value={password}
                                            onChange={(e) => setPassword(e.target.value)}
                                            placeholder=" "
                                            className="w-full px-4 py-3.5 pr-12 rounded-2xl bg-[#02030A] border border-[#00B7FF]/20 text-[#DFFAFF] text-[12px] outline-none focus:border-[#00D9FF] focus:ring-1 focus:ring-[#00D9FF]/20 transition-all duration-300 placeholder:text-transparent peer"
                                            style={{ pointerEvents: 'auto' }}
                                            autoComplete="current-password"
                                            required
                                        />
                                        <div className="absolute right-4 top-1/2 -translate-y-1/2 text-[#00B7FF]/40 group-hover:text-[#00D9FF]/60 transition-colors">
                                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 002-2H6a2 2 0 00-2-2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                                            </svg>
                                        </div>
                                    </label>
                                    <button
                                        type="submit"
                                        disabled={pwBusy}
                                        className="w-full px-4 py-3.5 rounded-2xl bg-gradient-to-r from-[#00B7FF] to-[#0099cc] text-[#001018] text-[10px] uppercase font-bold transition-all duration-300 hover:from-[#00ccff] hover:to-[#00B7FF] hover:shadow-[0_0_25px_rgba(0,183,255,0.3)] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {pwBusy ? (
                                            <span className="flex items-center justify-center gap-2">
                                                <span className="w-5 h-5 border-2 border-[#001018] border-t-transparent rounded-full animate-spin" />
                                                Checking…
                                            </span>
                                        ) : (
                                            'Sign In'
                                        )}
                                    </button>
                                    {pwError ? (
                                        <motion.div
                                            initial={{ opacity: 0, y: -10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            className="text-[9px] text-[#ff6b81] uppercase tracking-[0.1em] animate-shake"
                                        >{pwError}</motion.div>
                                    ) : null}
                                </form>

                                {resetMsg ? (
                                    <motion.div
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        className="mt-2 text-[9px] text-[#00D9FF] uppercase tracking-[0.1em]"
                                    >{resetMsg}</motion.div>
                                ) : null}

                                {IS_DEV ? (
                                    <motion.div
                                        initial={{ opacity: 0, y: -10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        className="mt-3 font-grotesk text-[8px] text-[#00B7FF]/40 tracking-[0.1em] uppercase"
                                    >
                                        dev password: <span className="text-[#00D9FF]">{DEV_PASSWORD}</span>
                                    </motion.div>
                                ) : null}

                                <motion.button
                                    type="button"
                                    onClick={onReset}
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    className="mt-3 text-[8px] text-[#DFFAFF]/30 uppercase tracking-[0.1em] underline hover:text-[#00D9FF] transition-colors"
                                    style={{ pointerEvents: 'auto' }}
                                >
                                    Forgot password? Reset access
                                </motion.button>

                                <motion.p
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="mt-4 font-grotesk text-[8px] text-[#DFFAFF]/25 leading-5"
                                >
                                    First sign-in sets your admin password. Switch to Normal mode for open access.
                                </motion.p>
                            </motion.div>
                        ) : null}
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

            {!locked && !audioEnabled ? (
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