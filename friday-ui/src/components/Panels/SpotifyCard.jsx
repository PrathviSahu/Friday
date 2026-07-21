import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Music, Play, Pause, SkipBack, SkipForward, Volume2, Move, X, Search } from 'lucide-react';
import { fetchChatText } from '../../api/chatText';

export default function SpotifyCard() {
    const [isVisible, setIsVisible] = useState(true);
    const [spotifyTrack, setSpotifyTrack] = useState({ playing: false, title: '', artist: '' });
    const [volume, setVolume] = useState(50);
    const [songQuery, setSongQuery] = useState('');
    const [searching, setSearching] = useState(false);
    const inputRef = useRef(null);

    const handleMediaAction = async (cmd) => {
        try {
            await fetchChatText(cmd, true);
            setTimeout(async () => {
                const res = await fetch('http://localhost:8000/api/spotify/current-track');
                if (res.ok) setSpotifyTrack(await res.json());
            }, 600);
        } catch (_) {}
    };

    const handlePlaySong = async (e) => {
        e.preventDefault();
        const q = songQuery.trim();
        if (!q) return;
        setSearching(true);
        setSongQuery('');
        try {
            await fetchChatText(`play ${q}`, true);
            setTimeout(async () => {
                const res = await fetch('http://localhost:8000/api/spotify/current-track');
                if (res.ok) setSpotifyTrack(await res.json());
            }, 1200);
        } catch (_) {}
        setTimeout(() => setSearching(false), 1500);
    };

    useEffect(() => {
        const fetchTrack = async () => {
            try {
                const res = await fetch('http://localhost:8000/api/spotify/current-track');
                if (res.ok) setSpotifyTrack(await res.json());
            } catch (_) {}
        };
        fetchTrack();
        const interval = setInterval(fetchTrack, 4000);
        return () => clearInterval(interval);
    }, []);

    if (!isVisible) {
        return (
            <motion.button
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={() => setIsVisible(true)}
                className="fixed bottom-6 right-6 z-50 p-2.5 rounded-full bg-[#001018]/90 border border-[#00B7FF]/50 text-[#00B7FF] shadow-[0_0_18px_rgba(0,183,255,0.4)] cursor-pointer flex items-center gap-1.5 font-orbitron text-[9px] tracking-widest pointer-events-auto"
            >
                <Music size={14} className="animate-pulse" />
                <span>SPOTIFY</span>
            </motion.button>
        );
    }

    return (
        <AnimatePresence>
            <motion.div
                drag
                dragConstraints={{ left: -500, right: 100, top: -500, bottom: 100 }}
                dragElastic={0.12}
                initial={{ opacity: 0, y: 20, scale: 0.92 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, scale: 0.85, y: 10 }}
                className="fixed bottom-20 right-6 z-40 w-60 rounded-2xl border border-[#00B7FF]/35 bg-[#000f1a]/92 p-3 backdrop-blur-xl shadow-[0_0_22px_rgba(0,183,255,0.22)] cursor-grab active:cursor-grabbing pointer-events-auto select-none"
            >
                {/* ── Header ── */}
                <div className="flex items-center justify-between pb-1.5 border-b border-[#00B7FF]/15 mb-2">
                    <div className="flex items-center gap-1.5 font-orbitron text-[9px] tracking-[0.18em] text-[#00B7FF]">
                        <Move size={10} className="text-[#00B7FF]/50" />
                        <Music size={12} className="text-[#00B7FF] animate-pulse" />
                        <span>SPOTIFY</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <span className={`text-[7px] px-1.5 py-0.5 rounded-full font-mono uppercase tracking-wider ${
                            spotifyTrack.playing
                                ? 'bg-green-500/20 text-green-400 border border-green-500/40 shadow-[0_0_6px_rgba(34,197,94,0.25)]'
                                : 'bg-cyan-500/10 text-cyan-400/60 border border-cyan-500/20'
                        }`}>
                            {spotifyTrack.playing ? '▶ LIVE' : spotifyTrack.title ? '⏸ PAUSED' : '— OFF'}
                        </span>
                        <button
                            onClick={() => setIsVisible(false)}
                            className="p-0.5 rounded-full hover:bg-red-500/20 text-[#00B7FF]/50 hover:text-red-400 transition-colors cursor-pointer"
                        >
                            <X size={12} />
                        </button>
                    </div>
                </div>

                {/* ── Track Info ── */}
                <div className="bg-[#001520]/60 border border-[#00B7FF]/15 rounded-lg px-2.5 py-2 mb-2 relative overflow-hidden">
                    <div className={`absolute top-0 left-0 w-full h-[1.5px] ${
                        spotifyTrack.playing
                            ? 'bg-gradient-to-r from-green-500 via-[#00B7FF] to-green-500 animate-pulse'
                            : 'bg-[#00B7FF]/15'
                    }`} />
                    {spotifyTrack.title ? (
                        <>
                            <div className="font-orbitron text-[10px] font-bold text-[#DFFAFF] truncate drop-shadow-[0_0_6px_rgba(0,183,255,0.4)]">
                                {spotifyTrack.title}
                            </div>
                            <div className="font-grotesk text-[9px] text-[#00B7FF]/70 truncate mt-0.5">
                                {spotifyTrack.artist || 'Unknown Artist'}
                            </div>
                        </>
                    ) : (
                        <div className="text-[9px] font-orbitron text-[#DFFAFF]/35 text-center py-1">
                            No active playback
                        </div>
                    )}
                </div>

                {/* ── Playback Controls ── */}
                <div className="flex items-center justify-evenly py-1 mb-2">
                    <motion.button whileHover={{ scale: 1.18 }} whileTap={{ scale: 0.88 }}
                        onClick={() => handleMediaAction('previous track')}
                        className="p-1.5 rounded-lg bg-[#00B7FF]/10 hover:bg-[#00B7FF]/22 border border-[#00B7FF]/20 text-[#00B7FF] transition-all cursor-pointer">
                        <SkipBack size={12} />
                    </motion.button>

                    <motion.button whileHover={{ scale: 1.15 }} whileTap={{ scale: 0.88 }}
                        onClick={() => handleMediaAction(spotifyTrack.playing ? 'pause music' : 'play music')}
                        className="p-2.5 rounded-full bg-gradient-to-r from-[#00B7FF]/35 to-[#00E5FF]/35 hover:from-[#00B7FF]/55 hover:to-[#00E5FF]/55 border border-[#00B7FF]/55 text-[#DFFAFF] transition-all cursor-pointer shadow-[0_0_14px_rgba(0,183,255,0.45)]">
                        {spotifyTrack.playing ? <Pause size={14} /> : <Play size={14} />}
                    </motion.button>

                    <motion.button whileHover={{ scale: 1.18 }} whileTap={{ scale: 0.88 }}
                        onClick={() => handleMediaAction('next track')}
                        className="p-1.5 rounded-lg bg-[#00B7FF]/10 hover:bg-[#00B7FF]/22 border border-[#00B7FF]/20 text-[#00B7FF] transition-all cursor-pointer">
                        <SkipForward size={12} />
                    </motion.button>
                </div>

                {/* ── Volume Slider ── */}
                <div className="flex items-center gap-1.5 bg-[#001520]/50 border border-[#00B7FF]/12 rounded-lg px-2 py-1.5 mb-2">
                    <Volume2 size={11} className="text-[#00B7FF]/60 shrink-0" />
                    <input
                        type="range" min="0" max="100" value={volume}
                        onChange={(e) => {
                            const val = Number(e.target.value);
                            setVolume(val);
                            handleMediaAction(`volume ${val}%`);
                        }}
                        className="w-full h-0.5 bg-[#00B7FF]/20 rounded-lg appearance-none cursor-pointer accent-[#00B7FF]"
                    />
                    <span className="font-mono text-[8px] text-[#00B7FF] w-5 text-right">{volume}%</span>
                </div>

                {/* ── Song Search Line ── */}
                <form onSubmit={handlePlaySong} className="flex items-center gap-1.5 relative">
                    <div className="flex-1 flex items-center bg-[#001520]/60 border border-[#00B7FF]/20 rounded-lg px-2 py-1 gap-1.5 focus-within:border-[#00B7FF]/60 focus-within:shadow-[0_0_8px_rgba(0,183,255,0.25)] transition-all">
                        <Search size={10} className="text-[#00B7FF]/50 shrink-0" />
                        <input
                            ref={inputRef}
                            type="text"
                            value={songQuery}
                            onChange={(e) => setSongQuery(e.target.value)}
                            placeholder={searching ? 'Searching...' : 'Play a song...'}
                            disabled={searching}
                            className="bg-transparent text-[9px] font-grotesk text-[#DFFAFF] placeholder-[#DFFAFF]/30 outline-none w-full cursor-text"
                        />
                    </div>
                    <motion.button
                        type="submit"
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        disabled={!songQuery.trim() || searching}
                        className="p-1.5 rounded-lg bg-[#00B7FF]/20 hover:bg-[#00B7FF]/40 border border-[#00B7FF]/40 text-[#00B7FF] transition-all cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                        <Play size={11} />
                    </motion.button>
                </form>
            </motion.div>
        </AnimatePresence>
    );
}
