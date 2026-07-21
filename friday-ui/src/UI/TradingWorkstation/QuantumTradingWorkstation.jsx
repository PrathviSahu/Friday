import React, { useState } from 'react';
import { motion } from 'framer-motion';
import ProfessionalChart from './components/ProfessionalChart';
import CustomWatchlist from './components/Watchlist';

export default function QuantumTradingWorkstation({ onClose }) {
    const [selectedSymbol, setSelectedSymbol] = useState('OANDA:XAUUSD');

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.04 }}
            transition={{ type: 'spring', stiffness: 280, damping: 28 }}
            className="fixed inset-0 z-50 flex flex-col bg-[#131722] text-slate-100 font-sans select-none overflow-hidden"
        >
            {/* Top Bar Header */}
            <header className="h-10 bg-[#050811] border-b border-cyan-500/20 px-4 flex items-center justify-between z-40">
                <div className="flex items-center gap-3">
                    <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_10px_#00B7FF]" />
                    <span className="font-mono text-xs font-extrabold tracking-widest text-cyan-300 uppercase">
                        F.R.I.D.A.Y. PERSONAL TRADING STATION
                    </span>
                    <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 uppercase">
                        {selectedSymbol} • REAL-TIME
                    </span>
                </div>

                <button
                    onClick={onClose}
                    className="flex items-center gap-1.5 px-3 py-1 rounded-lg border border-rose-500/40 bg-[#131722]/90 text-rose-400 hover:bg-rose-500/20 text-xs font-mono tracking-wider transition-all cursor-pointer shadow-lg backdrop-blur-md"
                >
                    ✕ Exit Trading
                </button>
            </header>

            {/* Main Workstation Body: Chart on Left + Dedicated Watchlist Panel on Right */}
            <div className="flex-1 w-full h-full flex min-h-0 relative">
                {/* Real-time TradingView Chart Container */}
                <div className="flex-1 h-full relative">
                    <ProfessionalChart symbol={selectedSymbol} />
                </div>

                {/* Dedicated Custom Watchlist Panel (Forex + Indian Stock Market 🇮🇳) */}
                <CustomWatchlist
                    currentSymbol={selectedSymbol}
                    onSelectSymbol={setSelectedSymbol}
                />
            </div>
        </motion.div>
    );
}
