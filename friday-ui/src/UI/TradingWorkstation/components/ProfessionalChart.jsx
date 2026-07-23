import React, { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, CrosshairMode } from 'lightweight-charts';
import { Sliders, X, RefreshCw, TrendingUp, Activity } from 'lucide-react';

const INTERVALS = [
    { label: '1m',  value: '1' },
    { label: '5m',  value: '5' },
    { label: '15m', value: '15' },
    { label: '30m', value: '30' },
    { label: '1h',  value: '60' },
    { label: '1D',  value: 'D' },
    { label: '1W',  value: 'W' },
];

export default function ProfessionalChart({ symbol = 'NSE:RELIANCE' }) {
    const containerRef = useRef(null);
    const chartRef     = useRef(null);
    const candleRef    = useRef(null);
    const volumeRef    = useRef(null);

    const [interval, setInterval] = useState('5');
    const [loading, setLoading]   = useState(false);
    const [error, setError]       = useState(null);
    const [ohlcInfo, setOhlcInfo] = useState(null);
    const [showSettings, setShowSettings] = useState(false);
    const [lastUpdated, setLastUpdated]   = useState(null);
    const [isLive, setIsLive]             = useState(false);
    const pollTimerRef = useRef(null);
    const [upColor,   setUpColor]   = useState('#089981');
    const [downColor, setDownColor] = useState('#f23645');

    // ── Create / resize chart ─────────────────────────────────────────────────
    useEffect(() => {
        if (!containerRef.current) return;

        const chart = createChart(containerRef.current, {
            layout: {
                background:  { color: '#0a0f1d' },
                textColor:   '#9ca3af',
                fontFamily:  'Inter, JetBrains Mono, monospace',
                fontSize:    11,
            },
            grid: {
                vertLines: { color: '#1e222d' },
                horzLines: { color: '#1e222d' },
            },
            crosshair: {
                mode: CrosshairMode.Normal,
                vertLine: { color: '#00b7ff', labelBackgroundColor: '#0a0f1d' },
                horzLine: { color: '#00b7ff', labelBackgroundColor: '#0a0f1d' },
            },
            rightPriceScale: {
                borderColor: '#1e222d',
                scaleMargins: { top: 0.05, bottom: 0.22 },
            },
            timeScale: {
                borderColor:     '#1e222d',
                timeVisible:     true,
                secondsVisible:  false,
                tickMarkFormatter: (time) => {
                    const d = new Date(time * 1000);
                    return d.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
                },
            },
            handleScroll:  true,
            handleScale:   true,
            autoSize: true,
        });

        const candleSeries = chart.addCandlestickSeries({
            upColor,
            downColor,
            wickUpColor:   upColor,
            wickDownColor: downColor,
            borderUpColor:   upColor,
            borderDownColor: downColor,
            priceLineVisible: true,
            lastValueVisible: true,
        });

        const volumeSeries = chart.addHistogramSeries({
            priceFormat:  { type: 'volume' },
            priceScaleId: 'volume',
            scaleMargins: { top: 0.82, bottom: 0 },
        });
        chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });

        chartRef.current  = chart;
        candleRef.current = candleSeries;
        volumeRef.current = volumeSeries;

        // Crosshair → update OHLC tooltip
        chart.subscribeCrosshairMove((param) => {
            if (!param?.seriesData) return;
            const cd = param.seriesData.get(candleSeries);
            if (cd) setOhlcInfo(cd);
        });

        return () => { chart.remove(); chartRef.current = null; };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // ── Update candle / wick colors when user changes them ───────────────────
    useEffect(() => {
        if (!candleRef.current) return;
        candleRef.current.applyOptions({
            upColor, downColor,
            wickUpColor: upColor, wickDownColor: downColor,
            borderUpColor: upColor, borderDownColor: downColor,
        });
    }, [upColor, downColor]);

    // ── Fetch OHLCV data from backend ─────────────────────────────────────────
    const fetchData = useCallback(async (sym, iv) => {
        if (!candleRef.current || !volumeRef.current) return;
        setLoading(true);
        setError(null);

        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 12000);

        try {
            const res = await fetch(
                `http://localhost:8000/api/trading/ohlcv?symbol=${encodeURIComponent(sym)}&interval=${iv}`,
                { signal: controller.signal }
            );
            clearTimeout(timeout);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const { candles, error: apiError } = await res.json();

            if (apiError) throw new Error(apiError);
            if (!candles || candles.length === 0) throw new Error(`No data for ${sym}`);

            candles.sort((a, b) => a.time - b.time);

            candleRef.current.setData(candles.map(c => ({
                time: c.time, open: c.open, high: c.high, low: c.low, close: c.close,
            })));
            volumeRef.current.setData(candles.map(c => ({
                time:  c.time,
                value: c.volume,
                color: c.close >= c.open ? `${upColor}66` : `${downColor}66`,
            })));
            chartRef.current?.timeScale().fitContent();
            setLastUpdated(new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
            setOhlcInfo(candles[candles.length - 1]);
        } catch (e) {
            clearTimeout(timeout);
            if (e.name === 'AbortError') {
                setError('Request timed out. Backend may be slow — click ↺ to retry.');
            } else {
                setError(`Failed to load ${sym}: ${e.message}`);
            }
        } finally {
            setLoading(false);
        }
    }, [upColor, downColor]);


    // Re-fetch when symbol or interval changes
    useEffect(() => {
        fetchData(symbol, interval);
    }, [symbol, interval, fetchData]);

    // ── Live auto-refresh every 30 s ─────────────────────────────────────────
    useEffect(() => {
        if (pollTimerRef.current) clearInterval(pollTimerRef.current);

        // Only poll for intraday intervals (not D / W)
        const shouldPoll = !['D', 'W'].includes(interval);
        if (!shouldPoll) { setIsLive(false); return; }

        setIsLive(true);
        pollTimerRef.current = setInterval(async () => {
            if (!candleRef.current || !volumeRef.current) return;
            try {
                const res  = await fetch(
                    `http://localhost:8000/api/trading/ohlcv?symbol=${encodeURIComponent(symbol)}&interval=${interval}`
                );
                const { candles } = await res.json();
                if (!candles || candles.length === 0) return;
                candles.sort((a, b) => a.time - b.time);

                // Update only the last candle (live tick)
                const last = candles[candles.length - 1];
                candleRef.current.update({ time: last.time, open: last.open, high: last.high, low: last.low, close: last.close });
                volumeRef.current.update({ time: last.time, value: last.volume, color: last.close >= last.open ? `${upColor}66` : `${downColor}66` });
                setLastUpdated(new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
                setOhlcInfo(last);
            } catch (_) {}
        }, 30000);

        return () => { if (pollTimerRef.current) clearInterval(pollTimerRef.current); };
    }, [symbol, interval, upColor, downColor]);

    // ── Interval button strip ─────────────────────────────────────────────────
    const displaySymbol = symbol.replace(/^(NSE:|BSE:|OANDA:|BINANCE:|FX:|NASDAQ:|NYSE:|CAPITALCOM:)/, '');

    return (
        <div className="w-full h-full bg-[#0a0f1d] relative overflow-hidden flex flex-col">

            {/* ── Top Bar ── */}
            <div className="flex items-center gap-2 px-3 py-1.5 bg-[#0d1220] border-b border-white/5 z-20 flex-shrink-0">
                {/* Symbol badge */}
                <div className="flex items-center gap-1.5">
                    <TrendingUp size={13} className="text-cyan-400" />
                    <span className="text-white font-mono font-bold text-sm tracking-wide">{displaySymbol}</span>
                    <span className="text-slate-500 font-mono text-xs">{symbol.split(':')[0]}</span>
                </div>

                <div className="h-4 w-px bg-white/10 mx-1" />

                {/* LIVE indicator */}
                {isLive && (
                    <div className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-emerald-500/15 border border-emerald-500/30">
                        <Activity size={9} className="text-emerald-400 animate-pulse" />
                        <span className="text-emerald-400 font-mono text-[9px] font-bold">LIVE</span>
                    </div>
                )}

                <div className="h-4 w-px bg-white/10 mx-1" />

                {/* Interval selector */}
                <div className="flex items-center gap-0.5">
                    {INTERVALS.map(iv => (
                        <button
                            key={iv.value}
                            onClick={() => setInterval(iv.value)}
                            className={`px-2 py-0.5 rounded text-[11px] font-mono font-semibold transition-all ${
                                interval === iv.value
                                    ? 'bg-cyan-500 text-black'
                                    : 'text-slate-400 hover:text-white hover:bg-white/10'
                            }`}
                        >
                            {iv.label}
                        </button>
                    ))}
                </div>

                <div className="flex-1" />

                {/* OHLC display */}
                {ohlcInfo && (
                    <div className="flex items-center gap-2 text-[10px] font-mono">
                        <span className="text-slate-500">O <span className="text-white">{ohlcInfo.open?.toFixed(2)}</span></span>
                        <span className="text-slate-500">H <span className="text-emerald-400">{ohlcInfo.high?.toFixed(2)}</span></span>
                        <span className="text-slate-500">L <span className="text-rose-400">{ohlcInfo.low?.toFixed(2)}</span></span>
                        <span className="text-slate-500">C <span className={`font-bold ${ohlcInfo.close >= ohlcInfo.open ? 'text-emerald-400' : 'text-rose-400'}`}>{ohlcInfo.close?.toFixed(2)}</span></span>
                    </div>
                )}

                {/* Last updated timestamp */}
                {lastUpdated && (
                    <span className="text-slate-600 font-mono text-[9px] hidden md:block">{lastUpdated}</span>
                )}

                <div className="flex items-center gap-1 ml-1">
                    <button
                        onClick={() => { fetchData(symbol, interval); setLastUpdated(new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })); }}
                        title="Refresh"
                        className="p-1 text-slate-400 hover:text-cyan-300 hover:bg-white/5 rounded transition-all"
                    >
                        <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
                    </button>
                    <button
                        onClick={() => setShowSettings(s => !s)}
                        title="Settings"
                        className="p-1 text-slate-400 hover:text-cyan-300 hover:bg-white/5 rounded transition-all"
                    >
                        <Sliders size={12} />
                    </button>
                </div>
            </div>

            {/* ── Settings Panel ── */}
            {showSettings && (
                <div className="absolute top-10 right-3 z-50 w-64 rounded-2xl bg-[#080d1a]/97 border border-cyan-500/30 p-4 shadow-[0_20px_60px_rgba(0,0,0,0.9)] backdrop-blur-2xl text-slate-100 text-xs flex flex-col gap-3">
                    <div className="flex items-center justify-between pb-2 border-b border-cyan-500/20">
                        <span className="font-mono text-cyan-300 font-bold flex items-center gap-1.5">
                            <Sliders size={12} /> CANDLE COLORS
                        </span>
                        <button onClick={() => setShowSettings(false)} className="text-slate-400 hover:text-white">
                            <X size={13} />
                        </button>
                    </div>
                    <div className="flex items-center justify-between bg-slate-900/60 p-2 rounded-xl border border-white/5">
                        <span className="text-emerald-400 font-medium">Bullish (Up)</span>
                        <input type="color" value={upColor} onChange={e => setUpColor(e.target.value)}
                            className="w-6 h-6 rounded cursor-pointer bg-transparent border-0" />
                    </div>
                    <div className="flex items-center justify-between bg-slate-900/60 p-2 rounded-xl border border-white/5">
                        <span className="text-rose-400 font-medium">Bearish (Down)</span>
                        <input type="color" value={downColor} onChange={e => setDownColor(e.target.value)}
                            className="w-6 h-6 rounded cursor-pointer bg-transparent border-0" />
                    </div>
                    <button
                        onClick={() => { fetchData(symbol, interval); setShowSettings(false); }}
                        className="w-full py-1.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-mono text-xs font-bold transition-all cursor-pointer"
                    >
                        Apply
                    </button>
                </div>
            )}

            {/* ── Loading overlay ── */}
            {loading && (
                <div className="absolute inset-0 flex items-center justify-center z-30 bg-[#0a0f1d]/80 backdrop-blur-sm">
                    <div className="flex flex-col items-center gap-3">
                        <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
                        <span className="text-cyan-400 font-mono text-xs">Loading {displaySymbol}...</span>
                    </div>
                </div>
            )}

            {/* ── Error state ── */}
            {!loading && error && (
                <div className="absolute inset-0 flex items-center justify-center z-30">
                    <div className="flex flex-col items-center gap-3 text-center px-8">
                        <span className="text-4xl">⚠️</span>
                        <span className="text-rose-400 font-mono text-sm">{error}</span>
                        <button
                            onClick={() => fetchData(symbol, interval)}
                            className="px-4 py-1.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-mono text-xs font-bold transition-all"
                        >
                            Retry
                        </button>
                    </div>
                </div>
            )}

            {/* ── Chart container ── */}
            <div ref={containerRef} className="flex-1 relative z-10" />
        </div>
    );
}
