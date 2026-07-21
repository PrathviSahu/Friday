import React, { useRef, useEffect, useState } from 'react';
import { motion } from 'framer-motion';

export default function ProfessionalChart({ symbol, interval, activeTool, onClear }) {
    const canvasRef = useRef(null);
    const [priceData, setPriceData] = useState([]);
    const [chartType, setChartType] = useState('candlestick'); // candlestick | line | area | heikin

    // Generate mock TradingView OHLC data for selected symbol
    useEffect(() => {
        const count = 60;
        let base = symbol.includes('BTC') ? 67000 : symbol.includes('GC=F') ? 2340 : 220;
        const data = [];
        let now = Date.now() - count * 300000;

        for (let i = 0; i < count; i++) {
            const open = base + (Math.random() - 0.48) * 8;
            const high = open + Math.random() * 6;
            const low = open - Math.random() * 6;
            const close = (open + high + low) / 3 + (Math.random() - 0.48) * 4;
            data.push({ time: now + i * 300000, open, high, low, close, volume: Math.floor(Math.random() * 1000 + 200) });
            base = close;
        }
        setPriceData(data);
    }, [symbol]);

    // Draw high-FPS Canvas Chart
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas || priceData.length === 0) return;
        const ctx = canvas.getContext('2d');
        const width = (canvas.width = canvas.parentElement.clientWidth);
        const height = (canvas.height = canvas.parentElement.clientHeight);

        ctx.clearRect(0, 0, width, height);

        // Chart padding
        const padTop = 30;
        const padBottom = 40;
        const padRight = 60;
        const chartWidth = width - padRight;
        const chartHeight = height - padTop - padBottom;

        const prices = priceData.flatMap((d) => [d.high, d.low]);
        const minP = Math.min(...prices);
        const maxP = Math.max(...prices);
        const rangeP = maxP - minP || 1;

        const getY = (price) => padTop + chartHeight - ((price - minP) / rangeP) * chartHeight;
        const stepX = chartWidth / priceData.length;

        // Grid lines
        ctx.strokeStyle = '#1e293b33';
        ctx.lineWidth = 1;
        for (let i = 1; i < 5; i++) {
            const y = padTop + (chartHeight / 5) * i;
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(chartWidth, y);
            ctx.stroke();
        }

        // Draw Candlesticks / Line / Area
        priceData.forEach((d, i) => {
            const x = i * stepX + stepX / 2;
            const isGreen = d.close >= d.open;

            if (chartType === 'candlestick') {
                // Wick
                ctx.strokeStyle = isGreen ? '#10b981' : '#ef4444';
                ctx.beginPath();
                ctx.moveTo(x, getY(d.high));
                ctx.lineTo(x, getY(d.low));
                ctx.stroke();

                // Candle body
                const yOpen = getY(d.open);
                const yClose = getY(d.close);
                const candleY = Math.min(yOpen, yClose);
                const candleH = Math.max(2, Math.abs(yClose - yOpen));

                ctx.fillStyle = isGreen ? '#10b981' : '#ef4444';
                ctx.fillRect(x - stepX * 0.35, candleY, stepX * 0.7, candleH);
            }
        });

        // Price scale on right
        ctx.fillStyle = '#94a3b8';
        ctx.font = '10px monospace';
        ctx.textAlign = 'left';
        for (let i = 0; i <= 5; i++) {
            const priceVal = (maxP - (rangeP / 5) * i).toFixed(1);
            const y = padTop + (chartHeight / 5) * i;
            ctx.fillText(priceVal, chartWidth + 8, y + 3);
        }
    }, [priceData, chartType]);

    return (
        <div className="flex-1 flex flex-col h-full bg-[#050811] relative select-none">
            {/* Chart Type Toolbar */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-cyan-500/15 bg-[#080d1a]/80 text-[10px] font-mono">
                <div className="flex items-center gap-2">
                    <span className="text-slate-400">Type:</span>
                    {['candlestick', 'line', 'area', 'heikin'].map((t) => (
                        <button
                            key={t}
                            onClick={() => setChartType(t)}
                            className={`px-2 py-0.5 rounded uppercase cursor-pointer ${
                                chartType === t
                                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/40 font-bold'
                                    : 'text-slate-400 hover:text-slate-200'
                            }`}
                        >
                            {t}
                        </button>
                    ))}
                </div>
                <div className="text-cyan-400/70">
                    Active Tool: <span className="font-bold text-cyan-300">{activeTool || 'Crosshair'}</span>
                </div>
            </div>

            {/* Canvas Container */}
            <div className="flex-1 relative w-full h-full">
                <canvas ref={canvasRef} className="w-full h-full block" />
            </div>
        </div>
    );
}
