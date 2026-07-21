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
            className="fixed inset-0 z-50 flex flex-col bg-[#131722] text-slate-100 font-sans select-none overflow-hidden"
        >
            {/* Floating Exit Button over TradingView Top Right */}
            <div className="absolute top-2.5 right-20 z-50">
                <button
                    onClick={onClose}
                    className="flex items-center gap-1.5 px-3 py-1 rounded-lg border border-rose-500/40 bg-[#131722]/90 text-rose-400 hover:bg-rose-500/20 text-xs font-mono tracking-wider transition-all cursor-pointer shadow-lg backdrop-blur-md"
                >
                    ✕ Exit Trading
                </button>
            </div>

            {/* Real-time TradingView Chart Container */}
            <div className="flex-1 w-full h-full relative">
                <ProfessionalChart />
            </div>
        </motion.div>
    );
}
