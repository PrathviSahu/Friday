import React, { useEffect, useRef, useState } from 'react';
import { Sliders, X } from 'lucide-react';

// Free real-time streamable symbols (US NASDAQ, Indian NSE, Gold, Forex, Crypto)
const FULL_REALTIME_WATCHLIST = [
    'OANDA:XAUUSD',     // Gold Spot (Free live real-time)
    'NASDAQ:NDX',       // NASDAQ 100 Index
    'NASDAQ:NVDA',      // NVIDIA
    'NASDAQ:AAPL',      // Apple
    'NASDAQ:TSLA',      // Tesla
    'CAPITALCOM:DXY',   // US Dollar Index
    'BINANCE:BTCUSDT',  // Bitcoin
    'BINANCE:ETHUSDT',  // Ethereum
    'BINANCE:SOLUSDT',  // Solana
    'FX:EURUSD',        // EUR/USD
    'FX:GBPUSD',        // GBP/USD
    'NSE:NIFTY',        // NIFTY 50
    'NSE:BANKNIFTY',   // BANK NIFTY
    'NSE:RELIANCE',    // Reliance
    'NSE:TCS',         // TCS
    'NSE:INFY',        // Infosys
    'NSE:HDFCBANK',    // HDFC Bank
];

export default function ProfessionalChart() {
    const containerRef = useRef(null);
    const [contextMenu, setContextMenu] = useState(null);
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
                    watchlist: FULL_REALTIME_WATCHLIST,
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

    // Handle Right-Click Context Menu on Chart
    const handleContextMenu = (e) => {
        e.preventDefault();
        setContextMenu({ x: e.clientX, y: e.clientY });
    };

    return (
        <div 
            onContextMenu={handleContextMenu}
            onClick={() => setContextMenu(null)}
            className="flex-1 w-full h-full bg-[#0a0f1d] relative overflow-hidden"
        >
            {/* Right-Click Context Menu */}
            {contextMenu && (
                <div
                    style={{ top: contextMenu.y, left: contextMenu.x }}
                    className="fixed z-50 w-48 rounded-xl bg-[#080d1a]/95 border border-cyan-500/30 p-1.5 shadow-[0_10px_30px_rgba(0,0,0,0.8)] backdrop-blur-xl text-slate-200 text-xs font-sans select-none"
                >
                    <button
                        onClick={() => { setShowSettings(true); setContextMenu(null); }}
                        className="w-full text-left px-3 py-2 rounded-lg hover:bg-cyan-500/20 text-cyan-300 font-mono font-medium flex items-center justify-between cursor-pointer"
                    >
                        <span>⚙️ Settings & Color Customizer</span>
                    </button>
                    <div className="h-[1px] bg-cyan-500/15 my-1" />
                    <button
                        onClick={() => setContextMenu(null)}
                        className="w-full text-left px-3 py-1.5 rounded-lg hover:bg-slate-800 text-slate-400 text-[11px]"
                    >
                        Close Menu
                    </button>
                </div>
            )}

            {/* Customization Settings Modal (Triggered by Right Click) */}
            {showSettings && (
                <div className="absolute top-12 right-20 z-50 w-72 rounded-2xl bg-[#080d1a]/95 border border-cyan-500/30 p-4 shadow-[0_20px_60px_rgba(0,0,0,0.9)] backdrop-blur-2xl text-slate-100 font-sans text-xs flex flex-col gap-4 select-none">
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
