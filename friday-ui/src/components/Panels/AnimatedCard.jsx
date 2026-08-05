import { useRef } from 'react';
import { motion } from 'framer-motion';

/* Reusable card base with subtle rounded corners */
export default function AnimatedCard({ children, width = 260, height = 320, className = '' }) {
    return (
        <div
            className={`relative rounded-xl border border-slate-600/20 bg-slate-900/60 backdrop-blur-sm ${className}`}
            style={{ width, height }}
        >
            <div className="absolute inset-0 p-5 flex flex-col" style={{ zIndex: 1 }}>
                {children}
            </div>
        </div>
    );
}
