import React, { useState } from 'react';
import { motion } from 'framer-motion';
import AnimatedCard from './AnimatedCard';

function LockIcon() {
    return (
        <svg width="52" height="60" viewBox="0 0 52 60" fill="none">
            <circle cx="26" cy="22" r="20" stroke="#94a3b8" strokeWidth="0.6" strokeDasharray="2 4" opacity="0.3" />
            <rect x="12" y="26" width="28" height="22" rx="3"
                fill="none" stroke="#94a3b8" strokeWidth="1.5" />
            <path d="M 17,26 L 17,18 A 9,9 0 0 1 35,18 L 35,26"
                fill="none" stroke="#94a3b8" strokeWidth="1.5"
                strokeLinecap="round" />
            <circle cx="26" cy="35" r="3" fill="#60a5fa" opacity="0.6" />
            <rect x="24.5" y="35" width="3" height="6" rx="1" fill="#60a5fa" opacity="0.6" />
        </svg>
    );
}

export default function AccessCard({ onFingerprint, fingerprintState = 'idle', fingerprintError = '', onPasswordUnlock }) {
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
        <AnimatedCard width={220} height={310}>
            <div className="flex flex-col items-center gap-3 mt-4 px-2">
                <motion.div
                    animate={{ opacity: [0.7, 1, 0.7] }}
                    transition={{ duration: 2.5, repeat: Infinity }}
                >
                    <LockIcon />
                </motion.div>

                <div className="text-center mt-1">
                    <div className="font-sans text-xs tracking-[0.15em] text-slate-300 font-medium">
                        Access Required
                    </div>
                    <div className="w-12 h-px bg-slate-500/30 mx-auto mt-2.5" />
                </div>

                <div className="text-center space-y-2 mt-1 w-full">
                    <form onSubmit={handleSubmit} className="w-full space-y-2">
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Enter Passphrase..."
                            disabled={passPending}
                            className="w-full text-center bg-slate-800/60 border border-slate-600/25 focus:border-slate-400/50 rounded-lg px-2 py-1.5 text-[11px] font-sans tracking-wide text-slate-200 outline-none transition-all placeholder:text-slate-500/50"
                            style={{ pointerEvents: 'auto' }}
                        />
                        <button
                            type="submit"
                            disabled={passPending || !password.trim()}
                            className="w-full py-1.5 rounded-lg bg-blue-500/15 border border-blue-500/30 text-[10px] tracking-wide uppercase font-sans font-medium text-blue-300 cursor-pointer hover:bg-blue-500/25 transition-all disabled:opacity-25 disabled:cursor-not-allowed"
                            style={{ pointerEvents: 'auto' }}
                        >
                            {passPending ? 'Verifying...' : 'Authorize'}
                        </button>
                    </form>

                    <p className="text-[8px] text-slate-400/40 tracking-widest uppercase font-sans mt-1">— or —</p>

                    <button
                        type="button"
                        onClick={onFingerprint}
                        disabled={scanPending}
                        className={`w-full py-1.5 rounded-lg border text-[10px] tracking-wide uppercase font-sans font-medium transition ${
                            errored
                                ? 'border-red-400/30 text-red-300'
                                : 'border-slate-600/25 text-slate-400 hover:border-slate-500 hover:text-slate-200'
                        } ${scanPending ? 'opacity-50 cursor-wait' : 'cursor-pointer'}`}
                        style={{ pointerEvents: 'auto' }}
                    >
                        {scanPending ? 'Scanning…' : 'Fingerprint'}
                    </button>
                    {errored && (
                        <p className="text-[8.5px] text-red-400/70 tracking-[0.03em] mt-1.5 px-1 font-sans">
                            {errText || fingerprintError}
                        </p>
                    )}
                </div>
            </div>
        </AnimatedCard>
    );
}
