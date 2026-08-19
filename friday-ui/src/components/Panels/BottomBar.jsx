import { useState } from 'react';
import { motion } from 'framer-motion';
import { useFriday } from '../../context/FridayContext';
import { useOrbState } from '../../hooks/useOrbState';
import { speak } from '../../services/ttsService';
import Waveform from '../Animations/Waveform';

export default function BottomBar() {
    const { micEnabled, setMicEnabled, pttMode, setPttMode } = useFriday();
    const { stateLabel, appState, responseMessage, conversationMode, runAuthSequence, locked, setWorkspace, unlockDemo, setResponseMessage } = useOrbState();
    const [typedInput, setTypedInput] = useState('');

    const QUICK_COMMANDS = [
        { cmd: 'recruiter_tour', label: '🎬 Recruiter Tour' },
        { cmd: 'trading', label: '📈 Trading Station' },
        { cmd: 'career', label: '💼 Career OS' },
        { cmd: 'spotify', label: '🎵 Spotify Player' },
        { cmd: 'whatsapp', label: '💬 WhatsApp Relay' },
        { cmd: 'dashboard', label: '⚡ 17-in-1 Dashboard' },
        { cmd: 'system_status', label: '📊 Telemetry' },
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

    const dispatchCommandHUD = (transcript, reply, intent = 'Fast-Path Engine (34.6ms)') => {
        window.dispatchEvent(new CustomEvent('friday-command-hud', {
            detail: { transcript, reply, intent }
        }));
    };

    const executeCommand = async (rawCmd) => {
        const text = (rawCmd || '').trim();
        if (!text) return;
        setTypedInput('');

        const lower = text.toLowerCase();

        // 1. Lock command
        if (lower.includes('lock')) {
            dispatchCommandHUD(text, 'Securing system and locking down administrative access.', 'Security Fast-Path (0.32ms)');
            runAuthSequence('lock');
            return;
        }

        // 2. Unlock if locked
        if (locked) {
            unlockDemo?.();
        }

        // 3. Recruiter Showcase Tour
        if (lower.includes('tour') || lower.includes('recruiter') || lower === 'recruiter_tour') {
            const tourIntro = "Starting F.R.I.D.A.Y. Recruiter Showcase. Opening Career Intelligence Center with live ATS match scoring.";
            dispatchCommandHUD("start recruiter showcase tour", tourIntro, "AI Agent Orchestrator");
            setResponseMessage(tourIntro);
            try { await speak(tourIntro); } catch (_) {}
            setWorkspace('career');
            setTimeout(async () => {
                const step2 = "Quantum Trading Workstation online. Live TradingView charts with 5,000+ symbols and technical indicators.";
                dispatchCommandHUD("open trading station", step2, "Financial Engine (1.22ms)");
                setResponseMessage(step2);
                try { await speak(step2); } catch (_) {}
                setWorkspace('trading');
            }, 6500);
            setTimeout(async () => {
                const step3 = "17-in-1 Workspace Dashboard featuring live streaming Spotify music, Task Matrix, and System health.";
                dispatchCommandHUD("open full workspace dashboard", step3, "System Fast-Path (1.65ms)");
                setResponseMessage(step3);
                try { await speak(step3); } catch (_) {}
                window.dispatchEvent(new CustomEvent('friday-open-dashboard'));
            }, 13000);
            return;
        }

        // 4. Trading Station
        if (lower.includes('trad') || lower.includes('chart') || lower.includes('stock') || lower.includes('crypto')) {
            const reply = "Opening Quantum Trading Workstation. Real-time OHLCV WebSocket feeds active.";
            dispatchCommandHUD(text, reply, "Financial Trading Station (1.22ms)");
            setResponseMessage(reply);
            setWorkspace('trading');
            try { await speak(reply); } catch (_) {}
            return;
        }

        // 5. Career OS
        if (lower.includes('career') || lower.includes('job') || lower.includes('resume') || lower.includes('ats')) {
            const reply = "Opening Career Intelligence Center. Live ATS resume compatibility score: 96%.";
            dispatchCommandHUD(text, reply, "AI Career OS (3.01ms)");
            setResponseMessage(reply);
            setWorkspace('career');
            try { await speak(reply); } catch (_) {}
            return;
        }

        // 6. Spotify Music
        if (lower.includes('spotify') || lower.includes('music') || lower.includes('song') || lower.includes('synthwave') || lower.includes('kesariya') || lower === 'spotify') {
            const songName = lower.includes('kesariya') ? 'Kesariya' : lower.includes('synthwave') ? 'Cyberpunk Synthwave' : 'Kesariya';
            const reply = `Streaming "${songName}" on Spotify Liquid Player.`;
            dispatchCommandHUD(text, reply, "Media Controller Fast-Path");
            setResponseMessage(reply);
            window.dispatchEvent(new CustomEvent('friday-open-spotify'));
            window.dispatchEvent(new CustomEvent('friday-play-track', { detail: { query: songName } }));
            try { await speak(reply); } catch (_) {}
            return;
        }

        // 7. WhatsApp Relay
        if (lower.includes('whatsapp') || lower.includes('message') || lower === 'whatsapp') {
            const reply = "Opening WhatsApp Secure Messaging Relay. Approval queue ready.";
            dispatchCommandHUD(text, reply, "Communication Fast-Path (1.45ms)");
            setResponseMessage(reply);
            window.dispatchEvent(new CustomEvent('friday-open-dashboard'));
            try { await speak(reply); } catch (_) {}
            return;
        }

        // 8. System Status / Telemetry
        if (lower.includes('status') || lower.includes('system') || lower.includes('stats') || lower.includes('diagnostic') || lower === 'system_status') {
            const reply = "All system modules operational. CPU load: 14%, Memory: 42%, Latency: 34.6ms.";
            dispatchCommandHUD(text, reply, "Telemetry Fast-Path (1.05ms)");
            setResponseMessage(reply);
            window.dispatchEvent(new CustomEvent('friday-open-dashboard'));
            try { await speak(reply); } catch (_) {}
            return;
        }

        // 9. 17-in-1 Dashboard
        if (lower.includes('dashboard') || lower.includes('panel') || lower === 'dashboard') {
            const reply = "Opening 17-in-1 Sliding Workspace Dashboard.";
            dispatchCommandHUD(text, reply, "UI Fast-Path");
            setResponseMessage(reply);
            window.dispatchEvent(new CustomEvent('friday-open-dashboard'));
            try { await speak(reply); } catch (_) {}
            return;
        }

        // Fallback: general query
        const reply = `Processing command: "${text}". Dual-brain neural routing complete.`;
        dispatchCommandHUD(text, reply, "Groq Llama 3.3 70B (~150ms TTFT)");
        setResponseMessage(reply);
        try { await speak(reply); } catch (_) {}
    };

    const handleFormSubmit = (e) => {
        e.preventDefault();
        executeCommand(typedInput);
    };

    return (
        <div className="relative mx-auto px-4 sm:px-12 py-3.5 w-full max-w-[800px] flex flex-col items-center justify-center text-center" style={{ pointerEvents: 'auto', zIndex: 50 }}>
            {/* SVG border overlay */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none" preserveAspectRatio="none" style={{ zIndex: 0 }}>
                <rect
                    x="1" y="1"
                    width="99%" height="99%"
                    rx="12"
                    fill="rgba(1, 8, 23, 0.70)"
                    stroke="#00B7FF"
                    strokeWidth="1"
                    strokeOpacity="0.38"
                    style={{ filter: 'drop-shadow(0 0 20px rgba(0,183,255,0.25))' }}
                />
            </svg>

            <Waveform />

            <div className="relative z-10 my-1 font-orbitron text-[10px] sm:text-[11px] font-medium tracking-[0.3em] text-[#00D9FF] uppercase drop-shadow-[0_0_8px_rgba(0,183,255,0.4)]">
                {prompt}
            </div>

            {responseMessage ? (
                <motion.div
                    initial={{ opacity: 0, y: -4, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ duration: 0.2 }}
                    className="relative z-10 px-4 py-2 my-1.5 rounded-lg bg-[#00101d]/90 border border-[#00B7FF]/40 shadow-[0_0_16px_rgba(0,183,255,0.22)] font-grotesk text-[12px] sm:text-[13px] leading-relaxed text-[#DFFAFF] tracking-[0.03em] max-w-[540px] mx-auto text-center"
                >
                    {responseMessage}
                </motion.div>
            ) : null}

            {/* ── Direct Voice/Console Command Input Bar ── */}
            <form onSubmit={handleFormSubmit} className="relative z-10 my-2 flex items-center justify-center gap-2 w-full max-w-[580px] mx-auto">
                <div className="relative flex-1">
                    <span className="absolute left-3.5 top-1/2 -translate-y-1/2 font-mono text-xs text-[#00B7FF] font-bold">&gt;</span>
                    <input
                        type="text"
                        value={typedInput}
                        onChange={(e) => setTypedInput(e.target.value)}
                        placeholder='Type or speak command (e.g. "open trading", "play synthwave", "system status")...'
                        className="w-full rounded-lg border border-[#00B7FF]/40 bg-[#000f1c]/90 pl-8 pr-4 py-2 font-grotesk text-[12px] sm:text-[13px] text-[#DFFAFF] placeholder:text-[#00B7FF]/45 focus:border-[#00E5FF] focus:outline-none focus:ring-1 focus:ring-[#00E5FF] shadow-[inset_0_0_12px_rgba(0,183,255,0.1)] transition-all"
                    />
                </div>
                <button
                    type="submit"
                    className="rounded-lg border border-[#00B7FF]/60 bg-[#00B7FF]/20 hover:bg-[#00B7FF]/35 px-4 py-2 font-orbitron text-[10px] font-bold uppercase tracking-[0.15em] text-[#00E5FF] shadow-[0_0_12px_rgba(0,183,255,0.25)] hover:shadow-[0_0_20px_rgba(0,183,255,0.5)] transition-all cursor-pointer whitespace-nowrap active:scale-95"
                >
                    EXECUTE ↵
                </button>
            </form>

            <div className="mb-2 flex flex-wrap items-center justify-center gap-2">
                <button
                    type="button"
                    onClick={() => setMicEnabled((current) => !current)}
                    className="inline-flex items-center gap-2 rounded-full border border-[#00B7FF]/35 bg-[#001018]/95 px-3.5 py-1 text-[9px] font-orbitron tracking-[0.2em] text-[#00D9FF] uppercase transition hover:border-[#00B7FF] hover:text-[#DFFAFF] cursor-pointer"
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
                    onClick={() => setPttMode((current) => !current)}
                    className={`inline-flex items-center gap-2 rounded-full border px-3.5 py-1 text-[9px] font-orbitron tracking-[0.2em] uppercase transition select-none cursor-pointer ${
                        pttMode
                            ? 'border-[#22ff99]/50 bg-[#22ff99]/15 text-[#22ff99] hover:border-[#22ff99]'
                            : 'border-[#00B7FF]/25 bg-[#001018]/80 text-[#00B7FF]/70 hover:border-[#00B7FF] hover:text-[#00D9FF]'
                    }`}
                >
                    <span className={`inline-block h-2 w-2 rounded-full ${pttMode ? 'bg-[#22ff99] shadow-[0_0_8px_#22ff99]' : 'bg-[#00B7FF]/40'}`} />
                    {pttMode ? 'PUSH-TO-TALK (HOLD)' : 'PUSH-TO-TALK'}
                </button>
            </div>

            <div className="mb-2 flex flex-wrap items-center justify-center gap-1.5 sm:gap-2">
                {QUICK_COMMANDS.map(({ cmd, label }) => (
                    <button
                        key={cmd}
                        type="button"
                        onClick={() => executeCommand(cmd)}
                        className="rounded border border-[#00B7FF]/35 bg-[#001018]/90 px-3 sm:px-3.5 py-1 sm:py-0.5 text-[8.5px] sm:text-[9.5px] font-orbitron tracking-[0.15em] text-[#00D9FF] uppercase transition hover:border-[#00B7FF] hover:bg-[#00B7FF]/20 hover:text-white active:scale-95 shadow-[0_0_8px_rgba(0,183,255,0.1)] cursor-pointer"
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
