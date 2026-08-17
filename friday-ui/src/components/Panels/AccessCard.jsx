import React, { useState } from 'react';
import { motion } from 'framer-motion';
import AnimatedCard from './AnimatedCard';

function LockIcon() {
    return (
        <svg width="52" height="60" viewBox="0 0 52 60" fill="none">
            {/* Dotted orbit circle */}
            <circle cx="26" cy="22" r="20" stroke="#00B7FF" strokeWidth="0.6" strokeDasharray="2 4" opacity="0.5" />
            {/* Lock body */}
            <rect x="12" y="26" width="28" height="22" rx="3"
                fill="none" stroke="#00B7FF" strokeWidth="1.5"
                style={{ filter: 'drop-shadow(0 0 5px #00B7FF)' }} />
            {/* Lock shackle */}
            <path d="M 17,26 L 17,18 A 9,9 0 0 1 35,18 L 35,26"
                fill="none" stroke="#00B7FF" strokeWidth="1.5"
                strokeLinecap="round"
                style={{ filter: 'drop-shadow(0 0 5px #00B7FF)' }} />
            {/* Keyhole */}
            <circle cx="26" cy="35" r="3" fill="#00D9FF" opacity="0.8" />
            <rect x="24.5" y="35" width="3" height="6" rx="1" fill="#00D9FF" opacity="0.8" />
        </svg>
    );
}

export default function AccessCard({ onFingerprint, fingerprintState = 'idle', fingerprintError = '', onPasswordUnlock, onDemoUnlock }) {
    const [password, setPassword] = useState('');
    const [passPending, setPassPending] = useState(false);
    const [errText, setErrText] = useState('');

    const scanPending = fingerprintState === 'pending';
    const errored = fingerprintState === 'error' || errText;

    const handleSubmit = async (e) => {
        e.preventDefault();
        const cleanPw = password.trim();
        if (!cleanPw || !onPasswordUnlock) return;
        setPassPending(true);
        setErrText('');
        try {
            const res = await onPasswordUnlock(cleanPw);
            if (res && res.ok) {
                setPassword('');
            } else {
                setErrText(res.reason === 'wrong' ? 'Invalid Passphrase' : 'Verification failed');
            }
        } catch (err) {
            setErrText('Crypto error');
        } finally {
            setPassPending(false);
        }
    };

    return (
        <AnimatedCard width={220} height={350}>
            <div className="flex flex-col items-center gap-2 mt-3 px-2">
                <motion.div
                    animate={{ opacity: [0.7, 1, 0.7] }}
                    transition={{ duration: 2.5, repeat: Infinity }}
                >
                    <LockIcon />
                </motion.div>

                <div className="text-center mt-0.5">
                    <div className="text-sm font-semibold text-[#00D9FF] tracking-tight">
                        Access Control
                    </div>
                    <div className="w-10 h-px bg-[#00B7FF]/40 mx-auto mt-1.5" />
                </div>

                <div className="text-center space-y-2 mt-1 w-full">
                    <form onSubmit={handleSubmit} className="w-full space-y-2">
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Enter Passphrase..."
                            disabled={passPending}
                            className="w-full text-center bg-[#02030A]/70 border border-[#00B7FF]/30 focus:border-[#00B7FF] rounded-lg px-3 py-1.5 text-xs text-[#DFFAFF] outline-none transition-all placeholder:text-slate-500"
                            style={{ pointerEvents: 'auto' }}
                        />
                        <button
                            type="submit"
                            disabled={passPending || !password.trim()}
                            className="w-full py-1.5 rounded-lg bg-[#00B7FF]/15 border border-[#00B7FF]/40 text-xs font-semibold text-[#00D9FF] cursor-pointer hover:bg-[#00B7FF]/25 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                            style={{ pointerEvents: 'auto' }}
                        >
                            {passPending ? 'Verifying...' : 'Authorize'}
                        </button>
                    </form>

                    <div className="flex items-center gap-2 my-1">
                        <div className="h-px flex-1 bg-white/10" />
                        <p className="text-[9px] text-slate-400 font-medium">OR</p>
                        <div className="h-px flex-1 bg-white/10" />
                    </div>

                    <button
                        type="button"
                        onClick={onFingerprint}
                        disabled={scanPending}
                        className={`w-full py-1.5 rounded-lg border text-xs font-medium transition ${
                            errored
                                ? 'border-red-400/50 text-red-300 bg-red-500/10'
                                : 'border-[#00B7FF]/30 text-slate-300 hover:border-[#00B7FF] hover:text-[#00D9FF] hover:bg-white/[0.03]'
                        } ${scanPending ? 'opacity-50 cursor-wait' : 'cursor-pointer'}`}
                        style={{ pointerEvents: 'auto' }}
                    >
                        {scanPending ? 'Scanning…' : 'Biometric Fingerprint'}
                    </button>

                    {onDemoUnlock && (
                        <button
                            type="button"
                            onClick={onDemoUnlock}
                            className="w-full py-2 rounded-lg bg-[#00D9FF]/20 border border-[#00D9FF]/60 text-xs font-bold text-[#00D9FF] cursor-pointer hover:bg-[#00D9FF]/35 shadow-[0_0_16px_rgba(0,217,255,0.2)] transition-all"
                            style={{ pointerEvents: 'auto' }}
                        >
                            ⚡ Instant Demo Access
                        </button>
                    )}

                    {errored && (
                        <p className="text-[10px] text-red-400 mt-1 px-1">
                            {errText || fingerprintError}
                        </p>
                    )}
                </div>

                {/* Scan line animation */}
                <motion.div
                    className="w-full h-px mt-2.5"
                    style={{ background: 'linear-gradient(90deg, transparent, #00B7FF, transparent)' }}
                    animate={{ opacity: [0.2, 0.8, 0.2] }}
                    transition={{ duration: 1.8, repeat: Infinity }}
                />
            </div>
        </AnimatedCard>
    );
}
