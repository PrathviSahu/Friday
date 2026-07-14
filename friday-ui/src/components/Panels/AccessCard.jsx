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

export default function AccessCard({ onFingerprint, fingerprintState = 'idle', fingerprintError = '' }) {
    const pending = fingerprintState === 'pending';
    const errored = fingerprintState === 'error';

    return (
        <AnimatedCard width={220} height={310}>
            <div className="flex flex-col items-center gap-4 mt-4">
                <motion.div
                    animate={{ opacity: [0.7, 1, 0.7] }}
                    transition={{ duration: 2.5, repeat: Infinity }}
                >
                    <LockIcon />
                </motion.div>

                <div className="text-center mt-2">
                    <div className="font-orbitron text-xs tracking-[0.2em] text-[#00B7FF] font-bold">
                        ACCESS REQUIRED
                    </div>
                    <div className="w-12 h-px bg-[#00B7FF]/40 mx-auto mt-2" />
                </div>

                <div className="text-center space-y-2 mt-2">
                    <p className="text-[10px] tracking-[0.15em] text-[#DFFAFF]/60 uppercase font-grotesk">
                        Voice Passphrase
                    </p>
                    <p className="text-[9px] text-[#00B7FF]/40 tracking-widest">— OR —</p>
                    <button
                        type="button"
                        onClick={onFingerprint}
                        disabled={pending}
                        className={`mt-1 px-4 py-1.5 rounded border text-[10px] tracking-[0.15em] uppercase font-grotesk transition ${
                            errored
                                ? 'border-red-400/50 text-red-300'
                                : 'border-[#00B7FF]/40 text-[#DFFAFF]/70 hover:border-[#00B7FF] hover:text-[#00D9FF]'
                        } ${pending ? 'opacity-60 cursor-wait' : 'cursor-pointer'}`}
                        style={{ pointerEvents: 'auto' }}
                    >
                        {pending ? 'Scanning…' : 'Fingerprint'}
                    </button>
                    {errored && fingerprintError ? (
                        <p className="text-[8px] text-red-300/80 tracking-[0.08em] mt-1 px-2">{fingerprintError}</p>
                    ) : null}
                </div>

                {/* Scan line animation */}
                <motion.div
                    className="w-full h-px mt-4"
                    style={{ background: 'linear-gradient(90deg, transparent, #00B7FF, transparent)' }}
                    animate={{ opacity: [0.2, 0.8, 0.2] }}
                    transition={{ duration: 1.8, repeat: Infinity }}
                />
            </div>
        </AnimatedCard>
    );
}
