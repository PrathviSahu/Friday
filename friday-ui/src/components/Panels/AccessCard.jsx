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
                    <div className="font-orbitron text-xs tracking-[0.2em] text-[#00B7FF] font-bold">
                        ACCESS REQUIRED
                    </div>
                    <div className="w-12 h-px bg-[#00B7FF]/40 mx-auto mt-2.5" />
                </div>

                <div className="text-center space-y-2 mt-1 w-full">
                    <form onSubmit={handleSubmit} className="w-full space-y-2">
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Enter Passphrase..."
                            disabled={passPending}
                            className="w-full text-center bg-[#02030A]/65 border border-[#00B7FF]/25 focus:border-[#00B7FF]/65 rounded px-2 py-1 text-[10px] font-grotesk tracking-widest text-[#DFFAFF] outline-none transition-all placeholder:text-[#DFFAFF]/20"
                            style={{ pointerEvents: 'auto' }}
                        />
                        <button
                            type="submit"
                            disabled={passPending || !password.trim()}
                            className="w-full py-1 rounded bg-[#00B7FF]/10 border border-[#00B7FF]/35 text-[9px] tracking-[0.2em] uppercase font-orbitron text-[#00D9FF] cursor-pointer hover:bg-[#00B7FF]/20 transition-all disabled:opacity-25 disabled:cursor-not-allowed"
                            style={{ pointerEvents: 'auto' }}
                        >
                            {passPending ? 'Verifying...' : 'Authorize'}
                        </button>
                    </form>

                    <p className="text-[8px] text-[#00B7FF]/25 tracking-widest uppercase font-orbitron mt-1">— OR —</p>

                    <button
                        type="button"
                        onClick={onFingerprint}
                        disabled={scanPending}
                        className={`w-full py-1 rounded border text-[9px] tracking-[0.2em] uppercase font-orbitron transition ${
                            errored
                                ? 'border-red-400/40 text-red-300'
                                : 'border-[#00B7FF]/25 text-[#DFFAFF]/60 hover:border-[#00B7FF] hover:text-[#00D9FF]'
                        } ${scanPending ? 'opacity-50 cursor-wait' : 'cursor-pointer'}`}
                        style={{ pointerEvents: 'auto' }}
                    >
                        {scanPending ? 'Scanning…' : 'Fingerprint'}
                    </button>
                    {errored && (
                        <p className="text-[8.5px] text-red-400/80 tracking-[0.05em] mt-1.5 px-1 font-grotesk uppercase">
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
