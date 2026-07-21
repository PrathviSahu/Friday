import { motion } from 'framer-motion';
import AnimatedCard from '../Panels/AnimatedCard';
import { useFriday } from '../../context/FridayContext';
import { useEffect, useState, useRef } from 'react';
import { Shield, Wifi, TrendingUp, Database, Fingerprint, Music, Play, Pause, SkipBack, SkipForward, Volume2 } from 'lucide-react';
import { fetchChatText } from '../../api/chatText';

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
    const [spotifyTrack, setSpotifyTrack] = useState({ playing: false, title: '', artist: '' });
    const [volume, setVolume] = useState(50);
    const wrapperRef = useRef(null);

    const handleMediaAction = async (cmd) => {
        try {
            await fetchChatText(cmd, true); // silenceTts = true
            setTimeout(async () => {
                const res = await fetch('http://localhost:8000/api/spotify/current-track');
                if (res.ok) setSpotifyTrack(await res.json());
            }, 500);
        } catch (_) {}
    };

    useEffect(() => {
        const fetchTrack = async () => {
            try {
                const res = await fetch('http://localhost:8000/api/spotify/current-track');
                if (res.ok) {
                    const data = await res.json();
                    setSpotifyTrack(data);
                }
            } catch (_) {}
        };
        fetchTrack();
        const interval = setInterval(fetchTrack, 4000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        const calcShift = () => {
            const max = 320; // debug panel width
            const vw = window.innerWidth;
            const computed = Math.min(max, Math.round(vw * 0.3));
            setShift(showDebug ? computed : 0);
        };

        // Always pin the card to the right side of the viewport, keeping its current vertical position
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
        <AnimatedCard width={260} height={380}>
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

                {/* Spotify Currently Playing Widget */}
                <div className="border-t border-[#00B7FF]/10 pt-2 mt-1">
                    <div className="flex items-center justify-between font-orbitron text-[8px] tracking-[0.2em] text-[#00B7FF]/60 mb-2">
                        <span className="flex items-center gap-1.5"><Music size={10} className="text-[#00B7FF]" /> SPOTIFY FEED</span>
                        <span className={`text-[7px] px-1.5 py-0.5 rounded font-mono ${spotifyTrack.playing ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 'bg-cyan-500/10 text-cyan-400/50'}`}>
                            {spotifyTrack.playing ? 'PLAYING' : spotifyTrack.title ? 'PAUSED' : 'OFFLINE'}
                        </span>
                    </div>

                    <div className="bg-cyan-950/20 border border-[#00B7FF]/15 rounded p-2 text-left space-y-2">
                        {spotifyTrack.title ? (
                            <div>
                                <div className="font-orbitron text-[9px] font-bold text-[#DFFAFF] truncate drop-shadow-[0_0_6px_rgba(0,183,255,0.4)]">
                                    {spotifyTrack.title}
                                </div>
                                <div className="font-grotesk text-[8px] text-[#00B7FF]/70 truncate mt-0.5">
                                    {spotifyTrack.artist || 'Unknown Artist'}
                                </div>
                            </div>
                        ) : (
                            <div className="text-[8px] font-orbitron text-[#DFFAFF]/40 text-center py-1">
                                No active playback
                            </div>
                        )}

                        {/* Playback Control Buttons */}
                        <div className="flex items-center justify-center gap-2 pt-1 border-t border-[#00B7FF]/10">
                            <button
                                onClick={() => handleMediaAction('previous track')}
                                className="p-1 rounded hover:bg-[#00B7FF]/20 text-[#00B7FF] transition-all cursor-pointer"
                                title="Previous Track"
                            >
                                <SkipBack size={12} />
                            </button>
                            <button
                                onClick={() => handleMediaAction(spotifyTrack.playing ? 'pause music' : 'play music')}
                                className="p-1.5 rounded-full bg-[#00B7FF]/20 hover:bg-[#00B7FF]/30 border border-[#00B7FF]/40 text-[#DFFAFF] transition-all cursor-pointer"
                                title={spotifyTrack.playing ? 'Pause' : 'Play'}
                            >
                                {spotifyTrack.playing ? <Pause size={12} /> : <Play size={12} />}
                            </button>
                            <button
                                onClick={() => handleMediaAction('next track')}
                                className="p-1 rounded hover:bg-[#00B7FF]/20 text-[#00B7FF] transition-all cursor-pointer"
                                title="Next Track"
                            >
                                <SkipForward size={12} />
                            </button>
                        </div>

                        {/* Volume Control Bar */}
                        <div className="flex items-center gap-2 pt-1">
                            <Volume2 size={11} className="text-[#00B7FF]/60 shrink-0" />
                            <input
                                type="range"
                                min="0"
                                max="100"
                                value={volume}
                                onChange={(e) => {
                                    const val = Number(e.target.value);
                                    setVolume(val);
                                    handleMediaAction(`volume ${val}%`);
                                }}
                                className="w-full h-1 bg-[#00B7FF]/20 rounded-lg appearance-none cursor-pointer accent-[#00B7FF]"
                            />
                            <span className="font-mono text-[7px] text-[#00B7FF]/70 w-5 text-right">{volume}%</span>
                        </div>
                    </div>
                </div>
            </div>
        </AnimatedCard>
        </div>
    );
}
