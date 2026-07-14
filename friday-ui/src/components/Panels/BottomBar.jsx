import { motion } from 'framer-motion';
import { useFriday } from '../../context/FridayContext';
import { useOrbState } from '../../hooks/useOrbState';
import Waveform from '../Animations/Waveform';

export default function BottomBar() {
    const { micEnabled, setMicEnabled } = useFriday();
    const { stateLabel, appState, responseMessage, conversationMode, runAuthSequence, locked } = useOrbState();

    // Quick-launch commands so panels open even when voice recognition is
    // unavailable (offline Web Speech, or the Tauri webview). These mirror the
    // voice commands in voiceCommands.js.
    const QUICK_COMMANDS = [
        { cmd: 'trading', label: 'Trading' },
        { cmd: 'dashboard', label: 'Dashboard' },
        { cmd: 'engineering', label: 'Engineering' },
        { cmd: 'vscode', label: 'VS Code' },
        { cmd: 'browser', label: 'Browser' },
        { cmd: 'lock', label: 'Lock' },
    ];
    const prompt = (() => {
        if (conversationMode === 'awaiting-command') return 'WAKE WORD DETECTED';
        if (appState === 'IDLE') return 'I AM STANDING BY, BOSS.';
        if (appState === 'LISTENING') return "I'M LISTENING...";
        if (appState === 'THINKING') return 'ANALYZING REQUEST...';
        if (appState === 'SPEAKING') return 'RESPONDING...';
        return stateLabel || 'I AM STANDING BY, BOSS.';
    })();
    const micLabel = micEnabled ? 'VOICE LISTENING ON' : 'VOICE LISTENING OFF';

    return (
        <div className="relative px-14 py-4 min-w-[360px] max-w-[720px] text-center">
            <svg className="absolute inset-0 w-full h-full" preserveAspectRatio="none">
                <rect
                    x="1" y="1"
                    width="calc(100% - 2)" height="calc(100% - 2)"
                    rx="8"
                    fill="rgba(1, 8, 23, 0.55)"
                    stroke="#00B7FF"
                    strokeWidth="1"
                    strokeOpacity="0.25"
                    style={{ filter: 'drop-shadow(0 0 16px rgba(0,183,255,0.18))' }}
                />
            </svg>

            <Waveform />

            <div className="relative font-orbitron text-[10px] tracking-[0.45em] text-[#00B7FF] uppercase mb-3">
                {prompt}
            </div>

            {responseMessage ? (
                <div className="font-grotesk text-[11px] text-[#DFFAFF] uppercase tracking-[0.2em] mb-3">
                    {responseMessage}
                </div>
            ) : null}

            <button
                type="button"
                onClick={() => setMicEnabled((current) => !current)}
                className="mx-auto mb-3 inline-flex items-center gap-2 rounded-full border border-[#00B7FF]/35 bg-[#001018]/95 px-4 py-2 text-[9px] tracking-[0.35em] text-[#00D9FF] uppercase transition hover:border-[#00B7FF] hover:text-[#DFFAFF]"
            >
                <span className={`inline-block h-2.5 w-2.5 rounded-full ${micEnabled ? 'bg-[#22ff99]' : 'bg-[#ff4d6d]'}`} />
                {micLabel}
            </button>

            <div className="mb-3 flex flex-wrap items-center justify-center gap-2">
                {QUICK_COMMANDS.map(({ cmd, label }) => (
                    <button
                        key={cmd}
                        type="button"
                        disabled={locked && cmd !== 'lock'}
                        onClick={() => runAuthSequence(cmd)}
                        className="rounded border border-[#00B7FF]/30 bg-[#001018]/80 px-3 py-1 text-[9px] tracking-[0.2em] text-[#00D9FF] uppercase transition hover:border-[#00B7FF] hover:text-[#DFFAFF] disabled:opacity-30 disabled:cursor-not-allowed"
                        style={{ pointerEvents: 'auto' }}
                    >
                        {label}
                    </button>
                ))}
            </div>

            <motion.p
                className="font-grotesk text-[8px] text-[#00B7FF]/45 uppercase"
                animate={{ opacity: [0.35, 0.85, 0.35] }}
                transition={{ duration: 3, repeat: Infinity }}
            >
                YOUR COMMAND. MY PRIORITY.
            </motion.p>
        </div>
    );
}
