import { motion } from 'framer-motion';
import AnimatedCard from '../Panels/AnimatedCard';
import { useFriday } from '../../context/FridayContext';
import { useEffect, useState, useRef } from 'react';
import { Shield, Wifi, TrendingUp, Database, Fingerprint } from 'lucide-react';

const STATUS_ITEMS = [
    { icon: Shield,      label: 'Core Systems',    sub: 'Locked',  dot: '#ef4444' },
    { icon: Wifi,        label: 'Network',          sub: 'Standby', dot: '#f59e0b' },
    { icon: TrendingUp,  label: 'Trading Engine',   sub: 'Locked',  dot: '#ef4444' },
    { icon: Database,    label: 'Data Vault',       sub: 'Locked',  dot: '#ef4444' },
];

export default function StatusCard() {
    const { showDebug } = useFriday();
    const [shift, setShift] = useState(0);
    const [fixedStyle, setFixedStyle] = useState(null);
    const wrapperRef = useRef(null);

    useEffect(() => {
        const calcShift = () => {
            const max = 320;
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
                    <div className="font-sans text-[10px] tracking-[0.15em] text-slate-400/70 border-b border-slate-600/20 pb-2 mb-1 font-medium">
                        System Status
                    </div>

                    {STATUS_ITEMS.map(({ icon: Icon, label, sub, dot }, i) => (
                        <motion.div
                            key={i}
                            className="flex items-center gap-3"
                            style={{ paddingRight: '1.5rem' }}
                            initial={{ opacity: 0, x: 10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.3 + i * 0.12 }}
                        >
                            <Icon size={12} className="text-slate-400/60 shrink-0" />
                            <div className="flex-1 min-w-0">
                                <div className="font-sans text-[9px] tracking-wide text-slate-400/60">{label}</div>
                                <div className="font-sans text-[10px] tracking-wide text-slate-300/80">{sub}</div>
                            </div>
                            <div
                                className="w-1.5 h-1.5 rounded-full shrink-0"
                                style={{ backgroundColor: dot }}
                            />
                        </motion.div>
                    ))}

                    <div className="border-t border-slate-600/15 pt-3 mt-1">
                        <div className="font-sans text-[9px] tracking-[0.15em] text-slate-400/50 mb-3">Quick Hint</div>

                        <div className="text-center space-y-2">
                            <p className="font-sans text-xs text-slate-300/70 italic">"Hey Friday"</p>
                            <p className="text-[8px] text-slate-400/40 tracking-wide">— or —</p>

                            <div className="flex justify-center">
                                <div className="border border-slate-600/25 rounded-lg p-2">
                                    <Fingerprint size={24} className="text-slate-400/50" />
                                </div>
                            </div>
                            <p className="text-[8px] tracking-[0.15em] text-slate-400/40 uppercase">Scan to Unlock</p>
                        </div>
                    </div>
                </div>
            </AnimatedCard>
        </div>
    );
}
