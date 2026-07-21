import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    TrendingUp, ArrowRight, Square, Minus, MoveVertical,
    GitCommit, ArrowUpRight, ArrowDownRight, Brush, Trash2, Sliders, Pin, Palette
} from 'lucide-react';

const FLOATING_ITEMS = [
    { id: 'trend', name: 'Trendline', icon: TrendingUp },
    { id: 'arrow', name: 'Arrow', icon: ArrowRight },
    { id: 'rect', name: 'Rectangle', icon: Square },
    { id: 'hline', name: 'H-Line', icon: Minus },
    { id: 'vline', name: 'V-Line', icon: MoveVertical },
    { id: 'fib_ret', name: 'Fib Ret', icon: GitCommit },
    { id: 'long', name: 'Long Pos', icon: ArrowUpRight },
    { id: 'short', name: 'Short Pos', icon: ArrowDownRight },
    { id: 'brush', name: 'Brush', icon: Brush },
];

const COLORS = ['#00B7FF', '#10b981', '#ef4444', '#eab308', '#a855f7', '#ffffff'];

export default function FloatingToolbar({ activeTool, setActiveTool, onClear }) {
    const [color, setColor] = useState('#00B7FF');
    const [pinned, setPinned] = useState(false);
    const [showPicker, setShowPicker] = useState(false);

    if (!activeTool || activeTool === 'select' || activeTool === 'crosshair') return null;

    return (
        <AnimatePresence>
            <motion.div
                drag
                dragConstraints={{ left: -400, right: 400, top: -200, bottom: 400 }}
                initial={{ opacity: 0, y: -20, scale: 0.9 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="absolute top-16 left-1/2 -translate-x-1/2 z-40 flex items-center gap-1.5 px-3 py-1.5 rounded-2xl bg-[#090e1a]/95 border border-cyan-500/40 shadow-[0_12px_40px_rgba(0,0,0,0.8),0_0_20px_rgba(0,183,255,0.25)] backdrop-blur-2xl cursor-grab active:cursor-grabbing select-none"
            >
                <div className="text-[10px] font-mono text-cyan-400 font-bold uppercase border-r border-cyan-500/20 pr-2">
                    {activeTool}
                </div>

                {/* Tools shortcuts */}
                {FLOATING_ITEMS.map((item) => {
                    const Icon = item.icon;
                    const isActive = activeTool === item.id;
                    return (
                        <button
                            key={item.id}
                            onClick={() => setActiveTool(item.id)}
                            title={item.name}
                            className={`p-1.5 rounded-lg transition-all cursor-pointer ${
                                isActive
                                    ? 'bg-cyan-500/30 text-cyan-300 border border-cyan-400/50'
                                    : 'text-slate-400 hover:text-cyan-300 hover:bg-cyan-500/10'
                            }`}
                        >
                            <Icon size={14} />
                        </button>
                    );
                })}

                <div className="w-[1px] h-4 bg-cyan-500/20 mx-1" />

                {/* Color picker toggle */}
                <div className="relative">
                    <button
                        onClick={() => setShowPicker((s) => !s)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-cyan-300 transition-colors flex items-center gap-1 cursor-pointer"
                        title="Line Color"
                    >
                        <div className="w-3.5 h-3.5 rounded-full border border-white/40" style={{ background: color }} />
                    </button>
                    {showPicker && (
                        <div className="absolute top-9 left-0 p-2 rounded-xl bg-[#070b14] border border-cyan-500/30 flex gap-1.5 z-50 shadow-xl">
                            {COLORS.map((c) => (
                                <button
                                    key={c}
                                    onClick={() => { setColor(c); setShowPicker(false); }}
                                    className="w-4 h-4 rounded-full border border-white/20 hover:scale-125 transition-transform cursor-pointer"
                                    style={{ background: c }}
                                />
                            ))}
                        </div>
                    )}
                </div>

                {/* Clear / Delete */}
                <button
                    onClick={() => { onClear?.(); setActiveTool('select'); }}
                    className="p-1.5 rounded-lg text-red-400/70 hover:text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
                    title="Delete Current Drawing"
                >
                    <Trash2 size={14} />
                </button>

                {/* Pin toggle */}
                <button
                    onClick={() => setPinned((p) => !p)}
                    className={`p-1.5 rounded-lg transition-colors cursor-pointer ${pinned ? 'text-cyan-400' : 'text-slate-500 hover:text-slate-300'}`}
                    title={pinned ? 'Pinned' : 'Unpinned'}
                >
                    <Pin size={13} />
                </button>
            </motion.div>
        </AnimatePresence>
    );
}
