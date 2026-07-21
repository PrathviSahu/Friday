import React from 'react';
import { motion } from 'framer-motion';
import {
    MousePointer, Crosshair, TrendingUp, MoveUpRight, ArrowRight,
    Minus, MoveVertical, Square, Circle, CircleOff, Brush,
    Type, MessageSquare, Ruler, ArrowUpRight, ArrowDownRight,
    Scale, GitCommit, GitBranch, Layers, Sliders, Magnet,
    Zap, ZoomIn, Lock, Trash2
} from 'lucide-react';

const DRAWING_TOOLS = [
    { id: 'select', name: 'Select', icon: MousePointer, group: 'cursor' },
    { id: 'crosshair', name: 'Crosshair', icon: Crosshair, group: 'cursor' },
    
    { id: 'trend', name: 'Trend Line', icon: TrendingUp, group: 'lines' },
    { id: 'arrow', name: 'Arrow', icon: MoveUpRight, group: 'lines' },
    { id: 'ray', name: 'Ray', icon: ArrowRight, group: 'lines' },
    { id: 'hline', name: 'Horizontal Line', icon: Minus, group: 'lines' },
    { id: 'vline', name: 'Vertical Line', icon: MoveVertical, group: 'lines' },

    { id: 'rect', name: 'Rectangle', icon: Square, group: 'shapes' },
    { id: 'circle', name: 'Circle', icon: Circle, group: 'shapes' },
    { id: 'ellipse', name: 'Ellipse', icon: CircleOff, group: 'shapes' },
    { id: 'brush', name: 'Brush', icon: Brush, group: 'shapes' },

    { id: 'text', name: 'Text Annotation', icon: Type, group: 'text' },
    { id: 'callout', name: 'Callout', icon: MessageSquare, group: 'text' },

    { id: 'measure', name: 'Ruler / Measure', icon: Ruler, group: 'tools' },
    { id: 'long', name: 'Long Position', icon: ArrowUpRight, group: 'prediction' },
    { id: 'short', name: 'Short Position', icon: ArrowDownRight, group: 'prediction' },
    { id: 'risk_reward', name: 'Risk Reward', icon: Scale, group: 'prediction' },

    { id: 'fib_ret', name: 'Fibonacci Retracement', icon: GitCommit, group: 'fib' },
    { id: 'fib_ext', name: 'Fibonacci Extension', icon: GitBranch, group: 'fib' },
    { id: 'pitchfork', name: 'Pitchfork', icon: Layers, group: 'fib' },
    { id: 'parallel', name: 'Parallel Channel', icon: Sliders, group: 'fib' },

    { id: 'magnet', name: 'Magnet Mode', icon: Magnet, group: 'utility' },
    { id: 'snap', name: 'Snap Mode', icon: Zap, group: 'utility' },
    { id: 'zoom', name: 'Zoom Tool', icon: ZoomIn, group: 'utility' },
    { id: 'lock', name: 'Lock Drawings', icon: Lock, group: 'utility' },
    { id: 'delete', name: 'Delete Drawings', icon: Trash2, group: 'utility' },
];

export default function LeftSidebar({ activeTool, setActiveTool, onClear }) {
    const handleToolClick = (toolId) => {
        if (toolId === 'delete') {
            onClear?.();
            setActiveTool('select');
        } else {
            setActiveTool(toolId);
        }
    };

    return (
        <aside className="w-12 bg-[#070a11]/90 border-r border-cyan-500/20 flex flex-col items-center py-3 gap-1 z-30 select-none backdrop-blur-xl">
            <div className="text-[9px] font-mono text-cyan-400/60 font-bold mb-1 tracking-wider uppercase">
                TOOLS
            </div>

            <div className="flex-1 flex flex-col gap-1 overflow-y-auto pr-0.5 w-full items-center scrollbar-none">
                {DRAWING_TOOLS.map((t) => {
                    const Icon = t.icon;
                    const isActive = activeTool === t.id;
                    const isDelete = t.id === 'delete';

                    return (
                        <motion.button
                            key={t.id}
                            whileHover={{ scale: 1.15, x: 2 }}
                            whileTap={{ scale: 0.9 }}
                            onClick={() => handleToolClick(t.id)}
                            title={`${t.name}`}
                            className={`relative p-2 rounded-xl transition-all cursor-pointer flex items-center justify-center ${
                                isActive
                                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/50 shadow-[0_0_12px_rgba(0,217,255,0.3)]'
                                    : isDelete
                                    ? 'text-red-400/60 hover:text-red-400 hover:bg-red-500/10'
                                    : 'text-slate-400 hover:text-cyan-300 hover:bg-cyan-500/10'
                            }`}
                        >
                            <Icon size={16} />
                            {isActive && (
                                <motion.div
                                    layoutId="activeToolGlow"
                                    className="absolute inset-0 rounded-xl border border-cyan-400/60 pointer-events-none"
                                />
                            )}
                        </motion.button>
                    );
                })}
            </div>
        </aside>
    );
}
