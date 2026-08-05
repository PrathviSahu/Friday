import { useState } from 'react';
import { motion } from 'framer-motion';
import { normalize } from '../../services/passphraseStore';

/**
 * First-run enrollment. Collects a spoken unlock phrase and a distinct lock
 * phrase, then hands them to `onEnroll` (which persists them + creates the
 * encrypted vault).
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
            className="absolute inset-0 z-[70] flex items-center justify-center bg-slate-950/95 px-6 py-10"
            style={{ pointerEvents: 'auto' }}
        >
            <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, ease: 'easeOut' }}
                className="max-w-2xl w-full rounded-2xl border border-slate-600/30 bg-slate-900/95 p-10"
            >
                <div className="font-sans text-[9px] tracking-[0.3em] text-slate-400/60 uppercase mb-4 text-center">
                    First-Time Setup
                </div>
                <h2 className="font-sans text-[2rem] tracking-[0.5em] text-slate-100 uppercase mb-2 text-center">
                    F.R.I.D.A.Y.
                </h2>
                <p className="font-sans text-sm text-slate-300/80 leading-6 mb-8 text-center">
                    Set a spoken phrase to unlock, and a different one to lock. You can
                    type them here or say them later — FRIDAY normalizes what it hears,
                    so keep them simple and distinct.
                </p>

                <form onSubmit={submit} className="space-y-5">
                    <div>
                        <label className="block font-sans text-[10px] tracking-[0.2em] text-slate-300 uppercase mb-2">
                            Unlock Phrase
                        </label>
                        <input
                            type="text"
                            value={unlock}
                            onChange={(e) => setUnlock(e.target.value)}
                            placeholder="e.g. open sesame friday"
                            autoFocus
                            className="w-full rounded-lg border border-slate-600/30 bg-slate-800/60 px-4 py-3 text-slate-200 font-sans text-sm tracking-wide outline-none focus:border-slate-400/50"
                            style={{ pointerEvents: 'auto' }}
                        />
                        {nu ? (
                            <p className="text-[9px] text-slate-400/50 tracking-[0.1em] mt-1">
                                stored as: "{nu}"
                            </p>
                        ) : null}
                    </div>

                    <div>
                        <label className="block font-sans text-[10px] tracking-[0.2em] text-slate-300 uppercase mb-2">
                            Lock Phrase
                        </label>
                        <input
                            type="text"
                            value={lock}
                            onChange={(e) => setLock(e.target.value)}
                            placeholder="e.g. lock it down"
                            className="w-full rounded-lg border border-slate-600/30 bg-slate-800/60 px-4 py-3 text-slate-200 font-sans text-sm tracking-wide outline-none focus:border-slate-400/50"
                            style={{ pointerEvents: 'auto' }}
                        />
                        {nl ? (
                            <p className="text-[9px] text-slate-400/50 tracking-[0.1em] mt-1">
                                stored as: "{nl}"
                            </p>
                        ) : null}
                    </div>

                    {error ? (
                        <p className="text-[11px] text-red-300 tracking-[0.05em] text-center">{error}</p>
                    ) : null}

                    <button
                        type="submit"
                        className="w-full inline-flex items-center justify-center rounded-full bg-blue-500 px-8 py-3 text-[11px] font-bold uppercase tracking-[0.25em] text-white transition hover:bg-blue-400"
                        style={{ pointerEvents: 'auto' }}
                    >
                        Initialize Access
                    </button>
                </form>
            </motion.div>
        </div>
    );
}
