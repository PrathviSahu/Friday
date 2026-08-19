import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default function CommandHUDOverlay() {
    const [activeCommand, setActiveCommand] = useState(null);

    useEffect(() => {
        const handleCommand = (e) => {
            if (e.detail?.transcript || e.detail?.cmd) {
                const transcript = e.detail.transcript || e.detail.cmd;
                const reply = e.detail.reply || 'Processing command...';
                const intent = e.detail.intent || 'Fast-Path Engine (34.6ms)';
                setActiveCommand({
                    transcript,
                    reply,
                    intent,
                    timestamp: Date.now(),
                });
                setTimeout(() => {
                    setActiveCommand((cur) => (cur && Date.now() - cur.timestamp >= 4500 ? null : cur));
                }, 5000);
            }
        };

        window.addEventListener('friday-command-hud', handleCommand);
        return () => window.removeEventListener('friday-command-hud', handleCommand);
    }, []);

    return (
        <AnimatePresence>
            {activeCommand && (
                <motion.div
                    initial={{ opacity: 0, y: -40, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -30, scale: 0.95 }}
                    transition={{ type: 'spring', stiffness: 400, damping: 28 }}
                    className="fixed top-6 left-1/2 -translate-x-1/2 z-[9999] pointer-events-none w-[90%] max-w-[560px]"
                >
                    <div className="relative overflow-hidden rounded-xl border border-[#00B7FF]/60 bg-[#00101d]/95 p-3.5 sm:p-4 shadow-[0_0_30px_rgba(0,183,255,0.35),0_12px_32px_rgba(0,0,0,0.85)] backdrop-blur-xl">
                        {/* Glowing scanline effect */}
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-[#00B7FF]/10 to-transparent animate-pulse pointer-events-none" />
                        
                        {/* Header tag */}
                        <div className="flex items-center justify-between gap-2 border-b border-[#00B7FF]/25 pb-2 mb-2">
                            <div className="flex items-center gap-2">
                                <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#00E5FF] shadow-[0_0_8px_#00E5FF] animate-ping" />
                                <span className="font-orbitron text-[10px] sm:text-[11px] font-extrabold uppercase tracking-[0.2em] text-[#00E5FF]">
                                    🎙️ VOICE / CONSOLE INPUT
                                </span>
                            </div>
                            <span className="font-orbitron text-[9px] font-semibold tracking-wider text-[#22ff99] bg-[#22ff99]/10 px-2 py-0.5 rounded border border-[#22ff99]/30">
                                {activeCommand.intent}
                            </span>
                        </div>

                        {/* Transcript command */}
                        <div className="font-grotesk text-[13.5px] sm:text-[14.5px] font-bold text-white tracking-wide mb-1.5 flex items-center gap-1.5">
                            <span className="text-[#00B7FF] font-mono text-sm">&gt;</span>
                            <span className="text-[#DFFAFF]">"{activeCommand.transcript}"</span>
                        </div>

                        {/* F.R.I.D.A.Y. AI response */}
                        {activeCommand.reply && (
                            <div className="font-grotesk text-[11.5px] sm:text-[12.5px] text-[#8ce8ff] leading-relaxed pl-3 border-l-2 border-[#00B7FF]/50 mt-1">
                                <span className="font-orbitron text-[9.5px] text-[#00B7FF] font-bold uppercase tracking-wider block mb-0.5">
                                    🤖 F.R.I.D.A.Y. RESPONSE:
                                </span>
                                {activeCommand.reply}
                            </div>
                        )}
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
