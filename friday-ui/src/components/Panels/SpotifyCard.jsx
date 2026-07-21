import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Play, Pause, SkipBack, SkipForward,
    Volume2, VolumeX, X, Search,
    Shuffle, Repeat, Repeat1, Heart,
    GripHorizontal, Mic2, ListMusic,
    Laptop2, Maximize2
} from 'lucide-react';
import { fetchChatText } from '../../api/chatText';

const SpotifyIcon = ({ size = 20 }) => (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="#1DB954">
        <path d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm4.586 14.424a.622.622 0 01-.857.207c-2.348-1.435-5.304-1.76-8.785-.964a.622.622 0 01-.277-1.215c3.809-.87 7.076-.496 9.712 1.115a.622.622 0 01.207.857zm1.223-2.722a.779.779 0 01-1.072.257c-2.687-1.652-6.785-2.131-9.965-1.166a.779.779 0 01-.973-.519.779.779 0 01.519-.972c3.632-1.102 8.147-.568 11.234 1.328a.779.779 0 01.257 1.072zm.105-2.835c-3.223-1.914-8.54-2.09-11.618-1.156a.935.935 0 11-.543-1.79c3.532-1.073 9.404-.866 13.115 1.337a.935.935 0 01-.954 1.609z" />
    </svg>
);

function IconBtn({ icon: Icon, size = 16, color = '#b3b3b3', activeColor = '#fff', active = false, onClick, title }) {
    const [hovered, setHovered] = useState(false);
    return (
        <button
            onClick={onClick}
            title={title}
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
            style={{
                background: 'none', border: 'none', padding: 4, cursor: 'pointer',
                color: active ? activeColor : hovered ? '#fff' : color,
                transition: 'color 0.15s',
                display: 'flex', alignItems: 'center'
            }}
        >
            <Icon size={size} fill={active ? activeColor : 'none'} />
        </button>
    );
}

export default function SpotifyCard() {
    const [isVisible, setIsVisible] = useState(false);
    const [spotifyTrack, setSpotifyTrack] = useState({ playing: false, title: '', artist: '', artwork_url: '' });
    const [volume, setVolume] = useState(65);
    const [muted, setMuted] = useState(false);
    const [liked, setLiked] = useState(false);
    const [shuffle, setShuffle] = useState(false);
    const [repeat, setRepeat] = useState(0); // 0=off, 1=all, 2=one
    const [progress, setProgress] = useState(14); // seconds
    const totalSecs = 171; // 2:51 mock
    const progressPct = Math.min(100, (progress / totalSecs) * 100);
    const [songQuery, setSongQuery] = useState('');
    const [searching, setSearching] = useState(false);
    const [showSearch, setShowSearch] = useState(false);
    const progressBarRef = useRef(null);

    const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

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
        setShowSearch(false);
        try {
            await fetchChatText(`play ${q}`, true);
            setTimeout(async () => {
                const res = await fetch('http://localhost:8000/api/spotify/current-track');
                if (res.ok) setSpotifyTrack(await res.json());
            }, 1200);
        } catch (_) {}
        setTimeout(() => setSearching(false), 1500);
    };

    // Mock progress tick
    useEffect(() => {
        if (!spotifyTrack.playing) return;
        const iv = setInterval(() => setProgress(p => p >= totalSecs ? 0 : p + 1), 1000);
        return () => clearInterval(iv);
    }, [spotifyTrack.playing]);

    // Poll track
    useEffect(() => {
        const fetchTrack = async () => {
            try {
                const res = await fetch('http://localhost:8000/api/spotify/current-track');
                if (res.ok) setSpotifyTrack(await res.json());
            } catch (_) {}
        };
        fetchTrack();
        const iv = setInterval(fetchTrack, 4000);
        return () => clearInterval(iv);
    }, []);

    const handleProgressClick = (e) => {
        const rect = progressBarRef.current.getBoundingClientRect();
        const pct = (e.clientX - rect.left) / rect.width;
        setProgress(Math.round(pct * totalSecs));
    };

    if (!isVisible) {
        return (
            <motion.div
                drag
                dragConstraints={{ left: -1000, right: 200, top: -800, bottom: 200 }}
                dragElastic={0.1}
                whileDrag={{ scale: 1.05 }}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                whileHover={{ scale: 1.04 }}
                whileTap={{ scale: 0.96 }}
                onClick={() => setIsVisible(true)}
                style={{
                    position: 'fixed', bottom: 32, right: 40, zIndex: 50,
                    display: 'flex', alignItems: 'center', gap: 8,
                    padding: '8px 16px', borderRadius: 24,
                    background: '#121212', border: '1px solid #282828',
                    cursor: 'grab', pointerEvents: 'auto', userSelect: 'none',
                    boxShadow: '0 8px 24px rgba(0,0,0,0.6)'
                }}
                className="active:cursor-grabbing"
            >
                <SpotifyIcon size={16} />
                <span style={{ fontSize: 12, fontWeight: 600, color: '#b3b3b3', letterSpacing: '0.04em' }}>Now Playing</span>
            </motion.div>
        );
    }

    return (
        <AnimatePresence>
            <motion.div
                drag
                dragConstraints={{ left: -600, right: 80, top: -600, bottom: 80 }}
                dragElastic={0.07}
                initial={{ opacity: 0, y: 24, scale: 0.94 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 16, scale: 0.9 }}
                transition={{ type: 'spring', stiffness: 320, damping: 32 }}
                style={{
                    position: 'fixed', bottom: 88, right: 40, zIndex: 40,
                    width: 360, borderRadius: 12,
                    background: '#121212', border: '1px solid #282828',
                    boxShadow: '0 32px 80px rgba(0,0,0,0.8)',
                    pointerEvents: 'auto', userSelect: 'none', overflow: 'hidden',
                    fontFamily: "'Circular', 'Helvetica Neue', Helvetica, Arial, sans-serif"
                }}
            >
                {/* ── Top bar: drag + close ── */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 16px 8px', borderBottom: '1px solid #282828' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'grab', color: '#535353' }}>
                        <GripHorizontal size={13} />
                        <SpotifyIcon size={14} />
                        <span style={{ fontSize: 10, fontWeight: 700, color: '#535353', letterSpacing: '0.12em' }}>SPOTIFY</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <IconBtn icon={Search} size={14} title="Search a song" onClick={() => setShowSearch(s => !s)} active={showSearch} activeColor="#1DB954" />
                        <button onClick={() => setIsVisible(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, color: '#535353', display: 'flex' }}
                            onMouseEnter={e => e.currentTarget.style.color = '#b3b3b3'}
                            onMouseLeave={e => e.currentTarget.style.color = '#535353'}>
                            <X size={14} />
                        </button>
                    </div>
                </div>

                {/* ── Search bar (togglable) ── */}
                <AnimatePresence>
                    {showSearch && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            style={{ overflow: 'hidden', borderBottom: '1px solid #282828' }}
                        >
                            <form onSubmit={handlePlaySong} style={{ padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 8, background: '#181818' }}>
                                <Search size={14} style={{ color: '#535353', flexShrink: 0 }} />
                                <input
                                    autoFocus
                                    type="text"
                                    value={songQuery}
                                    onChange={e => setSongQuery(e.target.value)}
                                    placeholder={searching ? 'Searching…' : 'What do you want to play?'}
                                    style={{
                                        background: 'none', border: 'none', outline: 'none',
                                        fontSize: 13, color: '#ffffff', width: '100%',
                                        fontFamily: 'inherit'
                                    }}
                                />
                                {songQuery.trim() && (
                                    <motion.button type="submit" initial={{ scale: 0 }} animate={{ scale: 1 }}
                                        style={{ background: '#1DB954', border: 'none', borderRadius: '50%', width: 26, height: 26, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', flexShrink: 0 }}>
                                        <Play size={11} fill="#000" color="#000" style={{ marginLeft: 1 }} />
                                    </motion.button>
                                )}
                            </form>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* ── Album art + Track info + Heart ── */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '14px 16px 0' }}>
                    {/* Album art */}
                    <div style={{
                        width: 56, height: 56, borderRadius: 6, flexShrink: 0,
                        background: 'linear-gradient(135deg, #282828 0%, #1a1a1a 100%)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        boxShadow: spotifyTrack.playing ? '0 4px 20px rgba(29,185,84,0.35)' : '0 2px 8px rgba(0,0,0,0.5)',
                        transition: 'box-shadow 0.5s ease',
                        overflow: 'hidden', position: 'relative'
                    }}>
                        {spotifyTrack.artwork_url ? (
                            <motion.img
                                key={spotifyTrack.artwork_url}
                                src={spotifyTrack.artwork_url}
                                alt="Album art"
                                initial={{ opacity: 0, scale: 1.05 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ duration: 0.4 }}
                                style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 6 }}
                            />
                        ) : (
                            <SpotifyIcon size={24} />
                        )}
                    </div>

                    {/* Track text */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 14, fontWeight: 700, color: '#ffffff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', letterSpacing: '-0.01em' }}>
                            {spotifyTrack.title || 'Nothing playing'}
                        </div>
                        <div style={{ fontSize: 12, color: '#b3b3b3', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginTop: 2 }}>
                            {spotifyTrack.artist || (spotifyTrack.title ? '' : 'Search or use voice to play')}
                        </div>
                    </div>

                    {/* Heart */}
                    <button onClick={() => setLiked(l => !l)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 6, flexShrink: 0, display: 'flex', alignItems: 'center' }}>
                        <Heart size={18} fill={liked ? '#1DB954' : 'none'} style={{ color: liked ? '#1DB954' : '#535353', transition: 'color 0.2s' }} />
                    </button>
                </div>

                {/* ── Progress bar ── */}
                <div style={{ padding: '14px 16px 0' }}>
                    <div
                        ref={progressBarRef}
                        onClick={handleProgressClick}
                        style={{ height: 4, background: '#535353', borderRadius: 2, cursor: 'pointer', position: 'relative', marginBottom: 4 }}
                        className="group"
                    >
                        <div style={{ width: `${progressPct}%`, height: '100%', background: '#1DB954', borderRadius: 2, position: 'relative', transition: 'background 0.2s' }}>
                            <div style={{
                                position: 'absolute', right: -5, top: '50%', transform: 'translateY(-50%)',
                                width: 12, height: 12, borderRadius: '50%', background: '#fff',
                                opacity: 0, transition: 'opacity 0.15s', pointerEvents: 'none'
                            }} className="scrubber-dot" />
                        </div>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#b3b3b3', fontVariantNumeric: 'tabular-nums' }}>
                        <span>{fmt(progress)}</span>
                        <span>-{fmt(totalSecs - progress)}</span>
                    </div>
                </div>

                {/* ── Playback Controls (Spotify bottom bar layout) ── */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, padding: '10px 16px 6px' }}>
                    {/* Shuffle */}
                    <button onClick={() => { setShuffle(s => !s); handleMediaAction('shuffle'); }}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 6, color: shuffle ? '#1DB954' : '#b3b3b3', display: 'flex', alignItems: 'center', position: 'relative', transition: 'color 0.15s' }}>
                        <Shuffle size={18} />
                        {shuffle && <span style={{ position: 'absolute', bottom: 2, left: '50%', transform: 'translateX(-50%)', width: 3, height: 3, borderRadius: '50%', background: '#1DB954' }} />}
                    </button>

                    {/* Prev */}
                    <motion.button whileTap={{ scale: 0.9 }} onClick={() => handleMediaAction('previous track')}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 6, color: '#b3b3b3', display: 'flex', transition: 'color 0.15s' }}
                        onMouseEnter={e => e.currentTarget.style.color = '#fff'}
                        onMouseLeave={e => e.currentTarget.style.color = '#b3b3b3'}>
                        <SkipBack size={20} fill="currentColor" />
                    </motion.button>

                    {/* Play / Pause */}
                    <motion.button
                        whileHover={{ scale: 1.06 }} whileTap={{ scale: 0.94 }}
                        onClick={() => handleMediaAction(spotifyTrack.playing ? 'pause music' : 'play music')}
                        style={{
                            width: 40, height: 40, borderRadius: '50%', background: '#ffffff',
                            border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                            boxShadow: '0 4px 14px rgba(0,0,0,0.5)', flexShrink: 0
                        }}
                    >
                        {spotifyTrack.playing
                            ? <Pause size={18} fill="#121212" color="#121212" />
                            : <Play size={18} fill="#121212" color="#121212" style={{ marginLeft: 2 }} />}
                    </motion.button>

                    {/* Next */}
                    <motion.button whileTap={{ scale: 0.9 }} onClick={() => handleMediaAction('next track')}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 6, color: '#b3b3b3', display: 'flex', transition: 'color 0.15s' }}
                        onMouseEnter={e => e.currentTarget.style.color = '#fff'}
                        onMouseLeave={e => e.currentTarget.style.color = '#b3b3b3'}>
                        <SkipForward size={20} fill="currentColor" />
                    </motion.button>

                    {/* Repeat */}
                    <button onClick={() => setRepeat(r => (r + 1) % 3)}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 6, display: 'flex', alignItems: 'center', position: 'relative', color: repeat > 0 ? '#1DB954' : '#b3b3b3', transition: 'color 0.15s' }}>
                        {repeat === 2 ? <Repeat1 size={18} /> : <Repeat size={18} />}
                        {repeat > 0 && <span style={{ position: 'absolute', bottom: 2, left: '50%', transform: 'translateX(-50%)', width: 3, height: 3, borderRadius: '50%', background: '#1DB954' }} />}
                    </button>
                </div>

                {/* ── Volume + extra icons (like Spotify's bar) ── */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 16px 14px', gap: 8 }}>
                    {/* Left extras */}
                    <div style={{ display: 'flex', gap: 2 }}>
                        <button style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, color: '#535353', display: 'flex' }}
                            onMouseEnter={e => e.currentTarget.style.color = '#b3b3b3'}
                            onMouseLeave={e => e.currentTarget.style.color = '#535353'}
                            title="Lyrics">
                            <Mic2 size={15} />
                        </button>
                        <button style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, color: '#535353', display: 'flex' }}
                            onMouseEnter={e => e.currentTarget.style.color = '#b3b3b3'}
                            onMouseLeave={e => e.currentTarget.style.color = '#535353'}
                            title="Queue">
                            <ListMusic size={15} />
                        </button>
                    </div>

                    {/* Volume control */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, flex: 1, justifyContent: 'flex-end' }}>
                        <button
                            onClick={() => { setMuted(m => !m); handleMediaAction(muted ? `volume ${volume}%` : 'volume 0%'); }}
                            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, color: '#b3b3b3', display: 'flex' }}>
                            {(muted || volume === 0) ? <VolumeX size={16} /> : <Volume2 size={16} />}
                        </button>
                        <div style={{ flex: 1, maxWidth: 100, position: 'relative', height: 4, background: '#535353', borderRadius: 2, cursor: 'pointer' }}>
                            <div style={{ width: `${muted ? 0 : volume}%`, height: '100%', background: '#b3b3b3', borderRadius: 2 }} />
                            <input
                                type="range" min="0" max="100" value={muted ? 0 : volume}
                                onChange={e => { setVolume(Number(e.target.value)); setMuted(false); handleMediaAction(`volume ${e.target.value}%`); }}
                                style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: 0, cursor: 'pointer', margin: 0 }}
                            />
                        </div>
                    </div>

                    {/* Expand */}
                    <button style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, color: '#535353', display: 'flex' }}
                        onMouseEnter={e => e.currentTarget.style.color = '#b3b3b3'}
                        onMouseLeave={e => e.currentTarget.style.color = '#535353'}
                        title="Full screen">
                        <Maximize2 size={14} />
                    </button>
                </div>
            </motion.div>
        </AnimatePresence>
    );
}
