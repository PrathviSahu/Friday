import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence, useDragControls, useMotionValue, useSpring } from 'framer-motion';
import {
    Play, Pause, SkipBack, SkipForward,
    Volume2, VolumeX, X, Search,
    Shuffle, Repeat, Repeat1, Heart,
    GripHorizontal, Mic2, ListMusic,
    Maximize2, Plus, ListPlus, Sparkles, Music
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
    const [spotifyTrack, setSpotifyTrack] = useState({
        playing: false, title: '', artist: '', artwork_url: '', position: 0, duration: 180
    });
    const [volume, setVolume] = useState(70);
    const [muted, setMuted] = useState(false);
    const [liked, setLiked] = useState(false);
    const [shuffle, setShuffle] = useState(false);
    const [repeat, setRepeat] = useState(0); // 0=off, 1=all, 2=one
    const [progress, setProgress] = useState(0); // real seconds
    const [songQuery, setSongQuery] = useState('');
    const [searching, setSearching] = useState(false);
    const [showSearch, setShowSearch] = useState(true);
    const [suggestions, setSuggestions] = useState([]);
    const [loadingSuggestions, setLoadingSuggestions] = useState(false);
    const progressBarRef = useRef(null);

    // Create New Playlist Modal State
    const [showCreatePlaylist, setShowCreatePlaylist] = useState(false);
    const [newPlaylistName, setNewPlaylistName] = useState('');
    const [newPlaylistVibe, setNewPlaylistVibe] = useState('🎧 Chill Lo-Fi');
    const [creatingPlaylist, setCreatingPlaylist] = useState(false);
    const [playlistCreatedMsg, setPlaylistCreatedMsg] = useState('');

    // ── 3D Liquid Drag & Motion Controls ──
    const [isDragging, setIsDragging] = useState(false);
    const [transformOrigin, setTransformOrigin] = useState('50% 50%');
    const cardRef = useRef(null);

    const dragControls = useDragControls();
    const rawRotateX = useMotionValue(0);
    const rawRotateY = useMotionValue(0);
    const rotateX = useSpring(rawRotateX, { stiffness: 180, damping: 14, mass: 0.35 });
    const rotateY = useSpring(rawRotateY, { stiffness: 180, damping: 14, mass: 0.35 });

    const handlePointerDownHeader = (e) => {
        if (cardRef.current) {
            const rect = cardRef.current.getBoundingClientRect();
            setTransformOrigin(`${e.clientX - rect.left}px ${e.clientY - rect.top}px`);
        }
        setIsDragging(true);
        dragControls.start(e);
    };

    const handleDrag = (_, info) => {
        const vx = info.velocity.x;
        const vy = info.velocity.y;
        // Balanced tilt sensitivity & 24deg max tilt limit
        const targetTiltX = Math.max(-24, Math.min(24, -vy * 0.045));
        const targetTiltY = Math.max(-24, Math.min(24, vx * 0.045));
        rawRotateX.set(targetTiltX);
        rawRotateY.set(targetTiltY);
    };

    const handleDragEnd = () => {
        setIsDragging(false);
        rawRotateX.set(0);
        rawRotateY.set(0);
    };

    // Live search suggestions as user types (Spotify style)
    useEffect(() => {
        const q = songQuery.trim();
        if (q.length < 2) {
            setSuggestions([]);
            return;
        }
        const timer = setTimeout(async () => {
            setLoadingSuggestions(true);
            try {
                const res = await fetch(`https://itunes.apple.com/search?term=${encodeURIComponent(q)}&entity=song&limit=5`);
                if (res.ok) {
                    const data = await res.json();
                    const items = (data.results || []).map(r => ({
                        id: r.trackId,
                        title: r.trackName,
                        artist: r.artistName,
                        artwork: r.artworkUrl60 || r.artworkUrl100
                    }));
                    setSuggestions(items);
                }
            } catch (_) {}
            setLoadingSuggestions(false);
        }, 220);
        return () => clearTimeout(timer);
    }, [songQuery]);

    const playSuggestion = async (title, artist) => {
        const query = `${title} ${artist}`;
        setSearching(true);
        setSuggestions([]);
        setSongQuery('');
        try {
            await fetchChatText(`play ${query}`, true);
            setTimeout(async () => {
                const res = await fetch('http://localhost:8000/api/spotify/current-track');
                if (res.ok) {
                    const data = await res.json();
                    setSpotifyTrack(data);
                    if (typeof data.position === 'number') setProgress(data.position);
                }
            }, 1000);
        } catch (_) {}
        setTimeout(() => setSearching(false), 1500);
    };

    const totalSecs = spotifyTrack.duration || 180;
    const progressPct = Math.min(100, (progress / totalSecs) * 100);

    const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

    const handleMediaAction = async (cmd) => {
        try {
            await fetchChatText(cmd, true);
            setTimeout(async () => {
                const res = await fetch('http://localhost:8000/api/spotify/current-track');
                if (res.ok) {
                    const data = await res.json();
                    setSpotifyTrack(data);
                    if (typeof data.position === 'number') setProgress(data.position);
                }
            }, 500);
        } catch (_) {}
    };

    const handlePlaySong = async (e) => {
        e.preventDefault();
        const q = songQuery.trim();
        if (!q) return;
        playSuggestion(q, '');
    };

    const handleCreatePlaylist = async (e) => {
        if (e) e.preventDefault();
        const name = newPlaylistName.trim() || newPlaylistVibe.replace(/^[^\s]+\s*/, '');
        if (!name) return;
        setCreatingPlaylist(true);
        try {
            await fetchChatText(`play ${name} playlist`, true);
            setPlaylistCreatedMsg(`✨ Playing '${name}'`);
            setTimeout(() => setPlaylistCreatedMsg(''), 4000);
            setShowCreatePlaylist(false);
            setNewPlaylistName('');
            setTimeout(async () => {
                const res = await fetch('http://localhost:8000/api/spotify/current-track');
                if (res.ok) {
                    const data = await res.json();
                    setSpotifyTrack(data);
                    if (typeof data.position === 'number') setProgress(data.position);
                }
            }, 1000);
        } catch (_) {}
        setCreatingPlaylist(false);
    };

    // Real-time track position tick + periodic synchronization
    useEffect(() => {
        if (!spotifyTrack.playing) return;
        const iv = setInterval(() => {
            setProgress(p => (p >= totalSecs ? 0 : p + 1));
        }, 1000);
        return () => clearInterval(iv);
    }, [spotifyTrack.playing, totalSecs]);

    // Poll current track details from backend
    useEffect(() => {
        const fetchTrack = async () => {
            try {
                const res = await fetch('http://localhost:8000/api/spotify/current-track');
                if (res.ok) {
                    const data = await res.json();
                    setSpotifyTrack(data);
                    if (typeof data.position === 'number') {
                        setProgress(currP => {
                            if (Math.abs(currP - data.position) > 2 || !data.playing) {
                                return data.position;
                            }
                            return currP;
                        });
                    }
                    if (typeof data.volume === 'number') {
                        setVolume(data.volume);
                    }
                }
            } catch (_) {}
        };
        fetchTrack();
        const iv = setInterval(fetchTrack, 2500);
        return () => clearInterval(iv);
    }, []);

    // Handle interactive progress bar click/seek
    const handleProgressClick = async (e) => {
        if (!progressBarRef.current) return;
        const rect = progressBarRef.current.getBoundingClientRect();
        const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        const newSecs = Math.round(pct * totalSecs);
        setProgress(newSecs);
        try {
            await fetch('http://localhost:8000/api/spotify/seek', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ seconds: newSecs })
            });
        } catch (_) {}
    };

    if (!isVisible) {
        return (
            <motion.div
                drag
                dragMomentum={false}
                dragConstraints={{ left: -3000, right: 3000, top: -3000, bottom: 3000 }}
                dragElastic={0.05}
                whileDrag={{ scale: 1.05 }}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                whileHover={{ scale: 1.04 }}
                whileTap={{ scale: 0.96 }}
                onClick={() => setIsVisible(true)}
                style={{
                    position: 'fixed', bottom: 32, right: 40, zIndex: 50,
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '6px 12px', borderRadius: 20,
                    background: '#121212', border: '1px solid #282828',
                    cursor: 'grab', pointerEvents: 'auto', userSelect: 'none',
                    boxShadow: '0 8px 24px rgba(0,0,0,0.6)'
                }}
                className="active:cursor-grabbing"
            >
                <SpotifyIcon size={14} />
                <span
                    style={{
                        fontSize: 11, fontWeight: 600, color: '#b3b3b3',
                        letterSpacing: '0.02em', maxWidth: 160,
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'
                    }}
                >
                    {spotifyTrack.playing ? `${spotifyTrack.title} • ${spotifyTrack.artist}` : 'Now Playing'}
                </span>
            </motion.div>
        );
    }

    return (
        <AnimatePresence>
            <motion.div
                ref={cardRef}
                drag
                dragControls={dragControls}
                dragListener={false}
                dragMomentum={false}
                dragElastic={0.2}
                dragConstraints={{ left: -3000, right: 3000, top: -3000, bottom: 3000 }}
                onDrag={handleDrag}
                onDragEnd={handleDragEnd}
                initial={{ opacity: 0, scale: 0.94 }}
                animate={{ opacity: 1, scale: isDragging ? 1.06 : 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ type: 'spring', stiffness: 320, damping: 32 }}
                style={{
                    position: 'fixed', bottom: 88, right: 40, zIndex: 40,
                    width: 360, borderRadius: 12,
                    background: '#121212', border: '1px solid #282828',
                    boxShadow: isDragging ? '0 45px 100px rgba(0,0,0,0.9), 0 0 0 1px rgba(255,255,255,0.15)' : '0 32px 80px rgba(0,0,0,0.8)',
                    pointerEvents: 'auto', userSelect: 'none', overflow: 'hidden',
                    fontFamily: "'Circular', 'Helvetica Neue', Helvetica, Arial, sans-serif",
                    rotateX,
                    rotateY,
                    transformOrigin,
                    transformStyle: 'preserve-3d',
                    perspective: 1000,
                    willChange: 'transform',
                    backfaceVisibility: 'hidden',
                }}
            >
                {/* ── Top edge & side edge drag handle strips ── */}

                {/* ── Top edge & side edge drag handle strips ── */}
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 8, cursor: 'grab', zIndex: 50 }} />
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', top: 0, bottom: 0, left: 0, width: 8, cursor: 'grab', zIndex: 50 }} />
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', top: 0, bottom: 0, right: 0, width: 8, cursor: 'grab', zIndex: 50 }} />
                <div onPointerDown={handlePointerDownHeader} style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 8, cursor: 'grab', zIndex: 50 }} />

                {/* ── Top bar: drag handle + close ── */}
                <div
                    onPointerDown={handlePointerDownHeader}
                    style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                        padding: '10px 16px 8px', borderBottom: '1px solid #282828',
                        cursor: 'grab', position: 'relative', zIndex: 40
                    }}
                    className="active:cursor-grabbing"
                >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#535353' }}>
                        <GripHorizontal size={13} />
                        <SpotifyIcon size={14} />
                        <span style={{ fontSize: 10, fontWeight: 700, color: '#535353', letterSpacing: '0.12em' }}>SPOTIFY</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }} onPointerDown={(e) => e.stopPropagation()}>
                        <IconBtn icon={ListPlus} size={14} title="Create New Playlist" onClick={() => setShowCreatePlaylist(s => !s)} active={showCreatePlaylist} activeColor="#1DB954" />
                        <IconBtn icon={Search} size={14} title="Search a song" onClick={() => setShowSearch(s => !s)} active={showSearch} activeColor="#1DB954" />
                        <button onClick={() => setIsVisible(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, color: '#535353', display: 'flex' }}
                            onMouseEnter={e => e.currentTarget.style.color = '#b3b3b3'}
                            onMouseLeave={e => e.currentTarget.style.color = '#535353'}>
                            <X size={14} />
                        </button>
                    </div>
                </div>

                {/* ── Toast Banner when playlist is created ── */}
                {playlistCreatedMsg && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        style={{ background: '#1DB954', color: '#000', padding: '6px 16px', fontSize: 11, fontWeight: 700, textAlign: 'center' }}
                    >
                        {playlistCreatedMsg}
                    </motion.div>
                )}

                {/* ── Create New Playlist Drawer Modal ── */}
                <AnimatePresence>
                    {showCreatePlaylist && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            style={{ borderBottom: '1px solid #282828', background: '#181818', padding: '12px 16px', overflow: 'hidden' }}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#1DB954', fontSize: 11, fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                                    <Sparkles size={13} />
                                    <span>Create New Playlist</span>
                                </div>
                                <button onClick={() => setShowCreatePlaylist(false)} style={{ background: 'none', border: 'none', color: '#535353', cursor: 'pointer', padding: 2 }}>
                                    <X size={13} />
                                </button>
                            </div>

                            <form onSubmit={handleCreatePlaylist} style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: '#282828', borderRadius: 8, padding: '6px 12px' }}>
                                    <Music size={13} style={{ color: '#b3b3b3', flexShrink: 0 }} />
                                    <input
                                        type="text"
                                        value={newPlaylistName}
                                        onChange={e => setNewPlaylistName(e.target.value)}
                                        placeholder="Playlist name (e.g. Midnight Beats)..."
                                        style={{ background: 'none', border: 'none', outline: 'none', color: '#fff', fontSize: 12, width: '100%', fontFamily: 'inherit' }}
                                    />
                                </div>

                                <div style={{ fontSize: 10, color: '#b3b3b3', fontWeight: 600, marginTop: 2 }}>
                                    Or Pick a Preset Vibe:
                                </div>

                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                                    {[
                                        '🎧 Chill Lo-Fi',
                                        '⚡ Gym & Hype',
                                        '🕉️ Krishna Bhajans',
                                        '☕ Acoustic Coffee',
                                        '🌃 Bollywood Romance',
                                        '🎸 Indie Rock'
                                    ].map(vibe => (
                                        <button
                                            key={vibe}
                                            type="button"
                                            onClick={() => { setNewPlaylistVibe(vibe); setNewPlaylistName(vibe.replace(/^[^\s]+\s*/, '')); }}
                                            style={{
                                                fontSize: 10, fontWeight: 600, padding: '4px 10px', borderRadius: 12,
                                                background: (newPlaylistVibe === vibe && !newPlaylistName) ? '#1DB954' : '#282828',
                                                color: (newPlaylistVibe === vibe && !newPlaylistName) ? '#000' : '#b3b3b3',
                                                border: 'none', cursor: 'pointer', transition: 'all 0.15s ease'
                                            }}
                                        >
                                            {vibe}
                                        </button>
                                    ))}
                                </div>

                                <motion.button
                                    type="submit"
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.98 }}
                                    disabled={creatingPlaylist}
                                    style={{
                                        marginTop: 4, padding: '8px 14px', borderRadius: 20,
                                        background: '#1DB954', color: '#000', border: 'none',
                                        fontSize: 11, fontWeight: 700, cursor: 'pointer',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6
                                    }}
                                >
                                    <Plus size={14} />
                                    <span>{creatingPlaylist ? 'Creating...' : 'Create & Play Playlist'}</span>
                                </motion.button>
                            </form>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* ── Search bar (Permanent & Prominent) ── */}
                <div style={{ borderBottom: '1px solid #282828', background: '#181818' }}>
                    <form onSubmit={handlePlaySong} style={{ padding: '10px 16px 8px', display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Search size={14} style={{ color: '#1DB954', flexShrink: 0 }} />
                        <input
                            type="text"
                            value={songQuery}
                            onChange={e => setSongQuery(e.target.value)}
                            placeholder={searching ? 'Searching Spotify...' : 'Search & play any song (e.g. Kesariya)...'}
                            style={{
                                background: 'none', border: 'none', outline: 'none',
                                fontSize: 12, color: '#ffffff', width: '100%',
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

                    {/* ── Live Search Suggestions Dropdown (Spotify Style) ── */}
                    {suggestions.length > 0 && (
                        <div style={{ maxHeight: 210, overflowY: 'auto', borderTop: '1px solid #282828', background: '#141414' }}>
                            <div style={{ padding: '6px 16px 2px', fontSize: 10, fontWeight: 700, color: '#1DB954', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                                Spotify Suggestions
                            </div>
                            {suggestions.map((item) => (
                                <div
                                    key={item.id}
                                    onClick={() => playSuggestion(item.title, item.artist)}
                                    style={{
                                        display: 'flex', alignItems: 'center', gap: 10, padding: '8px 16px',
                                        cursor: 'pointer', transition: 'background 0.15s ease'
                                    }}
                                    onMouseEnter={e => e.currentTarget.style.background = '#282828'}
                                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                                >
                                    <img src={item.artwork} alt="" style={{ width: 32, height: 32, borderRadius: 4, objectFit: 'cover', flexShrink: 0 }} />
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                        <div style={{ fontSize: 12, fontWeight: 600, color: '#ffffff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                            {item.title}
                                        </div>
                                        <div style={{ fontSize: 10, color: '#b3b3b3', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                            {item.artist}
                                        </div>
                                    </div>
                                    <button style={{ background: '#1DB954', border: 'none', borderRadius: '50%', width: 24, height: 24, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', flexShrink: 0 }}>
                                        <Play size={10} fill="#000" color="#000" style={{ marginLeft: 1 }} />
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

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
                        <span>-{fmt(Math.max(0, totalSecs - progress))}</span>
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

                {/* ── Volume + extra icons ── */}
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
                            onClick={() => { setMuted(m => !m); handleMediaAction(muted ? `set volume to ${volume}` : 'set volume to 0'); }}
                            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, color: '#b3b3b3', display: 'flex' }}>
                            {(muted || volume === 0) ? <VolumeX size={16} /> : <Volume2 size={16} />}
                        </button>
                        <div style={{ flex: 1, maxWidth: 100, position: 'relative', height: 4, background: '#535353', borderRadius: 2, cursor: 'pointer' }}>
                            <div style={{ width: `${muted ? 0 : volume}%`, height: '100%', background: '#b3b3b3', borderRadius: 2 }} />
                            <input
                                type="range" min="0" max="100" value={muted ? 0 : volume}
                                onChange={e => { setVolume(Number(e.target.value)); setMuted(false); handleMediaAction(`set volume to ${e.target.value}`); }}
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
