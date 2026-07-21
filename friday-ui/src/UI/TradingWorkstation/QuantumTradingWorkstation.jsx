import React from 'react';
import { motion } from 'framer-motion';
import ProfessionalChart from './components/ProfessionalChart';

export default function QuantumTradingWorkstation({ onClose }) {
    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.04 }}
            transition={{ type: 'spring', stiffness: 280, damping: 28 }}
            className="fixed inset-0 z-50 flex flex-col bg-[#080d1a] text-slate-100 font-sans select-none overflow-hidden"
        >
            {/* Top Bar Header */}
            <header className="h-11 bg-[#050811] border-b border-cyan-500/20 px-4 flex items-center justify-between z-40">
                <div className="flex items-center gap-3">
                    <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_10px_#00B7FF]" />
                    <span className="font-mono text-xs font-extrabold tracking-widest text-cyan-300 uppercase">
                        F.R.I.D.A.Y. QUANT WORKSTATION
                    </span>
                    <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                        REAL-TIME STREAM
                    </span>
                </div>

                <button
                    onClick={onClose}
                    className="flex items-center gap-2 px-3 py-1 rounded-lg border border-rose-500/30 bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 text-xs font-mono tracking-wider transition-all cursor-pointer"
                >
                    ✕ Exit Trading Mode
                </button>
            </header>

            {/* Real-time TradingView Chart Container (Indian Stock Market NSE:NIFTY default) */}
            <div className="flex-1 w-full h-full relative">
                <ProfessionalChart symbol="NSE:NIFTY" />
            </div>
        </motion.div>
    );
}
