import React, { useEffect, useRef } from 'react';

// Maps user symbols to official TradingView widget symbols with focus on Indian Stock Market (NSE / BSE / NIFTY / BANKNIFTY)
const SYMBOL_MAP = {
    'NIFTY': 'NSE:NIFTY',
    'NIFTY50': 'NSE:NIFTY',
    'BANKNIFTY': 'NSE:BANKNIFTY',
    'FINNIFTY': 'NSE:FINNIFTY',
    'RELIANCE': 'NSE:RELIANCE',
    'TCS': 'NSE:TCS',
    'INFY': 'NSE:INFY',
    'HDFCBANK': 'NSE:HDFCBANK',
    'ICICIBANK': 'NSE:ICICIBANK',
    'SBIN': 'NSE:SBIN',
    'TATAMOTORS': 'NSE:TATAMOTORS',
    'TATASTEEL': 'NSE:TATASTEEL',
    'BHARTIARTL': 'NSE:BHARTIARTL',
    'ITC': 'NSE:ITC',
    'LIKHITH': 'NSE:LIKHITH',
    'DBOL': 'NSE:DBOL',
    'TITAGARH': 'NSE:TITAGARH',
    'XAUUSD': 'OANDA:XAUUSD',
    'GOLD': 'OANDA:XAUUSD',
    'BTCUSD': 'BINANCE:BTCUSDT',
};

export default function ProfessionalChart({ symbol = 'NSE:NIFTY' }) {
    const containerRef = useRef(null);

    const tvSymbol = SYMBOL_MAP[symbol] || (symbol.includes(':') ? symbol : `NSE:${symbol.replace(/[^a-zA-Z0-9]/g, '')}`);

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
                    symbol: tvSymbol,
                    interval: '5',
                    timezone: 'Asia/Kolkata',
                    theme: 'dark',
                    style: '1',
                    locale: 'in',
                    toolbar_bg: '#080d1a',
                    enable_publishing: false,
                    hide_side_toolbar: false, // Show professional drawing tools
                    allow_symbol_change: true,
                    details: true,
                    hotlist: true,
                    calendar: true,
                    show_popup_button: true,
                    popup_width: '1000',
                    popup_height: '650',
                    container_id: 'tradingview_widget_container',
                    backgroundColor: '#080d1a',
                    gridColor: 'rgba(30, 41, 59, 0.3)',
                });
            }
        };

        containerRef.current.appendChild(script);
    }, [tvSymbol]);

    return (
        <div className="flex-1 w-full h-full bg-[#080d1a] relative overflow-hidden">
            <div id="tradingview_widget_container" ref={containerRef} className="w-full h-full" />
        </div>
    );
}
