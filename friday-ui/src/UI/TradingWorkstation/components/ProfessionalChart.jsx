import React, { useEffect, useRef, useState } from 'react';

export default function ProfessionalChart({ symbol = 'FX:EURUSD', interval = '5' }) {
    const containerRef = useRef(null);
    const widgetRef    = useRef(null);
    const [error, setError] = useState(false);

    const getTvSymbol = (sym) => {
        if (!sym) return 'FX:EURUSD';
        if (sym === 'EURUSD') return 'FX:EURUSD';
        if (sym === 'GBPUSD') return 'FX:GBPUSD';
        if (sym === 'USDJPY') return 'FX:USDJPY';
        if (sym === 'XAUUSD') return 'OANDA:XAUUSD';
        if (sym === 'BTCUSD' || sym === 'BTCUSDT') return 'BINANCE:BTCUSDT';
        if (sym === 'NASDAQ' || sym === 'NAS100') return 'OANDA:NAS100USD';
        if (sym === 'DXY') return 'CAPITALCOM:DXY';
        return sym;
    };

    const getTvInterval = (intv) => {
        if (!intv) return '5';
        if (intv === '1h' || intv === '60') return '60';
        if (intv === '4h' || intv === '240') return '240';
        if (intv === '1D' || intv === 'D') return 'D';
        if (intv === '1W' || intv === 'W') return 'W';
        return intv;
    };

    const tvSymbol   = getTvSymbol(symbol);
    const tvInterval = getTvInterval(interval);

    useEffect(() => {
        setError(false);
        if (!containerRef.current) return;

        // Unique container ID per mount to prevent stale DOM conflicts
        const uid = `tv_${Math.random().toString(36).slice(2, 9)}`;

        // Destroy previous widget instance
        if (widgetRef.current) {
            try { widgetRef.current.remove?.(); } catch (_) {}
            widgetRef.current = null;
        }
        containerRef.current.innerHTML = `<div id="${uid}" style="width:100%;height:100%;"></div>`;

        const initWidget = () => {
            const el = document.getElementById(uid);
            if (!el || !window.TradingView) return;
            try {
                widgetRef.current = new window.TradingView.widget({
                    autosize:            true,
                    symbol:              tvSymbol,
                    interval:            tvInterval,
                    timezone:            'Asia/Kolkata',
                    theme:               'dark',
                    style:               '1',
                    locale:              'en',
                    toolbar_bg:          '#131722',
                    enable_publishing:   false,
                    allow_symbol_change: true,
                    container_id:        uid,
                    backgroundColor:     '#131722',
                    gridColor:           'rgba(42, 46, 57, 0.5)',

                    // Disable features that try to access `.list` internals in the
                    // embedded widget context and trigger the TypeError crash
                    disabled_features: [
                        'widget_bar',
                        'timeframes_toolbar',
                        'go_to_date',
                        'display_market_status',
                        'header_saveload',
                        'header_screenshot',
                        'header_fullscreen_button',
                        'popup_hints',
                        'pane_context_menu',
                        'show_chart_property_page',
                        'items_favoriting',
                        'border_around_the_chart',
                        'chart_events',
                    ],
                    enabled_features: [
                        'header_widget',
                        'header_symbol_search',
                        'header_resolutions',
                        'header_chart_type',
                        'header_indicators',
                        'header_compare',
                        'header_undo_redo',
                        'study_templates',
                        'use_localstorage_for_settings',
                        'side_toolbar_in_fullscreen_mode',
                    ],
                    overrides: {
                        'mainSeriesProperties.candleStyle.upColor':         '#089981',
                        'mainSeriesProperties.candleStyle.downColor':       '#f23645',
                        'mainSeriesProperties.candleStyle.drawWick':        true,
                        'mainSeriesProperties.candleStyle.drawBorder':      true,
                        'mainSeriesProperties.candleStyle.borderUpColor':   '#089981',
                        'mainSeriesProperties.candleStyle.borderDownColor': '#f23645',
                        'mainSeriesProperties.candleStyle.wickUpColor':     '#089981',
                        'mainSeriesProperties.candleStyle.wickDownColor':   '#f23645',
                        'paneProperties.background':                        '#131722',
                        'paneProperties.vertGridProperties.color':          '#1e222d',
                        'paneProperties.horzGridProperties.color':          '#1e222d',
                    }
                });
            } catch (err) {
                console.warn('[ProfessionalChart] TradingView widget init error:', err);
                setError(true);
            }
        };

        let cleanup = () => {};

        if (window.TradingView) {
            const t = setTimeout(initWidget, 80);
            cleanup = () => clearTimeout(t);
        } else {
            const existing = document.getElementById('tradingview-tv-script');
            if (existing) {
                existing.addEventListener('load', initWidget);
                cleanup = () => existing.removeEventListener('load', initWidget);
            } else {
                const script = document.createElement('script');
                script.id    = 'tradingview-tv-script';
                script.src   = 'https://s3.tradingview.com/tv.js';
                script.async = true;
                script.onload = initWidget;
                document.head.appendChild(script);
            }
        }

        return () => {
            cleanup();
            if (widgetRef.current) {
                try { widgetRef.current.remove?.(); } catch (_) {}
                widgetRef.current = null;
            }
            if (containerRef.current) containerRef.current.innerHTML = '';
        };
    }, [tvSymbol, tvInterval]);

    if (error) {
        return (
            <div className="w-full h-full flex items-center justify-center bg-[#131722] text-[#00B7FF] font-orbitron text-sm tracking-widest">
                CHART UNAVAILABLE — RELOAD TO RETRY
            </div>
        );
    }

    return (
        <div className="w-full h-full relative bg-[#131722] overflow-hidden">
            <div ref={containerRef} className="w-full h-full" />
        </div>
    );
}
