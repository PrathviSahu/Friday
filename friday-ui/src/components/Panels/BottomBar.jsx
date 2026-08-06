import { motion } from 'framer-motion';
import { useFriday } from '../../context/FridayContext';
import { useOrbState } from '../../hooks/useOrbState';
import Waveform from '../Animations/Waveform';

export default function BottomBar() {
    const { micEnabled, setMicEnabled, pttMode, setPttMode } = useFriday();
    const { stateLabel, appState, responseMessage, conversationMode, runAuthSequence, locked } = useOrbState();

    const QUICK_COMMANDS = [
        { cmd: 'trading', label: 'Trading' },
        { cmd: 'dashboard', label: 'Dashboard' },
        { cmd: 'engineering', label: 'Engineering' },
        { cmd: 'vscode', label: 'VS Code' },
        { cmd: 'browser', label: 'Browser' },
        { cmd: 'lock', label: 'Lock' },
    ];
    const prompt = (() => {
        if (conversationMode === 'awaiting-command') return 'Wake word detected';
        if (appState === 'IDLE') return 'Standing by, Prem.';
        if (appState === 'LISTENING') return "Listening...";
        if (appState === 'THINKING') return 'Thinking...';
        if (appState === 'SPEAKING') return 'Responding...';
        return stateLabel || 'Standing by, Prem.';
    })();
    const micLabel = micEnabled ? 'Mic On' : 'Mic Off';

    return (
        <div className="relative px-14 py-4 min-w-[360px] max-w-[720px] text-center">
            <div className="absolute inset-0 rounded-xl border border-slate-600/20 bg-slate-900/70 backdrop-blur-sm" />

            <Waveform />

            <div className="relative font-sans text-[10px] tracking-[0.3em] text-slate-300 uppercase mb-3">
                {prompt}
            </div>

            {responseMessage ? (
                <div className="font-sans text-[11px] text-slate-200 tracking-[0.04em] mb-3">
                    {responseMessage}
                </div>
            ) : null}

            <div className="mb-3 flex flex-wrap items-center justify-center gap-2">
                <button
                    type="button"
                    onClick={() => setMicEnabled((current) => !current)}
                    className="inline-flex items-center gap-2 rounded-full border border-slate-600/30 bg-slate-800/80 px-4 py-2 text-[10px] tracking-wide text-slate-300 transition hover:border-slate-500 hover:text-slate-100"
                >
                    <span className={`inline-block h-2.5 w-2.5 rounded-full ${micEnabled ? 'bg-green-500' : 'bg-red-400'}`} />
                    {micLabel}
                </button>

                <button
                    type="button"
                    onClick={() => setPttMode((current) => !current)}
                    className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-[10px] tracking-wide uppercase transition ${
                        pttMode
                            ? 'border-green-500/40 bg-green-500/10 text-green-400 hover:border-green-500'
                            : 'border-slate-600/25 bg-slate-800/60 text-slate-400 hover:border-slate-500 hover:text-slate-200'
                    }`}
                >
                    <span className={`inline-block h-2.5 w-2.5 rounded-full ${pttMode ? 'bg-green-500' : 'bg-slate-500/40'}`} />
                    {pttMode ? 'Push-to-Talk On' : 'Push-to-Talk Off'}
                </button>
            </div>

            {pttMode && (
                <div className="mb-2 font-sans text-[8px] tracking-[0.2em] text-slate-400/60 uppercase">
                    Hold Space to talk · release to send
                </div>
            )}

            <div className="mb-3 flex flex-wrap items-center justify-center gap-2">
                {QUICK_COMMANDS.map(({ cmd, label }) => (
                    <button
                        key={cmd}
                        type="button"
                        disabled={locked && cmd !== 'lock'}
                        onClick={() => runAuthSequence(cmd)}
                        className="rounded-lg border border-slate-600/25 bg-slate-800/60 px-3 py-1 text-[10px] tracking-wide text-slate-300 transition hover:border-slate-500 hover:text-slate-100 disabled:opacity-30 disabled:cursor-not-allowed"
                        style={{ pointerEvents: 'auto' }}
                    >
                        {label}
                    </button>
                ))}
            </div>

            <motion.p
                className="font-sans text-[8px] text-slate-400/40 uppercase"
                animate={{ opacity: [0.3, 0.6, 0.3] }}
                transition={{ duration: 3, repeat: Infinity }}
            >
                Your command, my priority.
            </motion.p>
        </div>
    );
}
