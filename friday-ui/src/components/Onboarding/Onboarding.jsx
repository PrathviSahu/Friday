import { useState } from 'react';
import { motion } from 'framer-motion';
import { normalize } from '../../services/passphraseStore';

/**
 * First-run enrollment. Collects a spoken unlock phrase and a distinct lock
 * phrase, then hands them to `onEnroll` (which persists them + creates the
 * encrypted vault). Mirrors the HUD style of the lock-screen "Enable Voice"
 * gate so the two overlays read as one system.
 */
export default function Onboarding({ onEnroll }) {
    const [unlock, setUnlock] = useState('');
    const [lock, setLock] = useState('');
    const [error, setError] = useState('');

    const nu = normalize(unlock);
    const nl = normalize(lock);

    const submit = (e) => {
        e.preventDefault();
        if (!nu) { setError('Choose an unlock phrase.'); return; }
        if (!nl) { setError('Choose a lock phrase.'); return; }
        if (nu === nl) { setError('Unlock and lock phrases must be different.'); return; }
        setError('');
        onEnroll({ unlock, lock });
    };

    return (
        <div
            className="absolute inset-0 z-[70] flex items-center justify-center bg-[#02030A]/95 px-6 py-10"
            style={{ pointerEvents: 'auto' }}
        >
            <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, ease: 'easeOut' }}
                className="max-w-2xl w-full rounded-[2rem] border border-[#00B7FF]/30 bg-[#001018]/95 p-10 shadow-[0_0_80px_rgba(0,183,255,0.20)]"
            >
                <div className="font-orbitron text-[9px] tracking-[0.45em] text-[#00B7FF]/45 uppercase mb-4 text-center">
                    FIRST-TIME SETUP
                </div>
                <h2 className="font-orbitron text-[2rem] tracking-[0.5em] text-[#DFFAFF] uppercase mb-2 text-center">
                    F.R.I.D.A.Y.
                </h2>
                <p className="font-grotesk text-sm text-[#DFFAFF]/80 leading-6 mb-8 text-center">
                    Set a spoken phrase to unlock, and a different one to lock. You can
                    type them here or say them later — FRIDAY normalizes what it hears,
                    so keep them simple and distinct.
                </p>

                <form onSubmit={submit} className="space-y-5">
                    <div>
                        <label className="block font-orbitron text-[10px] tracking-[0.3em] text-[#00B7FF] uppercase mb-2">
                            Unlock Phrase
                        </label>
                        <input
                            type="text"
                            value={unlock}
                            onChange={(e) => setUnlock(e.target.value)}
                            placeholder="e.g. open sesame friday"
                            autoFocus
                            className="w-full rounded border border-[#00B7FF]/30 bg-[#02030A]/60 px-4 py-3 text-[#DFFAFF] font-grotesk text-sm tracking-wide outline-none focus:border-[#00B7FF]"
                            style={{ pointerEvents: 'auto' }}
                        />
                        {nu ? (
                            <p className="text-[9px] text-[#00B7FF]/50 tracking-[0.1em] mt-1">
                                stored as: “{nu}”
                            </p>
                        ) : null}
                    </div>

                    <div>
                        <label className="block font-orbitron text-[10px] tracking-[0.3em] text-[#00B7FF] uppercase mb-2">
                            Lock Phrase
                        </label>
                        <input
                            type="text"
                            value={lock}
                            onChange={(e) => setLock(e.target.value)}
                            placeholder="e.g. lock it down"
                            className="w-full rounded border border-[#00B7FF]/30 bg-[#02030A]/60 px-4 py-3 text-[#DFFAFF] font-grotesk text-sm tracking-wide outline-none focus:border-[#00B7FF]"
                            style={{ pointerEvents: 'auto' }}
                        />
                        {nl ? (
                            <p className="text-[9px] text-[#00B7FF]/50 tracking-[0.1em] mt-1">
                                stored as: “{nl}”
                            </p>
                        ) : null}
                    </div>

                    {error ? (
                        <p className="text-[11px] text-red-300 tracking-[0.1em] text-center">{error}</p>
                    ) : null}

                    <button
                        type="submit"
                        className="w-full inline-flex items-center justify-center rounded-full bg-[#00B7FF] px-8 py-3 text-[11px] font-bold uppercase tracking-[0.35em] text-[#001018] transition hover:bg-[#00d1ff]"
                        style={{ pointerEvents: 'auto' }}
                    >
                        Initialize Access
                    </button>
                </form>
            </motion.div>
        </div>
    );
}
