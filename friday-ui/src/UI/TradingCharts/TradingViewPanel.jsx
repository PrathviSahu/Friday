import { useEffect, useRef, useState } from 'react';
import { createChart, ColorType } from 'lightweight-charts';
import { fetchKlines } from '../../services/market';
import DrawOverlay from './DrawOverlay';

const UP = '#26a69a';
const DOWN = '#ef5350';

export default function TradingViewPanel({ symbol, interval = '5m', livePrice = null, drawMode = null, clearSignal = 0 }) {
    const containerRef = useRef(null);
    const chartRef = useRef(null);
    const candleRef = useRef(null);
    const volumeRef = useRef(null);
    const lastBarRef = useRef(null);

    const [status, setStatus] = useState('loading'); // loading | ready | error
    const [error, setError] = useState('');

    // ── create chart once ────────────────────────────────────────────────────
    useEffect(() => {
        if (!containerRef.current) return;
        const chart = createChart(containerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: '#131722' },
                textColor: '#d1d4dc',
                fontFamily: 'Space Grotesk, sans-serif',
            },
            grid: {
                vertLines: { color: 'rgba(42,46,57,0.5)' },
                horzLines: { color: 'rgba(42,46,57,0.5)' },
            },
            crosshair: { mode: 0 },
            rightPriceScale: { borderColor: 'rgba(42,46,57,0.8)' },
            timeScale: { borderColor: 'rgba(42,46,57,0.8)', timeVisible: true, secondsVisible: false },
            autoSize: true,
        });
        const candle = chart.addCandlestickSeries({
            upColor: UP,
            downColor: DOWN,
            borderUpColor: UP,
            borderDownColor: DOWN,
            wickUpColor: UP,
            wickDownColor: DOWN,
        });
        const volume = chart.addHistogramSeries({
            priceFormat: { type: 'volume' },
            priceScaleId: 'vol',
            color: 'rgba(0,183,255,0.4)',
        });
        volume.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });

        chartRef.current = chart;
        candleRef.current = candle;
        volumeRef.current = volume;

        return () => {
            chart.remove();
            chartRef.current = null;
            candleRef.current = null;
            volumeRef.current = null;
        };
    }, []);

    // ── load klines on symbol / interval change ───────────────────────────────
    useEffect(() => {
        let cancelled = false;
        setStatus('loading');
        setError('');
        fetchKlines(symbol, interval)
            .then((data) => {
                if (cancelled || !candleRef.current) return;
                const candles = (data.candles || []).map((c) => ({
                    time: c.time,
                    open: c.open,
                    high: c.high,
                    low: c.low,
                    close: c.close,
                }));
                const vols = (data.candles || []).map((c) => ({
                    time: c.time,
                    value: c.volume,
                    color: c.close >= c.open ? 'rgba(38,166,154,0.4)' : 'rgba(239,83,80,0.4)',
                }));
                if (!candles.length) {
                    setStatus('error');
                    setError('No data');
                    return;
                }
                candleRef.current.setData(candles);
                volumeRef.current.setData(vols);
                candleRef.current.priceScale().applyOptions({ autoScale: true });
                lastBarRef.current = { ...candles[candles.length - 1], volume: vols[vols.length - 1]?.value || 0 };
                setStatus('ready');
            })
            .catch((err) => {
                if (cancelled) return;
                setStatus('error');
                setError(String(err.message || err));
            });
        return () => {
            cancelled = true;
        };
    }, [symbol, interval]);

    // ── periodic refresh (pick up new bars from the backend cache) ─────────────
    useEffect(() => {
        const id = setInterval(() => {
            fetchKlines(symbol, interval)
                .then((data) => {
                    if (!candleRef.current || !data.candles?.length) return;
                    const candles = data.candles.map((c) => ({
                        time: c.time,
                        open: c.open,
                        high: c.high,
                        low: c.low,
                        close: c.close,
                    }));
                    candleRef.current.setData(candles);
                    lastBarRef.current = { ...candles[candles.length - 1] };
                })
                .catch(() => {});
        }, 60000);
        return () => clearInterval(id);
    }, [symbol, interval]);

    // ── live last-bar update from polled quote price ──────────────────────────
    useEffect(() => {
        if (livePrice == null || !candleRef.current || !lastBarRef.current) return;
        const bar = lastBarRef.current;
        const next = {
            ...bar,
            close: livePrice,
            high: Math.max(bar.high, livePrice),
            low: Math.min(bar.low, livePrice),
        };
        lastBarRef.current = next;
        candleRef.current.update({
            time: next.time,
            open: next.open,
            high: next.high,
            low: next.low,
            close: next.close,
        });
        if (volumeRef.current) {
            volumeRef.current.update({
                time: next.time,
                value: next.volume,
                color: next.close >= next.open ? 'rgba(38,166,154,0.4)' : 'rgba(239,83,80,0.4)',
            });
        }
    }, [livePrice]);

    return (
        <div className="relative w-full h-full">
            <div ref={containerRef} className="absolute inset-0" />
            {chartRef.current && candleRef.current && (
                <DrawOverlay
                    chart={chartRef.current}
                    series={candleRef.current}
                    symbol={symbol}
                    drawMode={drawMode}
                    clearSignal={clearSignal}
                />
            )}
            {status === 'loading' && (
                <div className="absolute inset-0 flex items-center justify-center text-[11px] tracking-[0.3em] uppercase text-[#00B7FF]/60">
                    Loading market data…
                </div>
            )}
            {status === 'error' && (
                <div className="absolute inset-0 flex items-center justify-center text-[11px] tracking-[0.2em] uppercase text-[#ef5350]/80">
                    Data unavailable — {error}
                </div>
            )}
        </div>
    );
}
