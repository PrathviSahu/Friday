import React, { useEffect, useRef, useState } from 'react';
import { Settings, X, Palette, Sliders } from 'lucide-react';

const FREE_REALTIME_WATCHLIST = [
    'OANDA:XAUUSD',
    'CAPITALCOM:DXY',
    'TVC:US10Y',
    'BINANCE:BTCUSDT',
    'BINANCE:ETHUSDT',
    'BINANCE:SOLUSDT',
    'FX:EURUSD',
    'FX:GBPUSD',
    'FX:USDJPY',
    'FOREXCOM:SPXUSD',
    'FOREXCOM:NSXUSD',
    'NSE:NIFTY',
    'NSE:BANKNIFTY',
    'NSE:RELIANCE',
];

export default function ProfessionalChart() {
    const containerRef = useRef(null);
    const [showSettings, setShowSettings] = useState(false);

    // Customizable Candle & Drawing Settings
    const [upColor, setUpColor] = useState('#089981');    // Bullish Green
    const [downColor, setDownColor] = useState('#f23645');  // Bearish Red
    const [fibColor, setFibColor] = useState('#00b7ff');    // Fib Retracement color
    const [fibExtend, setFibExtend] = useState(true);

    const loadChart = () => {
        if (!containerRef.current) return;
        containerRef.current.innerHTML = '';

        const script = document.createElement('script');
        script.src = 'https://s3.tradingview.com/tv.js';
        script.async = true;
        script.onload = () => {
            if (window.TradingView && containerRef.current) {
                new window.TradingView.widget({
                    autosize: true,
                    symbol: 'OANDA:XAUUSD',
                    interval: '5',
                    timezone: 'Asia/Kolkata',
                    theme: 'dark',
                    style: '1',
                    locale: 'en',
                    toolbar_bg: '#131722',
                    enable_publishing: false,
                    hide_side_toolbar: false, // Left drawing tools (Trendlines, Fibs, Position tools)
                    allow_symbol_change: true,
                    watchlist: FREE_REALTIME_WATCHLIST,
                    details: true,
                    hotlist: true,
                    calendar: true,
                    show_popup_button: true,
                    popup_width: '1000',
                    popup_height: '650',
                    container_id: 'tradingview_widget_container',
                    backgroundColor: '#0a0f1d',
                    gridColor: 'rgba(56, 189, 248, 0.15)',
                    disabled_features: [],
                    enabled_features: [
                        'study_templates',
                        'use_localstorage_for_settings',
                        'side_toolbar_in_fullscreen_mode',
                        'items_favoriting'
                    ],
                    overrides: {
                        // Candle Colors
                        "mainSeriesProperties.candleStyle.upColor": upColor,
                        "mainSeriesProperties.candleStyle.downColor": downColor,
                        "mainSeriesProperties.candleStyle.drawWick": true,
                        "mainSeriesProperties.candleStyle.drawBorder": true,
                        "mainSeriesProperties.candleStyle.borderColor": "#378658",
                        "mainSeriesProperties.candleStyle.borderUpColor": upColor,
                        "mainSeriesProperties.candleStyle.borderDownColor": downColor,
                        "mainSeriesProperties.candleStyle.wickUpColor": upColor,
                        "mainSeriesProperties.candleStyle.wickDownColor": downColor,
                        
                        // Fib Retracement Defaults
                        "linetoolfibretracement.linecolor": fibColor,
                        "linetoolfibretracement.extendLines": fibExtend,

                        // Grid & Background
                        "paneProperties.vertGridProperties.color": "rgba(56, 189, 248, 0.15)",
                        "paneProperties.horzGridProperties.color": "rgba(56, 189, 248, 0.15)",
                    }
                });
            }
        };

        containerRef.current.appendChild(script);
    };

    useEffect(() => {
        loadChart();
    }, [upColor, downColor, fibColor, fibExtend]);

    return (
        <div className="flex-1 w-full h-full bg-[#0a0f1d] relative overflow-hidden">
            {/* Customization Settings Button */}
            <div className="absolute top-2.5 right-48 z-40">
                <button
                    onClick={() => setShowSettings((s) => !s)}
                    className="flex items-center gap-1.5 px-3 py-1 rounded-lg border border-cyan-500/40 bg-[#0a0f1d]/90 text-cyan-300 hover:bg-cyan-500/20 text-xs font-mono tracking-wider transition-all cursor-pointer shadow-lg backdrop-blur-md"
                >
                    <Settings size={13} className="text-cyan-400" />
                    <span>Chart Settings</span>
                </button>
            </div>

            {/* Customization Modal */}
            {showSettings && (
                <div className="absolute top-12 right-48 z-50 w-72 rounded-2xl bg-[#080d1a]/95 border border-cyan-500/30 p-4 shadow-[0_20px_60px_rgba(0,0,0,0.9)] backdrop-blur-2xl text-slate-100 font-sans text-xs flex flex-col gap-4 select-none">
                    <div className="flex items-center justify-between pb-2 border-b border-cyan-500/20">
                        <div className="flex items-center gap-1.5 font-mono text-cyan-300 font-bold">
                            <Sliders size={14} className="text-cyan-400" />
                            <span>CHART & FIB CUSTOMIZER</span>
                        </div>
                        <button onClick={() => setShowSettings(false)} className="text-slate-400 hover:text-white cursor-pointer">
                            <X size={14} />
                        </button>
                    </div>

                    {/* Candle Colors */}
                    <div className="flex flex-col gap-2">
                        <span className="text-[10px] font-mono text-slate-400 uppercase font-semibold">Candle Colors</span>
                        <div className="flex items-center justify-between bg-slate-900/60 p-2 rounded-xl border border-white/5">
                            <span className="text-emerald-400 font-medium">Bullish (Up Candle)</span>
                            <input
                                type="color"
                                value={upColor}
                                onChange={(e) => setUpColor(e.target.value)}
                                className="w-6 h-6 rounded cursor-pointer bg-transparent border-0"
                            />
                        </div>
                        <div className="flex items-center justify-between bg-slate-900/60 p-2 rounded-xl border border-white/5">
                            <span className="text-rose-400 font-medium">Bearish (Down Candle)</span>
                            <input
                                type="color"
                                value={downColor}
                                onChange={(e) => setDownColor(e.target.value)}
                                className="w-6 h-6 rounded cursor-pointer bg-transparent border-0"
                            />
                        </div>
                    </div>

                    {/* Fibonacci Settings */}
                    <div className="flex flex-col gap-2 pt-2 border-t border-cyan-500/20">
                        <span className="text-[10px] font-mono text-slate-400 uppercase font-semibold">Fibonacci Retracement</span>
                        <div className="flex items-center justify-between bg-slate-900/60 p-2 rounded-xl border border-white/5">
                            <span className="text-cyan-300 font-medium">Fib Lines Color</span>
                            <input
                                type="color"
                                value={fibColor}
                                onChange={(e) => setFibColor(e.target.value)}
                                className="w-6 h-6 rounded cursor-pointer bg-transparent border-0"
                            />
                        </div>
                        <div className="flex items-center justify-between bg-slate-900/60 p-2 rounded-xl border border-white/5">
                            <span className="text-slate-300 font-medium">Extend Fib Lines</span>
                            <input
                                type="checkbox"
                                checked={fibExtend}
                                onChange={(e) => setFibExtend(e.target.checked)}
                                className="w-4 h-4 accent-cyan-500 cursor-pointer"
                            />
                        </div>
                    </div>

                    <button
                        onClick={() => setShowSettings(false)}
                        className="w-full py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-mono text-xs font-bold transition-all cursor-pointer shadow-md"
                    >
                        Apply & Save Settings
                    </button>
                </div>
            )}

            {/* Cyber Grid Background Pattern */}
            <div 
                className="absolute inset-0 pointer-events-none opacity-20 z-0"
                style={{
                    backgroundImage: `
                        linear-gradient(to right, rgba(0, 183, 255, 0.2) 1px, transparent 1px),
                        linear-gradient(to bottom, rgba(0, 183, 255, 0.2) 1px, transparent 1px)
                    `,
                    backgroundSize: '40px 40px'
                }}
            />

            <div id="tradingview_widget_container" ref={containerRef} className="w-full h-full relative z-10" />
        </div>
    );
}
