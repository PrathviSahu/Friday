import React, { useEffect, useRef } from 'react';

// Free real-time streamable symbols (Indices, Forex, Commodities, Crypto)
const FREE_REALTIME_WATCHLIST = [
    'OANDA:XAUUSD',     // Gold Spot (100% free live real-time)
    'CAPITALCOM:DXY',   // US Dollar Index
    'TVC:US10Y',        // US 10-Year Yield
    'BINANCE:BTCUSDT',  // Bitcoin
    'BINANCE:ETHUSDT',  // Ethereum
    'BINANCE:SOLUSDT',  // Solana
    'FX:EURUSD',        // EUR/USD
    'FX:GBPUSD',        // GBP/USD
    'FX:USDJPY',        // USD/JPY
    'FOREXCOM:SPXUSD',  // S&P 500
    'FOREXCOM:NSXUSD',  // NASDAQ 100
    'NSE:NIFTY',        // NIFTY 50
    'NSE:BANKNIFTY',   // BANK NIFTY
    'NSE:RELIANCE',    // Reliance
    'NSE:TCS',         // TCS
    'NSE:INFY',        // Infosys
    'NSE:HDFCBANK',    // HDFC Bank
];

export default function ProfessionalChart() {
    const containerRef = useRef(null);

    useEffect(() => {
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
                    hide_side_toolbar: false,
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
                    gridColor: 'rgba(56, 189, 248, 0.15)', // Visible Cyber-Grid
                    overrides: {
                        "paneProperties.vertGridProperties.color": "rgba(56, 189, 248, 0.15)",
                        "paneProperties.vertGridProperties.style": 0,
                        "paneProperties.horzGridProperties.color": "rgba(56, 189, 248, 0.15)",
                        "paneProperties.horzGridProperties.style": 0,
                        "mainSeriesProperties.style": 1,
                    }
                });
            }
        };

        containerRef.current.appendChild(script);
    }, []);

    return (
        <div className="flex-1 w-full h-full bg-[#0a0f1d] relative overflow-hidden">
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
