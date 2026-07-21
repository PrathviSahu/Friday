import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { TrendingUp, X, GripHorizontal, Maximize2, LineChart } from 'lucide-react';
import { useOrbState } from '../../hooks/useOrbState';

export default function TradingCard() {
    const { workspace, setWorkspace } = useOrbState();
    const isTradingOpen = workspace === 'trading';

    const toggleTrading = () => {
        if (isTradingOpen) {
            setWorkspace('unlocked');
        } else {
            setWorkspace('trading');
        }
    };

    if (isTradingOpen) return null; // Hide pill when full trading dashboard is active

    return (
        <AnimatePresence>
            <motion.div
                drag
                dragConstraints={{ left: -800, right: 400, top: -800, bottom: 200 }}
                dragElastic={0.1}
                whileDrag={{ scale: 1.05 }}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={toggleTrading}
                className="fixed bottom-20 left-10 z-50 flex items-center gap-2 px-3.5 py-2 rounded-full cursor-grab active:cursor-grabbing pointer-events-auto select-none bg-[#0a1622]/90 border border-emerald-500/30 text-emerald-400 shadow-[0_4px_20px_rgba(16,185,129,0.2)] text-[11px] font-mono"
            >
                <TrendingUp size={14} className="text-emerald-400 animate-pulse" />
                <span>Trading</span>
            </motion.div>
        </AnimatePresence>
    );
}
