import { motion } from 'framer-motion';
import { useFriday } from '../../context/FridayContext';
import { useOrbState } from '../../hooks/useOrbState';
import Waveform from '../Animations/Waveform';

export default function BottomBar() {
    const { micEnabled, setMicEnabled, pttMode, setPttMode } = useFriday();
    const { stateLabel, appState, responseMessage, conversationMode, runAuthSequence, locked, setWorkspace } = useOrbState();

    // Quick-launch commands so panels open even when voice recognition is
    // unavailable (offline Web Speech, or the Tauri webview). These mirror the
    // voice commands in voiceCommands.js.
    const QUICK_COMMANDS = [
        { cmd: 'demo', label: '🎯 1-Click Demo' },
        { cmd: 'career', label: '💼 Career OS' },
        { cmd: 'trading', label: '📈 Trading Station' },
        { cmd: 'dashboard', label: '⚡ 17-in-1 Dashboard' },
        { cmd: 'engineering', label: '🛠️ Dev Console' },
        { cmd: 'lock', label: '🔒 Lock' },
    ];
    const prompt = (() => {
        if (conversationMode === 'awaiting-command') return 'WAKE WORD DETECTED';
        if (appState === 'IDLE') return 'I AM STANDING BY, PREM.';
        if (appState === 'LISTENING') return "I'M LISTENING...";
        if (appState === 'THINKING') return 'ANALYZING REQUEST...';
        if (appState === 'SPEAKING') return 'RESPONDING...';
        return stateLabel || 'I AM STANDING BY, PREM.';
    })();
    const micLabel = micEnabled ? 'VOICE LISTENING ON' : 'VOICE LISTENING OFF';

    return (
        <div className="relative px-4 sm:px-14 py-4 w-full max-w-[720px] text-center">
            <svg className="absolute inset-0 w-full h-full" preserveAspectRatio="none">
                <rect
                    x="1" y="1"
                    width="99%" height="99%"
                    rx="8"
                    fill="rgba(1, 8, 23, 0.55)"
                    stroke="#00B7FF"
                    strokeWidth="1"
                    strokeOpacity="0.25"
                    style={{ filter: 'drop-shadow(0 0 16px rgba(0,183,255,0.18))' }}
                />
            </svg>

            <Waveform />

            <div className="relative text-xs font-semibold tracking-wider text-[#00D9FF] mb-2">
                {prompt}
            </div>

            {responseMessage ? (
                <div className="text-xs text-[#DFFAFF] tracking-wide mb-2.5">
                    {responseMessage}
                </div>
            ) : null}

            <div className="mb-2.5 flex flex-wrap items-center justify-center gap-2">
                <button
                    type="button"
                    onClick={() => setMicEnabled((current) => !current)}
                    className="inline-flex items-center gap-2 rounded-full border border-[#00B7FF]/35 bg-[#001018]/95 px-3.5 py-1.5 text-xs font-medium text-[#00D9FF] transition hover:border-[#00B7FF] hover:text-[#DFFAFF] cursor-pointer"
                >
                    <span className={`inline-block h-2 w-2 rounded-full ${micEnabled ? 'bg-[#22ff99]' : 'bg-[#ff4d6d]'}`} />
                    {micEnabled ? 'Listening Active' : 'Listening Off'}
                </button>

                <button
                    type="button"
                    onPointerDown={() => {
                        window.dispatchEvent(new CustomEvent('friday-ptt-toggle', { detail: { active: true } }));
                    }}
                    onPointerUp={() => {
                        window.dispatchEvent(new CustomEvent('friday-ptt-toggle', { detail: { active: false } }));
                    }}
                    onPointerCancel={() => {
                        window.dispatchEvent(new CustomEvent('friday-ptt-toggle', { detail: { active: false } }));
                    }}
                    onClick={() => setPttMode((current) => !current)}
                    className={`inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-xs font-medium transition select-none cursor-pointer ${
                        pttMode
                            ? 'border-[#22ff99]/50 bg-[#22ff99]/15 text-[#22ff99] hover:border-[#22ff99]'
                            : 'border-[#00B7FF]/25 bg-[#001018]/80 text-[#00B7FF]/70 hover:border-[#00B7FF] hover:text-[#00D9FF]'
                    }`}
                >
                    <span className={`inline-block h-2 w-2 rounded-full ${pttMode ? 'bg-[#22ff99] shadow-[0_0_8px_#22ff99]' : 'bg-[#00B7FF]/40'}`} />
                    {pttMode ? 'Push-To-Talk (Hold)' : 'Push-To-Talk'}
                </button>
            </div>

            <div className="mb-2 text-[10px] text-slate-400">
                Hold Space or Hold button to talk · release to send
            </div>

            <div className="mb-2 flex flex-wrap items-center justify-center gap-1.5 sm:gap-2">
                {QUICK_COMMANDS.map(({ cmd, label }) => (
                    <button
                        key={cmd}
                        type="button"
                        disabled={locked && cmd !== 'lock' && cmd !== 'demo'}
                        onClick={() => {
                            if (cmd === 'demo') {
                                window.dispatchEvent(new CustomEvent('friday-open-recruiter-demo'));
                                return;
                            }
                            if (cmd === 'lock') {
                                runAuthSequence('lock');
                                return;
                            }
                            if (cmd === 'dashboard') {
                                window.dispatchEvent(new CustomEvent('friday-open-dashboard'));
                                return;
                            }
                            if (cmd === 'career' || cmd === 'trading') {
                                setWorkspace(cmd);
                                return;
                            }
                            runAuthSequence(cmd);
                        }}
                        className="rounded-lg border border-[#00B7FF]/35 bg-[#001018]/90 px-3 py-1.5 text-xs font-medium text-[#00D9FF] transition hover:border-[#00B7FF] hover:bg-[#00B7FF]/20 hover:text-white active:scale-95 disabled:opacity-30 disabled:cursor-not-allowed shadow-[0_0_8px_rgba(0,183,255,0.1)] cursor-pointer"
                        style={{ pointerEvents: 'auto', touchAction: 'manipulation' }}
                    >
                        {label}
                    </button>
                ))}
            </div>

            <motion.p
                className="text-[10px] text-[#00B7FF]/50"
                animate={{ opacity: [0.4, 0.9, 0.4] }}
                transition={{ duration: 3, repeat: Infinity }}
            >
                Your command. My priority.
            </motion.p>
        </div>
    );
}
