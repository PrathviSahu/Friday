import { motion } from 'framer-motion';
import { useFriday } from '../../context/FridayContext';
import { useOrbState } from '../../hooks/useOrbState';
import { speak } from '../../services/ttsService';
import Waveform from '../Animations/Waveform';

export default function BottomBar() {
    const { micEnabled, setMicEnabled, pttMode, setPttMode } = useFriday();
    const { stateLabel, appState, responseMessage, conversationMode, runAuthSequence, locked, setWorkspace, unlockDemo, setResponseMessage } = useOrbState();

    const QUICK_COMMANDS = [
        { cmd: 'capabilities', label: '✨ Capabilities' },
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

    const handleCommandClick = async (cmd) => {
        if (cmd === 'lock') {
            runAuthSequence('lock');
            return;
        }
        if (cmd === 'capabilities') {
            const bioText = "I am F.R.I.D.A.Y., a voice-controlled AI operating system engineered by Prathvi Sahu (Prem), a Full-Stack Software Development Engineer from Mumbai. I feature real-time Quantum Trading, an autonomous Career OS, and dual-engine AI intelligence.";
            setResponseMessage(bioText);
            try {
                await speak(bioText);
            } catch (_) {}
            return;
        }
        if (locked) {
            unlockDemo?.();
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
    };

    return (
        <div className="relative px-4 sm:px-14 py-4 w-full max-w-[760px] text-center" style={{ pointerEvents: 'auto', zIndex: 50 }}>
            {/* SVG border overlay with pointer-events-none so it doesn't intercept clicks */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none" preserveAspectRatio="none" style={{ zIndex: 0 }}>
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

            <div className="relative font-orbitron text-[10px] sm:text-[11px] tracking-[0.35em] text-[#00B7FF] uppercase mb-2">
                {prompt}
            </div>

            {responseMessage ? (
                <div className="font-grotesk text-[11px] text-[#DFFAFF] tracking-[0.1em] mb-2.5 max-w-[620px] mx-auto">
                    {responseMessage}
                </div>
            ) : null}

            <div className="mb-2.5 flex flex-wrap items-center justify-center gap-2">
                <button
                    type="button"
                    onClick={() => setMicEnabled((current) => !current)}
                    className="inline-flex items-center gap-2 rounded-full border border-[#00B7FF]/35 bg-[#001018]/95 px-3.5 py-1.5 text-[9px] font-orbitron tracking-[0.2em] text-[#00D9FF] uppercase transition hover:border-[#00B7FF] hover:text-[#DFFAFF] cursor-pointer"
                >
                    <span className={`inline-block h-2 w-2 rounded-full ${micEnabled ? 'bg-[#22ff99]' : 'bg-[#ff4d6d]'}`} />
                    {micLabel}
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
                    className={`inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-[9px] font-orbitron tracking-[0.2em] uppercase transition select-none cursor-pointer ${
                        pttMode
                            ? 'border-[#22ff99]/50 bg-[#22ff99]/15 text-[#22ff99] hover:border-[#22ff99]'
                            : 'border-[#00B7FF]/25 bg-[#001018]/80 text-[#00B7FF]/70 hover:border-[#00B7FF] hover:text-[#00D9FF]'
                    }`}
                >
                    <span className={`inline-block h-2 w-2 rounded-full ${pttMode ? 'bg-[#22ff99] shadow-[0_0_8px_#22ff99]' : 'bg-[#00B7FF]/40'}`} />
                    {pttMode ? 'PUSH-TO-TALK (HOLD)' : 'PUSH-TO-TALK'}
                </button>
            </div>

            <div className="mb-2 font-grotesk text-[8px] sm:text-[9px] tracking-[0.2em] text-[#00B7FF]/60 uppercase">
                Hold Space or Hold button to talk · release to send
            </div>

            <div className="mb-2 flex flex-wrap items-center justify-center gap-1.5 sm:gap-2">
                {QUICK_COMMANDS.map(({ cmd, label }) => (
                    <button
                        key={cmd}
                        type="button"
                        onClick={() => handleCommandClick(cmd)}
                        className="rounded border border-[#00B7FF]/35 bg-[#001018]/90 px-3 sm:px-3.5 py-1.5 sm:py-1 text-[9px] sm:text-[9.5px] font-orbitron tracking-[0.15em] text-[#00D9FF] uppercase transition hover:border-[#00B7FF] hover:bg-[#00B7FF]/20 hover:text-white active:scale-95 shadow-[0_0_8px_rgba(0,183,255,0.1)] cursor-pointer"
                        style={{ pointerEvents: 'auto', touchAction: 'manipulation' }}
                    >
                        {label}
                    </button>
                ))}
            </div>

            <motion.p
                className="font-grotesk text-[8px] sm:text-[9px] text-[#00B7FF]/50 uppercase tracking-widest"
                animate={{ opacity: [0.35, 0.85, 0.35] }}
                transition={{ duration: 3, repeat: Infinity }}
            >
                YOUR COMMAND. MY PRIORITY.
            </motion.p>
        </div>
    );
}
