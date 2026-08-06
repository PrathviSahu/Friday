import { motion } from 'framer-motion';
import AnimatedCard from '../Panels/AnimatedCard';
import { useFriday } from '../../context/FridayContext';
import { useEffect, useState, useRef } from 'react';
import { Shield, Wifi, TrendingUp, Database, Fingerprint } from 'lucide-react';

const STATUS_ITEMS = [
    { icon: Shield,      label: 'CORE SYSTEMS',    sub: 'LOCKED',  dot: '#ff4444' },
    { icon: Wifi,        label: 'NETWORK',          sub: 'STANDBY', dot: '#ffaa00' },
    { icon: TrendingUp,  label: 'TRADING ENGINE',   sub: 'LOCKED',  dot: '#ff4444' },
    { icon: Database,    label: 'DATA VAULT',       sub: 'LOCKED',  dot: '#ff4444' },
];

export default function StatusCard() {
    const { showDebug } = useFriday();
    const [shift, setShift] = useState(0);
    const [fixedStyle, setFixedStyle] = useState(null);
    const wrapperRef = useRef(null);

    useEffect(() => {
        const calcShift = () => {
            const max = 320; // debug panel width
            const vw = window.innerWidth;
            const computed = Math.min(max, Math.round(vw * 0.3));
            setShift(showDebug ? computed : 0);
        };

        if (wrapperRef.current) {
            const rect = wrapperRef.current.getBoundingClientRect();
            const gap = 18;
            setFixedStyle({
                position: 'fixed',
                top: rect.top,
                right: gap,
                width: rect.width,
                zIndex: 40,
                transition: 'all 260ms cubic-bezier(.2,.9,.2,1)'
            });
        }

        calcShift();
        window.addEventListener('resize', calcShift);
        return () => window.removeEventListener('resize', calcShift);
    }, [showDebug]);

    return (
        <div
            ref={wrapperRef}
            style={{
                ...fixedStyle,
                transition: 'transform 260ms cubic-bezier(.2,.9,.2,1)',
                transform: `translateX(${shift}px)`,
            }}
        >
            <AnimatedCard width={260} height={340}>
                <div className="flex flex-col gap-3">
                    {/* Header */}
                    <div className="font-orbitron text-[9px] tracking-[0.25em] text-[#00B7FF]/60 border-b border-[#00B7FF]/10 pb-2 mb-1">
                        SYSTEM STATUS
                    </div>

                    {/* Status rows */}
                    {STATUS_ITEMS.map(({ icon: Icon, label, sub, dot }, i) => (
                        <motion.div
                            key={i}
                            className="flex items-center gap-3"
                            style={{ paddingRight: '1.5rem' }}
                            initial={{ opacity: 0, x: 10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.3 + i * 0.12 }}
                        >
                            <Icon size={12} className="text-[#00B7FF]/50 shrink-0" />
                            <div className="flex-1 min-w-0">
                                <div className="font-orbitron text-[8px] tracking-widest text-[#DFFAFF]/50">{label}</div>
                                <div className="font-orbitron text-[9px] tracking-widest text-[#DFFAFF]/80">{sub}</div>
                            </div>
                            <motion.div
                                className="w-1.5 h-1.5 rounded-full shrink-0"
                                style={{ backgroundColor: dot, boxShadow: `0 0 6px ${dot}` }}
                                animate={{ opacity: [0.5, 1, 0.5] }}
                                transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.3 }}
                            />
                        </motion.div>
                    ))}

                    {/* Divider & Fingerprint Hint */}
                    <div className="border-t border-[#00B7FF]/10 pt-3 mt-1">
                        <div className="font-orbitron text-[9px] tracking-[0.2em] text-[#00B7FF]/50 mb-3">QUICK HINT</div>

                        <div className="text-center space-y-2">
                            <p className="font-grotesk text-xs text-[#DFFAFF]/70 italic">"Hey Friday"</p>
                            <p className="text-[8px] text-[#00B7FF]/40 tracking-widest">— OR —</p>

                            <div className="flex justify-center">
                                <div className="border border-[#00B7FF]/30 rounded p-2" style={{ filter: 'drop-shadow(0 0 4px rgba(0,183,255,0.3))' }}>
                                    <Fingerprint size={24} className="text-[#00B7FF]/60" />
                                </div>
                            </div>
                            <p className="text-[8px] tracking-[0.2em] text-[#DFFAFF]/40 uppercase">Scan to Unlock</p>
                        </div>
                    </div>
                </div>
            </AnimatedCard>
        </div>
    );
}
