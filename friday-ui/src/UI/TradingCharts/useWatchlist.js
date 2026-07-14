import { useState, useCallback, useEffect } from 'react';
import { DEFAULT_WATCHLIST } from '../../services/market';

const KEY = 'friday_watchlist';

export function useWatchlist() {
    const [symbols, setSymbols] = useState(() => {
        try {
            const raw = localStorage.getItem(KEY);
            if (raw) {
                const arr = JSON.parse(raw);
                if (Array.isArray(arr) && arr.length) return arr;
            }
        } catch {
            /* ignore */
        }
        return [...DEFAULT_WATCHLIST];
    });

    useEffect(() => {
        try {
            localStorage.setItem(KEY, JSON.stringify(symbols));
        } catch {
            /* ignore */
        }
    }, [symbols]);

    const add = useCallback((symbol) => {
        setSymbols((prev) => (prev.includes(symbol) ? prev : [...prev, symbol]));
    }, []);

    const remove = useCallback((symbol) => {
        setSymbols((prev) => prev.filter((s) => s !== symbol));
    }, []);

    const has = useCallback((symbol) => symbols.includes(symbol), [symbols]);

    return { symbols, add, remove, has };
}
