import React, { useEffect, useRef, useState } from 'react';
import { Sliders, X } from 'lucide-react';

export default function ProfessionalChart({ symbol = 'OANDA:XAUUSD' }) {
    const containerRef = useRef(null);
    const [contextMenu, setContextMenu] = useState(null);
    const [showSettings, setShowSettings] = useState(false);

    // Customizable Candle & Drawing Settings
    const [upColor, setUpColor] = useState('#089981');
    const [downColor, setDownColor] = useState('#f23645');
    const [fibColor, setFibColor] = useState('#00b7ff');
    const [fibExtend, setFibExtend] = useState(true);

    const initWidget = () => {
        if (!containerRef.current || !window.TradingView) return;
        containerRef.current.innerHTML = '';

        new window.TradingView.widget({
            autosize: true,
            symbol: symbol,
            interval: '5',
            timezone: 'Asia/Kolkata',
            theme: 'dark',
            style: '1',
            locale: 'en',
            toolbar_bg: '#131722',
            enable_publishing: false,
            hide_side_toolbar: false, // Show left drawing toolbar (Trendlines, Fibs, Position tools)
            allow_symbol_change: true,
            details: false,           // DISABLE TradingView inner details sidebar
            hotlist: false,           // DISABLE TradingView inner hotlist sidebar
            calendar: false,          // DISABLE TradingView inner calendar sidebar
            show_popup_button: true,
            popup_width: '1000',
            popup_height: '650',
            container_id: 'tradingview_widget_element',
            backgroundColor: '#0a0f1d',
            gridColor: 'rgba(56, 189, 248, 0.15)',
            disabled_features: [
                'header_widget_dom_node',
                'trading_notifications'
            ],
            enabled_features: [
                'study_templates',
                'use_localstorage_for_settings',
                'side_toolbar_in_fullscreen_mode',
                'items_favoriting'
            ],
            overrides: {
                "mainSeriesProperties.candleStyle.upColor": upColor,
                "mainSeriesProperties.candleStyle.downColor": downColor,
                "mainSeriesProperties.candleStyle.drawWick": true,
                "mainSeriesProperties.candleStyle.drawBorder": true,
                "mainSeriesProperties.candleStyle.borderColor": "#378658",
                "mainSeriesProperties.candleStyle.borderUpColor": upColor,
                "mainSeriesProperties.candleStyle.borderDownColor": downColor,
                "mainSeriesProperties.candleStyle.wickUpColor": upColor,
                "mainSeriesProperties.candleStyle.wickDownColor": downColor,
                "linetoolfibretracement.linecolor": fibColor,
                "linetoolfibretracement.extendLines": fibExtend,
                "paneProperties.vertGridProperties.color": "rgba(56, 189, 248, 0.15)",
                "paneProperties.horzGridProperties.color": "rgba(56, 189, 248, 0.15)",
            }
        });
    };

    useEffect(() => {
        if (window.TradingView) {
            initWidget();
            return;
        }

        const existingScript = document.getElementById('tradingview-tv-script');
        if (existingScript) {
            existingScript.addEventListener('load', initWidget);
            return;
        }

        const script = document.createElement('script');
        script.id = 'tradingview-tv-script';
        script.src = 'https://s3.tradingview.com/tv.js';
        script.async = true;
        script.onload = () => {
            initWidget();
        };
        document.head.appendChild(script);
    }, [symbol, upColor, downColor, fibColor, fibExtend]);

    const handleContextMenu = (e) => {
        e.preventDefault();
        setContextMenu({ x: e.clientX, y: e.clientY });
    };

    return (
        <div 
            onContextMenu={handleContextMenu}
            onClick={() => setContextMenu(null)}
            className="w-full h-full bg-[#0a0f1d] relative overflow-hidden"
            style={{ width: '100%', height: '100%', minHeight: '500px' }}
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

            {/* Customization Settings Modal */}
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

            <div id="tradingview_widget_element" ref={containerRef} className="w-full h-full relative z-10" />
        </div>
    );
}
