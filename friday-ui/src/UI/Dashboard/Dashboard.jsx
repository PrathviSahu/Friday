import { motion } from 'framer-motion';
import AnimatedCard from '../../components/Panels/AnimatedCard';
import Clock from '../../components/Clock/Clock';

export default function Dashboard({ onLock }) {
    return (
        <div className="absolute inset-0 w-full h-full flex flex-col justify-between px-8 py-6 pointer-events-auto" style={{ zIndex: 25 }}>
            
            {/* Header Area */}
            <div className="flex justify-between items-center w-full">
                <div className="flex items-center gap-4">
                    <span className="font-orbitron text-[9px] tracking-[0.25em] text-[#00B7FF]/40 uppercase">
                        STARK INDUSTRIES /
                    </span>
                    <button 
                        onClick={onLock}
                        className="border border-[#ff4444]/30 bg-[#ff4444]/5 hover:bg-[#ff4444]/15 px-3 py-1 rounded text-[8px] font-orbitron tracking-widest text-[#ff6666] transition-all uppercase cursor-pointer"
                        style={{ boxShadow: '0 0 6px rgba(255, 68, 68, 0.15)' }}
                    >
                        Secure Console [Lock]
                    </button>
                </div>
                
                <div className="flex items-center gap-6">
                    <div className="font-orbitron text-xs tracking-widest text-[#00B7FF] flex items-center gap-2 drop-shadow-[0_0_8px_rgba(0,183,255,0.4)]">
                        <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" style={{ boxShadow: '0 0 6px #00ff00' }} />
                        CONSOLE LEVEL 4 ACTIVE
                    </div>
                    <Clock />
                </div>
            </div>

            {/* Main panels layout */}
            <div className="flex-1 flex justify-between items-center my-6 gap-6">
                
                {/* Left Side: Trading & Market Overview */}
                <motion.div
                    initial={{ opacity: 0, x: -80, scale: 0.95 }}
                    animate={{ opacity: 1, x: 0, scale: 1 }}
                    transition={{ duration: 1.1, ease: 'easeOut', delay: 0.1 }}
                >
                    <AnimatedCard width={290} height={420}>
                        <div className="flex flex-col gap-3 h-full">
                            <div className="font-orbitron text-[9px] tracking-[0.2em] text-[#00B7FF]/60 border-b border-[#00B7FF]/10 pb-2">
                                MARKET OVERVIEW
                            </div>

                            {/* Stock overview header */}
                            <div className="mt-1">
                                <div className="flex justify-between items-center">
                                    <span className="font-orbitron text-xs text-[#DFFAFF]">AAPL (Apple Inc.)</span>
                                    <span className="text-[10px] text-green-400 font-bold font-orbitron">+2.15 (1.15%)</span>
                                </div>
                                <div className="text-xl font-bold font-orbitron text-[#DFFAFF] mt-0.5">188.42 USD</div>
                            </div>

                            {/* Animated vector line chart */}
                            <div className="w-full h-32 relative bg-cyan-950/20 border border-cyan-800/10 rounded mt-1 overflow-hidden">
                                <svg className="w-full h-full" viewBox="0 0 100 50">
                                    {/* Grid Lines inside chart */}
                                    <line x1="0" y1="12" x2="100" y2="12" stroke="rgba(0, 183, 255, 0.05)" strokeWidth="0.5" />
                                    <line x1="0" y1="25" x2="100" y2="25" stroke="rgba(0, 183, 255, 0.05)" strokeWidth="0.5" />
                                    <line x1="0" y1="38" x2="100" y2="38" stroke="rgba(0, 183, 255, 0.05)" strokeWidth="0.5" />
                                    
                                    {/* Line graph */}
                                    <motion.path
                                        d="M 0 42 Q 15 35 25 38 T 50 18 T 75 22 T 100 8"
                                        fill="none"
                                        stroke="#00D9FF"
                                        strokeWidth="1.5"
                                        initial={{ pathLength: 0 }}
                                        animate={{ pathLength: 1 }}
                                        transition={{ duration: 2.2, ease: 'easeInOut', delay: 0.4 }}
                                        style={{ filter: 'drop-shadow(0 0 4px rgba(0, 217, 255, 0.8))' }}
                                    />
                                    {/* Gradient area under line */}
                                    <path
                                        d="M 0 42 Q 15 35 25 38 T 50 18 T 75 22 T 100 8 L 100 50 L 0 50 Z"
                                        fill="url(#chartGrad)"
                                        opacity="0.12"
                                    />
                                    
                                    <defs>
                                        <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="0%" stopColor="#00D9FF" />
                                            <stop offset="100%" stopColor="transparent" />
                                        </linearGradient>
                                    </defs>
                                </svg>
                            </div>

                            {/* Index status rows */}
                            <div className="space-y-2 mt-2">
                                {[
                                    { name: 'NASDAQ', val: '16,920.58', diff: '+1.13%', col: 'text-green-400' },
                                    { name: 'S&P 500', val: '5,308.15', diff: '+0.85%', col: 'text-green-400' },
                                    { name: 'DOW JONES', val: '39,869.38', diff: '+0.65%', col: 'text-green-400' },
                                ].map((idx, i) => (
                                    <div key={i} className="flex justify-between items-center text-[9px] font-orbitron border-b border-[#00B7FF]/5 pb-1">
                                        <span className="text-[#DFFAFF]/60">{idx.name}</span>
                                        <div className="flex gap-2">
                                            <span className="text-[#DFFAFF]">{idx.val}</span>
                                            <span className={`${idx.col} font-bold`}>{idx.diff}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </AnimatedCard>
                </motion.div>

                {/* Center Core HUD Area */}
                <div className="flex-1 self-stretch flex flex-col justify-between items-center pointer-events-none">
                    {/* Top title during dashboard active */}
                    <motion.div
                        className="text-center"
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.8 }}
                    >
                        <h2 className="font-orbitron text-xs tracking-[0.3em] text-[#00B7FF]/70">TACTICAL OVERVIEW</h2>
                        <div className="w-12 h-px bg-[#00B7FF]/30 mx-auto mt-1" />
                    </motion.div>

                    {/* Centered space holds the floating small orb */}
                    <div className="flex-1" />

                    {/* Dynamic Status Text */}
                    <div className="text-center pb-4">
                        <span className="font-orbitron text-[9px] tracking-[0.2em] text-[#00D9FF] font-bold uppercase drop-shadow-[0_0_6px_#00D9FF]">
                            CORE INTERACTION ONLINE
                        </span>
                    </div>
                </div>

                {/* Right Side: System Monitor & Events */}
                <motion.div
                    initial={{ opacity: 0, x: 80, scale: 0.95 }}
                    animate={{ opacity: 1, x: 0, scale: 1 }}
                    transition={{ duration: 1.1, ease: 'easeOut', delay: 0.1 }}
                >
                    <AnimatedCard width={290} height={420}>
                        <div className="flex flex-col gap-3 h-full justify-between">
                            <div>
                                <div className="font-orbitron text-[9px] tracking-[0.2em] text-[#00B7FF]/60 border-b border-[#00B7FF]/10 pb-2 mb-2">
                                    PORTFOLIO SUMMARY
                                </div>
                                <div className="text-center py-2 bg-cyan-950/10 border border-cyan-800/10 rounded">
                                    <div className="text-xs font-orbitron text-[#DFFAFF]/60 tracking-wider">TOTAL VALUE</div>
                                    <div className="text-lg font-bold font-orbitron text-green-400 mt-0.5">$125,430.75</div>
                                    <div className="text-[8px] font-orbitron text-green-500 mt-0.5">+$2,875.40 (Today)</div>
                                </div>
                            </div>

                            {/* System Resource Indicators */}
                            <div>
                                <div className="font-orbitron text-[8px] tracking-[0.2em] text-[#00B7FF]/40 mb-2">RESOURCES</div>
                                <div className="space-y-3">
                                    {[
                                        { label: 'CPU LOAD', val: '23%', w: '23%', col: 'bg-cyan-400' },
                                        { label: 'MEMORY', val: '41%', w: '41%', col: 'bg-cyan-400' },
                                        { label: 'BATTERY', val: '78%', w: '78%', col: 'bg-green-400' },
                                    ].map((r, i) => (
                                        <div key={i} className="text-[9px] font-orbitron">
                                            <div className="flex justify-between text-[#DFFAFF]/60 mb-1">
                                                <span>{r.label}</span>
                                                <span>{r.val}</span>
                                            </div>
                                            <div className="w-full h-1 bg-[#00B7FF]/10 rounded-full overflow-hidden">
                                                <motion.div 
                                                    className={`h-full ${r.col}`}
                                                    initial={{ width: 0 }}
                                                    animate={{ width: r.w }}
                                                    transition={{ duration: 1.4, ease: 'easeOut', delay: 0.5 }}
                                                />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Upcoming Events */}
                            <div className="border-t border-[#00B7FF]/10 pt-3">
                                <div className="font-orbitron text-[8px] tracking-[0.2em] text-[#00B7FF]/40 mb-2">CALENDAR EVENTS</div>
                                <div className="space-y-2">
                                    <div className="flex gap-2 items-start text-[8px] font-grotesk border-b border-[#00B7FF]/5 pb-1">
                                        <span className="text-cyan-400 font-bold shrink-0">2:00 PM</span>
                                        <span className="text-[#DFFAFF]/80">Team Briefing (Conference Room)</span>
                                    </div>
                                    <div className="flex gap-2 items-start text-[8px] font-grotesk">
                                        <span className="text-cyan-400 font-bold shrink-0">4:30 PM</span>
                                        <span className="text-[#DFFAFF]/80">Project Core Architecture Review</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </AnimatedCard>
                </motion.div>

            </div>

            {/* Bottom Panel */}
            <div className="flex justify-center w-full">
                <div className="border-t border-[#00B7FF]/15 pt-2 w-full text-center">
                    <span className="font-grotesk text-[8px] tracking-[0.3em] text-[#00B7FF]/35 uppercase">
                        STARK CONSOLE LEVEL 4 / ENCRYPTED SECURE FEED
                    </span>
                </div>
            </div>
        </div>
    );
}
