import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import LeftSidebar from './components/LeftSidebar';
import Watchlist from './components/Watchlist';
import AIAssistantPanel from './components/AIAssistantPanel';
import ProfessionalChart from './components/ProfessionalChart';
import FloatingToolbar from './components/FloatingToolbar';

const TIMEFRAMES = ['1m', '5m', '15m', '30m', '1H', '4H', '1D'];

export default function QuantumTradingWorkstation({ onClose }) {
    const [selectedSymbol, setSelectedSymbol] = useState('GC=F');
    const [interval, setInterval] = useState('5m');
    const [activeTool, setActiveTool] = useState('crosshair');
    const [clearSignal, setClearSignal] = useState(0);

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.04 }}
            transition={{ type: 'spring', stiffness: 280, damping: 28 }}
            className="fixed inset-0 z-50 flex flex-col bg-[#050811] text-slate-100 font-sans select-none overflow-hidden"
        >
            {/* Top Navigation Bar */}
            <header className="h-12 bg-[#070b14]/95 border-b border-cyan-500/20 px-4 flex items-center justify-between backdrop-blur-2xl z-40">
                {/* Left logo & Symbol */}
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                        <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_10px_#00B7FF]" />
                        <span className="font-mono text-xs font-extrabold tracking-widest text-cyan-300 uppercase">
                            F.R.I.D.A.Y. QUANT WORKSTATION
                        </span>
                    </div>

                    <div className="h-4 w-[1px] bg-cyan-500/20" />

                    <div className="flex items-center gap-2">
                        <span className="font-mono text-sm font-bold text-white">
                            {selectedSymbol}
                        </span>
                        <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                            LIVE
                        </span>
                    </div>
                </div>

                {/* Timeframes */}
                <div className="flex items-center gap-1 bg-[#090f1d] border border-cyan-500/20 rounded-xl p-1 text-[10px] font-mono">
                    {TIMEFRAMES.map((tf) => (
                        <button
                            key={tf}
                            onClick={() => setInterval(tf)}
                            className={`px-2.5 py-1 rounded-lg transition-all cursor-pointer ${
                                interval === tf
                                    ? 'bg-cyan-500/30 text-cyan-300 font-bold border border-cyan-400/40'
                                    : 'text-slate-400 hover:text-slate-200'
                            }`}
                        >
                            {tf}
                        </button>
                    ))}
                </div>

                {/* Exit / Return to Friday */}
                <button
                    onClick={onClose}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 text-xs font-mono tracking-wider transition-all cursor-pointer"
                >
                    ✕ Exit Trading Mode
                </button>
            </header>

            {/* Main Workstation Body */}
            <div className="flex-1 flex min-h-0 relative">
                {/* Left Drawing Sidebar */}
                <LeftSidebar
                    activeTool={activeTool}
                    setActiveTool={setActiveTool}
                    onClear={() => setClearSignal((c) => c + 1)}
                />

                {/* Center Canvas Chart */}
                <div className="flex-1 flex flex-col min-w-0 relative">
                    <FloatingToolbar
                        activeTool={activeTool}
                        setActiveTool={setActiveTool}
                        onClear={() => setClearSignal((c) => c + 1)}
                    />
                    <ProfessionalChart
                        symbol={selectedSymbol}
                        interval={interval}
                        activeTool={activeTool}
                        onClear={clearSignal}
                    />
                </div>

                {/* Right AI Assistant Panel */}
                <AIAssistantPanel symbol={selectedSymbol} currentPrice={2345.6} />

                {/* Far Right Watchlist Panel */}
                <Watchlist
                    selectedSymbol={selectedSymbol}
                    onSelectSymbol={setSelectedSymbol}
                />
            </div>
        </motion.div>
    );
}
