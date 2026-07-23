import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Sliders, Maximize2, X, TrendingUp, BarChart2, Save, Undo, Redo, Plus, Minus, Mic, MicOff, Calculator } from 'lucide-react';
import { useFriday } from '../../context/FridayContext';
import { stopSpeaking } from '../../services/ttsService';
import ProfessionalChart from './components/ProfessionalChart';
import CustomWatchlist from './components/Watchlist';

const TIMEFRAMES = [
    { label: '1m', value: '1' },
    { label: '3m', value: '3' },
    { label: '5m', value: '5' },
    { label: '15m', value: '15' },
    { label: '30m', value: '30' },
    { label: '1h', value: '60' },
    { label: '4h', value: '240' },
    { label: '1D', value: 'D' },
    { label: '1W', value: 'W' },
];

export default function QuantumTradingWorkstation({ isMinimized = false, onMinimize, onRestore, onClose }) {
    const { micEnabled, setMicEnabled } = useFriday();
    const [selectedSymbol, setSelectedSymbol] = useState('FX:EURUSD');
    const [selectedInterval, setSelectedInterval] = useState('5');
    const [showSymbolSearchModal, setShowSymbolSearchModal] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [layoutGrid, setLayoutGrid] = useState('single'); // 'single' | 'dual' | 'quad'
    const [saveStatus, setSaveStatus] = useState('saved'); // 'saved' | 'saving' | 'error'
    const [isFullscreen, setIsFullscreen] = useState(false);

    // Risk-Reward Lot Size Calculator State
    const [showRiskCalculatorModal, setShowRiskCalculatorModal] = useState(false);
    const [accountBalance, setAccountBalance] = useState(10000);
    const [riskPercent, setRiskPercent] = useState(1.0);
    const [stopPips, setStopPips] = useState(15);

    // Load drawings & chart layout from SQLite DB on symbol change
    React.useEffect(() => {
        const loadChartFromDb = async () => {
            try {
                const res = await fetch(`http://localhost:8000/api/trading/chart-db?symbol=${encodeURIComponent(selectedSymbol)}`);
                if (res.ok) {
                    const data = await res.json();
                    if (data.drawings_data && Object.keys(data.drawings_data).length > 0) {
                        Object.entries(data.drawings_data).forEach(([key, val]) => {
                            try { localStorage.setItem(key, val); } catch (_) {}
                        });
                        console.log(`[Chart DB] Restored drawings for ${selectedSymbol} from SQLite DB`);
                    }
                }
            } catch (_) {}
        };
        loadChartFromDb();
    }, [selectedSymbol]);

    // Save chart drawings & layout to SQLite database
    const saveChartToDb = async () => {
        setSaveStatus('saving');
        try {
            const drawingsObj = {};
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key && (key.includes('tradingview') || key.includes('tv_') || key.includes('drawing'))) {
                    drawingsObj[key] = localStorage.getItem(key);
                }
            }

            const res = await fetch('http://localhost:8000/api/trading/chart-db', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbol: selectedSymbol, drawings_data: drawingsObj }),
            });

            if (res.ok) {
                setSaveStatus('saved');
            } else {
                setSaveStatus('error');
            }
        } catch (err) {
            console.warn('[Chart DB] Auto-save error:', err);
            setSaveStatus('error');
        }
    };

    // Auto-Save drawings & chart layout to SQLite DB silently every 5 seconds
    React.useEffect(() => {
        const iv = setInterval(saveChartToDb, 5000);
        return () => clearInterval(iv);
    }, [selectedSymbol]);

    const toggleMicSilence = () => {
        if (micEnabled) {
            stopSpeaking();
            setMicEnabled(false);
        } else {
            setMicEnabled(true);
        }
    };

    const toggleFullscreen = () => {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen?.();
            setIsFullscreen(true);
        } else {
            document.exitFullscreen?.();
            setIsFullscreen(false);
        }
    };

    const handleCustomSymbolSearch = (e) => {
        e.preventDefault();
        const sym = searchQuery.trim().toUpperCase();
        if (!sym) return;
        const formatted = sym.includes(':') ? sym : `FX:${sym}`;
        setSelectedSymbol(formatted);
        setSearchQuery('');
        setShowSymbolSearchModal(false);
    };

    // ⚡ FLOATING MINI TRADING DOCK WIDGET WHEN MINIMIZED:
    // Keeps chart mounted in DOM background while showing compact control bar in bottom corner
    if (isMinimized) {
        return (
            <motion.div
                initial={{ opacity: 0, y: 20, scale: 0.9 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 20, scale: 0.9 }}
                className="fixed bottom-5 right-5 z-50 bg-[#1e222d]/95 border border-[#2a2e39] rounded-2xl shadow-2xl p-2.5 flex items-center gap-3 select-none text-slate-100 font-sans backdrop-blur-md"
            >
                {/* Active Ticker Badge */}
                <div className="flex items-center gap-2 px-2.5 py-1 rounded-xl bg-[#131722] border border-[#2a2e39]">
                    <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_8px_#00B7FF]" />
                    <span className="font-mono text-xs font-bold text-white tracking-wide">
                        {selectedSymbol.replace(/^.*:/, '')}
                    </span>
                    <span className="text-[10px] font-mono text-cyan-300 font-semibold px-1.5 py-0.5 rounded bg-cyan-500/20 uppercase border border-cyan-500/30">
                        {selectedInterval}m
                    </span>
                </div>

                {/* Mic Silence / Shut Up Toggle Icon-Only Button */}
                <button
                    onClick={toggleMicSilence}
                    className={`p-2 rounded-xl border text-xs font-semibold transition-all cursor-pointer ${
                        micEnabled
                            ? 'bg-[#131722] text-emerald-400 border-[#2a2e39] hover:bg-[#2a2e39]'
                            : 'bg-rose-500/20 text-rose-400 border-rose-500/40 hover:bg-rose-500/30'
                    }`}
                    title={micEnabled ? 'Mute FRIDAY Mic' : 'Unmute FRIDAY Mic'}
                >
                    {micEnabled ? <Mic size={15} /> : <MicOff size={15} />}
                </button>

                {/* Restore Fullscreen Workstation Button */}
                <button
                    onClick={onRestore}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#2962ff] hover:bg-[#1e54e4] text-white text-xs font-bold transition-all cursor-pointer shadow-lg"
                >
                    <Maximize2 size={13} />
                    <span>Restore Trading</span>
                </button>

                {/* Exit Button */}
                <button
                    onClick={onClose}
                    className="p-1.5 rounded-lg hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 transition-all cursor-pointer"
                    title="Exit Trading Station"
                >
                    <X size={15} />
                </button>
            </motion.div>
        );
    }

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.02 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="fixed inset-0 z-50 flex flex-col bg-[#131722] text-[#d1d4dc] font-sans select-none overflow-hidden"
        >
            {/* Authentic TradingView Top Header Bar */}
            <header className="h-13 bg-[#1e222d] border-b border-[#2a2e39] px-4 flex items-center justify-between z-40">
                {/* Left Controls: Symbol Search Button + Timeframe Selector */}
                <div className="flex items-center gap-3">
                    {/* TradingView Brand Indicator */}
                    <div className="flex items-center gap-2 pr-3 border-r border-[#2a2e39]">
                        <div className="w-6 h-6 rounded-md bg-[#2962ff] flex items-center justify-center font-bold text-white text-xs shadow-sm">
                            TV
                        </div>
                        <span className="font-mono text-xs font-bold text-slate-200 tracking-wider hidden sm:inline">
                            F.R.I.D.A.Y. PRO
                        </span>
                    </div>

                    {/* Symbol Search Button (TradingView Style) */}
                    <button
                        onClick={() => setShowSymbolSearchModal(true)}
                        className="flex items-center gap-2.5 px-3.5 py-1.5 rounded-lg bg-[#2a2e39]/80 hover:bg-[#363a45] text-white text-xs font-semibold border border-[#363a45] transition-all cursor-pointer shadow-sm"
                    >
                        <Search className="w-4 h-4 text-[#2962ff]" />
                        <span className="font-bold tracking-wide">{selectedSymbol.replace(/^.*:/, '')}</span>
                        <span className="text-[10px] text-slate-400 font-mono hidden md:inline ml-1">
                            {selectedSymbol}
                        </span>
                    </button>

                    {/* Timeframe Selector Bar */}
                    <div className="flex items-center gap-1 pl-3 border-l border-[#2a2e39]">
                        {TIMEFRAMES.map((tf) => (
                            <button
                                key={tf.value}
                                onClick={() => setSelectedInterval(tf.value)}
                                className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                                    selectedInterval === tf.value
                                        ? 'bg-[#2962ff] text-white shadow-md'
                                        : 'text-slate-400 hover:text-slate-100 hover:bg-[#2a2e39]'
                                }`}
                            >
                                {tf.label}
                            </button>
                        ))}
                    </div>

                    {/* Indicators Button */}
                    <div className="hidden lg:flex items-center gap-1 pl-3 border-l border-[#2a2e39]">
                        <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#2a2e39]/60 hover:bg-[#2a2e39] text-slate-300 text-xs font-semibold cursor-pointer border border-[#363a45]/50 transition-all">
                            <span className="font-serif italic font-bold text-[#2962ff]">fx</span>
                            <span>Indicators</span>
                        </button>
                    </div>

                    </div>

                {/* Right Action Tools: Multi-Chart Selector, Mic Silence, Minimize, Fullscreen, Exit */}
                <div className="flex items-center gap-2.5">
                    {/* Multi-Chart Grid Toggle Selector */}
                    <div className="flex items-center gap-1 bg-[#1a1e29] p-1 rounded-lg border border-[#2a2e39] font-mono">
                        <button
                            onClick={() => setLayoutGrid('single')}
                            className={`px-2 py-0.5 rounded text-[10px] font-bold transition-all cursor-pointer ${
                                layoutGrid === 'single'
                                    ? 'bg-[#2962ff] text-white shadow-sm'
                                    : 'text-slate-400 hover:text-slate-200'
                            }`}
                            title="Single Chart View (1x1)"
                        >
                            1x1
                        </button>
                        <button
                            onClick={() => setLayoutGrid('dual')}
                            className={`px-2 py-0.5 rounded text-[10px] font-bold transition-all cursor-pointer ${
                                layoutGrid === 'dual'
                                    ? 'bg-[#2962ff] text-white shadow-sm'
                                    : 'text-slate-400 hover:text-slate-200'
                            }`}
                            title="2x1 Dual Split View"
                        >
                            2x1
                        </button>
                        <button
                            onClick={() => setLayoutGrid('quad')}
                            className={`px-2 py-0.5 rounded text-[10px] font-bold transition-all cursor-pointer ${
                                layoutGrid === 'quad'
                                    ? 'bg-[#2962ff] text-white shadow-sm'
                                    : 'text-slate-400 hover:text-slate-200'
                            }`}
                            title="2x2 Quad Grid View"
                        >
                            2x2
                        </button>
                    </div>

                    {/* Risk-Reward Lot Calculator Button */}
                    <button
                        onClick={() => setShowRiskCalculatorModal(true)}
                        className="p-2 rounded-lg bg-[#2a2e39]/60 hover:bg-[#2a2e39] text-[#2962ff] hover:text-cyan-400 transition-all cursor-pointer border border-[#363a45]/50"
                        title="Position & Lot Size Calculator"
                    >
                        <Calculator className="w-4 h-4" />
                    </button>

                    {/* Mic Silence Toggle Icon-Only Button */}
                    <button
                        onClick={toggleMicSilence}
                        className={`p-2 rounded-lg border transition-all cursor-pointer border-[#363a45]/50 ${
                            micEnabled
                                ? 'bg-[#2a2e39]/60 hover:bg-[#2a2e39] text-emerald-400'
                                : 'bg-rose-500/20 text-rose-400 border-rose-500/40 hover:bg-rose-500/30'
                        }`}
                        title={micEnabled ? 'Mute FRIDAY Mic' : 'Unmute FRIDAY Mic'}
                    >
                        {micEnabled ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
                    </button>

                    {/* Minimize Button */}
                    <button
                        onClick={onMinimize}
                        className="p-2 rounded-lg bg-[#2a2e39]/60 hover:bg-[#2a2e39] text-slate-300 hover:text-white transition-all cursor-pointer border border-[#363a45]/50"
                        title="Minimize Trading Station"
                    >
                        <Minus className="w-4 h-4" />
                    </button>

                    <button
                        onClick={toggleFullscreen}
                        className="p-2 rounded-lg bg-[#2a2e39]/60 hover:bg-[#2a2e39] text-slate-300 hover:text-white transition-all cursor-pointer border border-[#363a45]/50"
                        title="Toggle Fullscreen"
                    >
                        <Maximize2 className="w-4 h-4" />
                    </button>

                    {/* Compact Icon-Only Exit Button */}
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg bg-[#f23645]/15 hover:bg-[#f23645]/30 text-[#f23645] transition-all cursor-pointer border border-[#f23645]/30"
                        title="Exit Trading Station"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>
            </header>

            {/* TradingView Symbol Search Overlay Modal */}
            <AnimatePresence>
                {showSymbolSearchModal && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
                        onClick={() => setShowSymbolSearchModal(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.95, y: -10 }}
                            animate={{ scale: 1, y: 0 }}
                            exit={{ scale: 0.95, y: -10 }}
                            className="w-full max-w-md bg-[#1e222d] border border-[#2a2e39] rounded-xl shadow-2xl p-4 flex flex-col gap-3 text-slate-100"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="flex items-center justify-between border-b border-[#2a2e39] pb-2">
                                <span className="font-bold text-sm text-slate-200">Symbol Search</span>
                                <button onClick={() => setShowSymbolSearchModal(false)} className="text-slate-400 hover:text-white cursor-pointer">
                                    <X className="w-4 h-4" />
                                </button>
                            </div>

                            <form onSubmit={handleCustomSymbolSearch} className="flex gap-2">
                                <div className="relative flex-1">
                                    <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
                                    <input
                                        type="text"
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        placeholder="Search Ticker (e.g. AAPL, EURUSD, XAUUSD, RELIANCE)..."
                                        className="w-full bg-[#131722] border border-[#2a2e39] rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#2962ff]"
                                        autoFocus
                                    />
                                </div>
                                <button type="submit" className="px-3 py-1.5 rounded-lg bg-[#2962ff] hover:bg-[#1e54e4] text-white text-xs font-semibold cursor-pointer">
                                    Load
                                </button>
                            </form>

                            <div className="text-[11px] text-slate-400">
                                Popular: <span className="text-[#2962ff] cursor-pointer" onClick={() => { setSelectedSymbol('FX:EURUSD'); setShowSymbolSearchModal(false); }}>EUR/USD</span> • <span className="text-[#2962ff] cursor-pointer" onClick={() => { setSelectedSymbol('FX:GBPUSD'); setShowSymbolSearchModal(false); }}>GBP/USD</span> • <span className="text-[#2962ff] cursor-pointer" onClick={() => { setSelectedSymbol('FX:USDJPY'); setShowSymbolSearchModal(false); }}>USD/JPY</span> • <span className="text-[#2962ff] cursor-pointer" onClick={() => { setSelectedSymbol('OANDA:XAUUSD'); setShowSymbolSearchModal(false); }}>XAU/USD</span> • <span className="text-[#2962ff] cursor-pointer" onClick={() => { setSelectedSymbol('BINANCE:BTCUSDT'); setShowSymbolSearchModal(false); }}>BTC/USD</span>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Risk-Reward & Lot Size Calculator Modal */}
            <AnimatePresence>
                {showRiskCalculatorModal && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
                        onClick={() => setShowRiskCalculatorModal(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.95, y: -10 }}
                            animate={{ scale: 1, y: 0 }}
                            exit={{ scale: 0.95, y: -10 }}
                            className="w-full max-w-sm bg-[#1e222d] border border-[#2a2e39] rounded-2xl shadow-2xl p-4 flex flex-col gap-3.5 text-slate-100 font-sans"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="flex items-center justify-between border-b border-[#2a2e39] pb-2.5">
                                <div className="flex items-center gap-2">
                                    <Calculator className="w-4 h-4 text-[#2962ff]" />
                                    <span className="font-bold text-sm text-slate-100 font-mono">Lot Size & Risk Calculator</span>
                                </div>
                                <button onClick={() => setShowRiskCalculatorModal(false)} className="text-slate-400 hover:text-white cursor-pointer">
                                    <X className="w-4 h-4" />
                                </button>
                            </div>

                            <div className="flex flex-col gap-2 font-mono text-xs">
                                <div className="flex flex-col gap-1">
                                    <label className="text-[10px] text-slate-400 uppercase">Account Balance ($)</label>
                                    <input
                                        type="number"
                                        value={accountBalance}
                                        onChange={(e) => setAccountBalance(Number(e.target.value))}
                                        className="bg-[#131722] border border-[#2a2e39] rounded-lg px-3 py-1.5 text-white outline-none focus:border-[#2962ff]"
                                    />
                                </div>

                                <div className="grid grid-cols-2 gap-2">
                                    <div className="flex flex-col gap-1">
                                        <label className="text-[10px] text-slate-400 uppercase">Risk %</label>
                                        <input
                                            type="number"
                                            step="0.1"
                                            value={riskPercent}
                                            onChange={(e) => setRiskPercent(Number(e.target.value))}
                                            className="bg-[#131722] border border-[#2a2e39] rounded-lg px-3 py-1.5 text-white outline-none focus:border-[#2962ff]"
                                        />
                                    </div>
                                    <div className="flex flex-col gap-1">
                                        <label className="text-[10px] text-slate-400 uppercase">Stop Loss (Pips)</label>
                                        <input
                                            type="number"
                                            value={stopPips}
                                            onChange={(e) => setStopPips(Number(e.target.value))}
                                            className="bg-[#131722] border border-[#2a2e39] rounded-lg px-3 py-1.5 text-white outline-none focus:border-[#2962ff]"
                                        />
                                    </div>
                                </div>

                                {/* Calculation Results Box */}
                                <div className="mt-2 p-3 rounded-xl bg-[#131722] border border-[#2a2e39] flex flex-col gap-2">
                                    <div className="flex justify-between items-center text-slate-300">
                                        <span>Max Risk Amount:</span>
                                        <span className="font-bold text-rose-400">${(accountBalance * (riskPercent / 100)).toFixed(2)}</span>
                                    </div>
                                    <div className="flex justify-between items-center text-slate-300">
                                        <span>Recommended Lot Size:</span>
                                        <span className="font-bold text-cyan-400 text-sm">
                                            {(((accountBalance * (riskPercent / 100)) / (stopPips * 10))).toFixed(2)} Lots
                                        </span>
                                    </div>
                                    <div className="flex justify-between items-center text-slate-300">
                                        <span>Target Profit (1:2 R:R):</span>
                                        <span className="font-bold text-emerald-400">+${(accountBalance * (riskPercent / 100) * 2).toFixed(2)}</span>
                                    </div>
                                </div>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Main Workstation Body: Multi-Chart Grid on Left + Dedicated Watchlist Panel on Right */}
            <div className="flex-1 w-full h-full flex min-h-0 relative overflow-hidden">
                {/* Multi-Chart Container Grid */}
                <div className="flex-1 h-full relative bg-[#131722]">
                    {layoutGrid === 'single' && (
                        <ProfessionalChart symbol={selectedSymbol} interval={selectedInterval} />
                    )}

                    {layoutGrid === 'dual' && (
                        <div className="grid grid-cols-2 gap-1 w-full h-full p-1 bg-[#1e222d]">
                            <div className="w-full h-full relative rounded overflow-hidden border border-[#2a2e39]">
                                <ProfessionalChart symbol={selectedSymbol} interval={selectedInterval} />
                            </div>
                            <div className="w-full h-full relative rounded overflow-hidden border border-[#2a2e39]">
                                <ProfessionalChart symbol="FX:GBPUSD" interval={selectedInterval} />
                            </div>
                        </div>
                    )}

                    {layoutGrid === 'quad' && (
                        <div className="grid grid-cols-2 grid-rows-2 gap-1 w-full h-full p-1 bg-[#1e222d]">
                            <div className="w-full h-full relative rounded overflow-hidden border border-[#2a2e39]">
                                <ProfessionalChart symbol={selectedSymbol} interval={selectedInterval} />
                            </div>
                            <div className="w-full h-full relative rounded overflow-hidden border border-[#2a2e39]">
                                <ProfessionalChart symbol="FX:GBPUSD" interval={selectedInterval} />
                            </div>
                            <div className="w-full h-full relative rounded overflow-hidden border border-[#2a2e39]">
                                <ProfessionalChart symbol="FX:USDJPY" interval={selectedInterval} />
                            </div>
                            <div className="w-full h-full relative rounded overflow-hidden border border-[#2a2e39]">
                                <ProfessionalChart symbol="OANDA:XAUUSD" interval={selectedInterval} />
                            </div>
                        </div>
                    )}
                </div>

                {/* Dedicated Custom Watchlist Panel (Forex + Indian Stock Market 🇮🇳) */}
                <CustomWatchlist
                    currentSymbol={selectedSymbol}
                    onSelectSymbol={setSelectedSymbol}
                />
            </div>
        </motion.div>
    );
}
