import React, { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, CrosshairMode } from 'lightweight-charts';
import { RefreshCw, TrendingUp, Activity, ChevronDown } from 'lucide-react';

// TradingView-exact timeframe list
const TIMEFRAMES = [
    { label: '1m',  value: '1' },
    { label: '5m',  value: '5' },
    { label: '15m', value: '15' },
    { label: '30m', value: '30' },
    { label: '1h',  value: '60' },
    { label: '4h',  value: '240' },
    { label: '1D',  value: 'D' },
    { label: '1W',  value: 'W' },
];

// TradingView dark theme — exact color match
const TV_THEME = {
    bg:          '#131722',
    bgSecondary: '#1e222d',
    border:      '#2a2e39',
    text:        '#b2b5be',
    textLight:   '#787b86',
    textBright:  '#d1d4dc',
    cyan:        '#00b7ff',
    green:       '#089981',
    red:         '#f23645',
    liveGreen:   '#26a69a',
};

function formatOHLC(value, symbol = '') {
    if (value === undefined || value === null) return '—';
    const s = String(symbol).toUpperCase();
    const isJPY = s.includes('JPY');
    const isFX  = s.includes('FX:');
    if (isJPY)  return value.toFixed(3);
    if (isFX)   return value.toFixed(5);
    return value.toFixed(4);
}

export default function ProfessionalChart({ symbol = 'FX:EURUSD', interval: propInterval, onIntervalChange }) {
    const containerRef = useRef(null);
    const chartRef     = useRef(null);
    const candleRef    = useRef(null);
    const volumeRef    = useRef(null);
    const pollRef      = useRef(null);

    const [interval, setIntervalState] = useState(propInterval || '5');
    const [loading,  setLoading]   = useState(false);
    const [error,    setError]     = useState(null);
    const [ohlcInfo, setOhlcInfo]  = useState(null);
    const [isLive,   setIsLive]    = useState(false);
    const [lastTick, setLastTick]  = useState(null);
    const [upColor,   setUpColor]   = useState(TV_THEME.green);
    const [downColor, setDownColor] = useState(TV_THEME.red);

    // Sync controlled interval from parent
    useEffect(() => {
        if (propInterval && propInterval !== interval) {
            setIntervalState(propInterval);
        }
    }, [propInterval]);

    const handleIntervalClick = (val) => {
        setIntervalState(val);
        onIntervalChange?.(val);
    };

    // ── Build chart once ─────────────────────────────────────────────────────
    useEffect(() => {
        if (!containerRef.current) return;

        const chart = createChart(containerRef.current, {
            layout: {
                background:  { color: TV_THEME.bg },
                textColor:   TV_THEME.text,
                fontFamily:  '"Inter", "JetBrains Mono", -apple-system, monospace',
                fontSize:    11,
            },
            grid: {
                vertLines: { color: TV_THEME.bgSecondary },
                horzLines: { color: TV_THEME.bgSecondary },
            },
            crosshair: {
                mode: CrosshairMode.Normal,
                vertLine: {
                    color:                TV_THEME.cyan,
                    width:                1,
                    style:                1, // dashed
                    labelBackgroundColor: TV_THEME.bgSecondary,
                },
                horzLine: {
                    color:                TV_THEME.cyan,
                    width:                1,
                    style:                1,
                    labelBackgroundColor: TV_THEME.bgSecondary,
                },
            },
            rightPriceScale: {
                borderColor:  TV_THEME.border,
                scaleMargins: { top: 0.06, bottom: 0.20 },
                mode:         0, // Normal
            },
            leftPriceScale: { visible: false },
            timeScale: {
                borderColor:    TV_THEME.border,
                timeVisible:    true,
                secondsVisible: false,
                rightOffset:    8,
                barSpacing:     6,
            },
            handleScroll:  { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: true },
            handleScale:   { axisPressedMouseMove: true, axisDoubleClickReset: true, mouseWheel: true, pinch: true },
            autoSize:      true,
        });

        const candleSeries = chart.addCandlestickSeries({
            upColor,
            downColor,
            wickUpColor:      upColor,
            wickDownColor:    downColor,
            borderUpColor:    upColor,
            borderDownColor:  downColor,
            priceLineVisible: true,
            lastValueVisible: true,
        });

        const volumeSeries = chart.addHistogramSeries({
            priceFormat:  { type: 'volume' },
            priceScaleId: 'volume',
        });
        chart.priceScale('volume').applyOptions({
            scaleMargins: { top: 0.82, bottom: 0 },
        });

        chartRef.current  = chart;
        candleRef.current = candleSeries;
        volumeRef.current = volumeSeries;

        chart.subscribeCrosshairMove((param) => {
            if (!param?.seriesData) return;
            const cd = param.seriesData.get(candleSeries);
            if (cd) setOhlcInfo(cd);
        });

        return () => {
            chart.remove();
            chartRef.current  = null;
            candleRef.current = null;
            volumeRef.current = null;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Update candle colours live
    useEffect(() => {
        if (!candleRef.current) return;
        candleRef.current.applyOptions({
            upColor, downColor,
            wickUpColor: upColor, wickDownColor: downColor,
            borderUpColor: upColor, borderDownColor: downColor,
        });
    }, [upColor, downColor]);

    // ── Fetch full OHLCV history ─────────────────────────────────────────────
    const fetchData = useCallback(async (sym, iv) => {
        if (!candleRef.current || !volumeRef.current) return;
        setLoading(true);
        setError(null);
        const ctrl = new AbortController();
        const timer = setTimeout(() => ctrl.abort(), 15000);
        try {
            const res = await fetch(
                `http://localhost:8000/api/trading/ohlcv?symbol=${encodeURIComponent(sym)}&interval=${iv}`,
                { signal: ctrl.signal }
            );
            clearTimeout(timer);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const { candles, error: apiErr, count } = await res.json();
            if (apiErr) throw new Error(apiErr);
            if (!candles || candles.length === 0) throw new Error(`No data available for ${sym}`);

            // Deduplicate by time (yfinance sometimes returns dupes)
            const seen = new Set();
            const clean = candles
                .filter(c => { if (seen.has(c.time)) return false; seen.add(c.time); return true; })
                .sort((a, b) => a.time - b.time);

            candleRef.current.setData(clean.map(c => ({
                time: c.time, open: c.open, high: c.high, low: c.low, close: c.close,
            })));
            volumeRef.current.setData(clean.map(c => ({
                time:  c.time,
                value: c.volume,
                color: c.close >= c.open ? `${upColor}55` : `${downColor}55`,
            })));
            chartRef.current?.timeScale().fitContent();
            setOhlcInfo(clean[clean.length - 1]);
            setLastTick(new Date());
        } catch (e) {
            clearTimeout(timer);
            if (e.name === 'AbortError') {
                setError('Request timed out — click ↺ to retry.');
            } else {
                setError(`${e.message}`);
            }
        } finally {
            setLoading(false);
        }
    }, [upColor, downColor]);

    // Refetch on symbol or interval change
    useEffect(() => {
        fetchData(symbol, interval);
    }, [symbol, interval, fetchData]);

    // ── Live tick poll (30s) for intraday intervals ─────────────────────────
    useEffect(() => {
        if (pollRef.current) clearInterval(pollRef.current);
        const shouldPoll = !['D', 'W'].includes(interval);
        if (!shouldPoll) { setIsLive(false); return; }
        setIsLive(true);

        pollRef.current = setInterval(async () => {
            if (!candleRef.current || !volumeRef.current) return;
            try {
                const res = await fetch(
                    `http://localhost:8000/api/trading/ohlcv?symbol=${encodeURIComponent(symbol)}&interval=${interval}`
                );
                const { candles } = await res.json();
                if (!candles?.length) return;
                const sorted = [...candles].sort((a, b) => a.time - b.time);
                const last = sorted[sorted.length - 1];
                candleRef.current.update({ time: last.time, open: last.open, high: last.high, low: last.low, close: last.close });
                volumeRef.current.update({ time: last.time, value: last.volume, color: last.close >= last.open ? `${upColor}55` : `${downColor}55` });
                setOhlcInfo(last);
                setLastTick(new Date());
            } catch (_) {}
        }, 30000);

        return () => { if (pollRef.current) clearInterval(pollRef.current); };
    }, [symbol, interval, upColor, downColor]);

    // Strip exchange prefix for display
    const displaySymbol = symbol.replace(/^(FX:|OANDA:|BINANCE:|NASDAQ:|NYSE:|CAPITALCOM:|NSE:|BSE:|NYMEX:)/, '');
    const priceDelta = ohlcInfo ? (ohlcInfo.close - ohlcInfo.open) : 0;
    const isUp       = priceDelta >= 0;

    return (
        <div style={{ background: TV_THEME.bg }} className="w-full h-full flex flex-col relative overflow-hidden">

            {/* ── TradingView-style Top Bar ── */}
            <div
                style={{ background: TV_THEME.bg, borderBottom: `1px solid ${TV_THEME.border}` }}
                className="flex items-center gap-0 px-2 py-0 flex-shrink-0 select-none"
                style={{ height: '38px', borderBottom: `1px solid ${TV_THEME.border}`, background: TV_THEME.bg }}
            >
                {/* Symbol pill */}
                <div className="flex items-center gap-1.5 pr-3 mr-1" style={{ borderRight: `1px solid ${TV_THEME.border}` }}>
                    <TrendingUp size={12} style={{ color: TV_THEME.cyan }} />
                    <span style={{ color: TV_THEME.textBright }} className="font-bold text-sm font-mono tracking-wide">
                        {displaySymbol}
                    </span>
                    <ChevronDown size={11} style={{ color: TV_THEME.textLight }} />
                </div>

                {/* Timeframe buttons — TradingView style */}
                <div className="flex items-center gap-0 px-1">
                    {TIMEFRAMES.map(tf => (
                        <button
                            key={tf.value}
                            onClick={() => handleIntervalClick(tf.value)}
                            className="transition-all duration-100 rounded font-mono text-xs px-2 py-0.5"
                            style={{
                                background:   interval === tf.value ? '#2962ff' : 'transparent',
                                color:         interval === tf.value ? '#fff'           : TV_THEME.text,
                                fontWeight:    interval === tf.value ? '700' : '400',
                                fontSize:      '11px',
                            }}
                        >
                            {tf.label}
                        </button>
                    ))}
                </div>

                <div style={{ flex: 1 }} />

                {/* OHLC Values — TradingView style */}
                {ohlcInfo && (
                    <div className="flex items-center gap-3 font-mono text-[11px] mr-2">
                        <span style={{ color: TV_THEME.textLight }}>
                            O <span style={{ color: TV_THEME.textBright }}>{formatOHLC(ohlcInfo.open, symbol)}</span>
                        </span>
                        <span style={{ color: TV_THEME.textLight }}>
                            H <span style={{ color: TV_THEME.green }}>{formatOHLC(ohlcInfo.high, symbol)}</span>
                        </span>
                        <span style={{ color: TV_THEME.textLight }}>
                            L <span style={{ color: TV_THEME.red }}>{formatOHLC(ohlcInfo.low, symbol)}</span>
                        </span>
                        <span style={{ color: TV_THEME.textLight }}>
                            C <span style={{ color: isUp ? TV_THEME.green : TV_THEME.red, fontWeight: 700 }}>
                                {formatOHLC(ohlcInfo.close, symbol)}
                            </span>
                        </span>
                        <span style={{
                            color: isUp ? TV_THEME.green : TV_THEME.red,
                            fontWeight: 600,
                        }}>
                            {isUp ? '+' : ''}{formatOHLC(priceDelta, symbol)}
                        </span>
                    </div>
                )}

                {/* Live badge */}
                {isLive && (
                    <div className="flex items-center gap-1 mr-2 px-1.5 py-0.5 rounded"
                        style={{ background: `${TV_THEME.liveGreen}20`, border: `1px solid ${TV_THEME.liveGreen}50` }}>
                        <Activity size={8} style={{ color: TV_THEME.liveGreen }} className="animate-pulse" />
                        <span style={{ color: TV_THEME.liveGreen, fontSize: '9px', fontWeight: 700 }} className="font-mono">LIVE</span>
                    </div>
                )}

                {/* Refresh */}
                <button
                    onClick={() => fetchData(symbol, interval)}
                    title="Refresh"
                    className="p-1 rounded transition-all"
                    style={{ color: TV_THEME.textLight }}
                    onMouseEnter={e => e.currentTarget.style.color = TV_THEME.textBright}
                    onMouseLeave={e => e.currentTarget.style.color = TV_THEME.textLight}
                >
                    <RefreshCw size={11} className={loading ? 'animate-spin' : ''} />
                </button>
            </div>

            {/* ── Loading overlay ── */}
            {loading && (
                <div
                    className="absolute inset-0 flex items-center justify-center z-30"
                    style={{ background: `${TV_THEME.bg}cc`, backdropFilter: 'blur(4px)' }}
                >
                    <div className="flex flex-col items-center gap-3">
                        <div className="w-7 h-7 border-2 rounded-full animate-spin"
                            style={{ borderColor: `${TV_THEME.cyan}40`, borderTopColor: TV_THEME.cyan }} />
                        <span style={{ color: TV_THEME.cyan }} className="font-mono text-xs">
                            Loading {displaySymbol}...
                        </span>
                    </div>
                </div>
            )}

            {/* ── Error state ── */}
            {!loading && error && (
                <div className="absolute inset-0 flex items-center justify-center z-30">
                    <div className="flex flex-col items-center gap-3 text-center px-8">
                        <span className="text-3xl">⚠️</span>
                        <span style={{ color: TV_THEME.red }} className="font-mono text-xs max-w-xs">{error}</span>
                        <button
                            onClick={() => fetchData(symbol, interval)}
                            className="px-4 py-1.5 rounded font-mono text-xs font-bold transition-all"
                            style={{ background: '#2962ff', color: '#fff' }}
                        >
                            Retry
                        </button>
                    </div>
                </div>
            )}

            {/* ── Chart canvas ── */}
            <div ref={containerRef} className="flex-1 relative z-10" />
        </div>
    );
}
