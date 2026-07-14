// Front-end market data service. Talks to our FastAPI proxy (which fetches
// Yahoo Finance), never to Yahoo directly — avoids CORS and API keys.

const API = '/api/market';

export async function fetchKlines(symbol, interval = '5m') {
    const res = await fetch(`${API}/klines?symbol=${encodeURIComponent(symbol)}&interval=${encodeURIComponent(interval)}`);
    if (!res.ok) throw new Error(`klines ${res.status}`);
    return res.json();
}

export async function fetchQuotes(symbols) {
    if (!symbols || !symbols.length) return [];
    const res = await fetch(`${API}/quote?symbols=${encodeURIComponent(symbols.join(','))}`);
    if (!res.ok) throw new Error(`quote ${res.status}`);
    return res.json();
}

export async function searchSymbols(query) {
    const res = await fetch(`${API}/search?q=${encodeURIComponent(query)}`);
    if (!res.ok) throw new Error(`search ${res.status}`);
    return res.json();
}

// Strip Yahoo exchange suffixes for a clean label: RELIANCE.NS -> RELIANCE,
// USDINR=X -> USDINR, ^NSEI -> NSEI.
export function formatSymbol(symbol = '') {
    return symbol
        .replace(/\.NS$/, '')
        .replace(/\.BO$/, '')
        .replace(/=X$/, '')
        .replace(/\^/g, '');
}

export const INTERVALS = ['1m', '5m', '15m', '1h', '1d'];

export const DEFAULT_WATCHLIST = [
    'RELIANCE.NS',
    'INFY.NS',
    'TCS.NS',
    'HDFCBANK.NS',
    'ICICIBANK.NS',
    'WIPRO.NS',
    'TATAMOTORS.NS',
    'USDINR=X',
    'EURINR=X',
    '^NSEI',
];
