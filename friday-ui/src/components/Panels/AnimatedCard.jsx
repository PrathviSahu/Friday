import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

/* Reusable SVG chamfered-corner card base */
export default function AnimatedCard({ children, width = 260, height = 320, className = '' }) {
    const pathRef = useRef(null);
    const c = 12; // chamfer size

    const d = [
        `M ${c},0`,
        `L ${width - c},0`,
        `L ${width},${c}`,
        `L ${width},${height - c}`,
        `L ${width - c},${height}`,
        `L ${c},${height}`,
        `L 0,${height - c}`,
        `L 0,${c}`,
        'Z'
    ].join(' ');

    const perimeter = 2 * (width + height) - 4 * c * (2 - Math.SQRT2);

    return (
        <div className={`relative ${className}`} style={{ width, height }}>
            {/* SVG border that draws itself in */}
            <svg
                className="absolute inset-0 pointer-events-none"
                width={width}
                height={height}
                style={{ overflow: 'visible' }}
            >
                {/* Background fill */}
                <path d={d} fill="rgba(2, 10, 24, 0.52)" />

                {/* Animated border */}
                <motion.path
                    ref={pathRef}
                    d={d}
                    fill="none"
                    stroke="#00B7FF"
                    strokeWidth="1"
                    strokeOpacity="0.28"
                    style={{
                        strokeDasharray: perimeter,
                        strokeDashoffset: perimeter,
                        filter: 'drop-shadow(0 0 5px rgba(0,183,255,0.22))',
                    }}
                    animate={{ strokeDashoffset: 0 }}
                    transition={{ duration: 1.6, ease: 'easeInOut', delay: 0.2 }}
                />

                {/* Corner glow dots */}
                {[
                    [c / 2, c / 2],
                    [width - c / 2, c / 2],
                    [width - c / 2, height - c / 2],
                    [c / 2, height - c / 2],
                ].map(([cx, cy], i) => (
                    <motion.circle
                        key={i}
                        cx={cx} cy={cy} r={2}
                        fill="#00D9FF"
                        animate={{ opacity: [0.3, 1, 0.3] }}
                        transition={{ duration: 2, repeat: Infinity, delay: i * 0.4 }}
                        style={{ filter: 'drop-shadow(0 0 4px #00D9FF)' }}
                    />
                ))}
            </svg>

            {/* Hover light sweep */}
            <motion.div
                className="absolute inset-0 pointer-events-none overflow-hidden"
                style={{ clipPath: `polygon(${c}px 0%, calc(100% - ${c}px) 0%, 100% ${c}px, 100% calc(100% - ${c}px), calc(100% - ${c}px) 100%, ${c}px 100%, 0% calc(100% - ${c}px), 0% ${c}px)` }}
                initial={false}
                whileHover={{ opacity: 1 }}
            >
                <motion.div
                    className="absolute top-0 -left-full h-full w-1/2"
                    style={{ background: 'linear-gradient(90deg, transparent, rgba(0,183,255,0.06), transparent)' }}
                    whileHover={{ x: '350%' }}
                    transition={{ duration: 0.7, ease: 'easeOut' }}
                />
            </motion.div>

            {/* Content */}
            <div className="absolute inset-0 p-5 flex flex-col" style={{ zIndex: 1 }}>
                {children}
            </div>
        </div>
    );
}
