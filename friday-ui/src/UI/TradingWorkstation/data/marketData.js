// Forex-first Market Assets — clean, fast, always-live (24/5 market)
export const MARKET_ASSETS = [
    // ── Major Forex Pairs ──
    { symbol: 'FX:EURUSD', name: 'EUR/USD', category: 'Forex', exchange: 'FX', full: 'Euro / U.S. Dollar',          basePrice: 1.0865, pip: 0.0001, digits: 5 },
    { symbol: 'FX:GBPUSD', name: 'GBP/USD', category: 'Forex', exchange: 'FX', full: 'British Pound / U.S. Dollar', basePrice: 1.2720, pip: 0.0001, digits: 5 },
    { symbol: 'FX:USDJPY', name: 'USD/JPY', category: 'Forex', exchange: 'FX', full: 'U.S. Dollar / Japanese Yen',  basePrice: 156.40, pip: 0.01,   digits: 3 },
    { symbol: 'FX:USDCHF', name: 'USD/CHF', category: 'Forex', exchange: 'FX', full: 'U.S. Dollar / Swiss Franc',   basePrice: 0.8975, pip: 0.0001, digits: 5 },
    { symbol: 'FX:USDCAD', name: 'USD/CAD', category: 'Forex', exchange: 'FX', full: 'U.S. Dollar / Canadian Dollar',basePrice: 1.3650, pip: 0.0001, digits: 5 },
    { symbol: 'FX:AUDUSD', name: 'AUD/USD', category: 'Forex', exchange: 'FX', full: 'Australian Dollar / U.S. Dollar', basePrice: 0.6590, pip: 0.0001, digits: 5 },
    { symbol: 'FX:NZDUSD', name: 'NZD/USD', category: 'Forex', exchange: 'FX', full: 'New Zealand Dollar / U.S. Dollar', basePrice: 0.6120, pip: 0.0001, digits: 5 },

    // ── Cross Pairs ──
    { symbol: 'FX:EURJPY', name: 'EUR/JPY', category: 'Forex', exchange: 'FX', full: 'Euro / Japanese Yen',         basePrice: 169.90, pip: 0.01,   digits: 3 },
    { symbol: 'FX:GBPJPY', name: 'GBP/JPY', category: 'Forex', exchange: 'FX', full: 'British Pound / Japanese Yen', basePrice: 198.80, pip: 0.01,   digits: 3 },
    { symbol: 'FX:EURGBP', name: 'EUR/GBP', category: 'Forex', exchange: 'FX', full: 'Euro / British Pound',         basePrice: 0.8540, pip: 0.0001, digits: 5 },
    { symbol: 'FX:EURAUD', name: 'EUR/AUD', category: 'Forex', exchange: 'FX', full: 'Euro / Australian Dollar',     basePrice: 1.6490, pip: 0.0001, digits: 5 },

    // ── Key Instruments ──
    { symbol: 'OANDA:XAUUSD',  name: 'XAU/USD', category: 'Commodity', exchange: 'OANDA',   full: 'Gold Spot / U.S. Dollar',  basePrice: 2340.0, pip: 0.01,   digits: 2 },
    { symbol: 'CAPITALCOM:DXY', name: 'DXY',    category: 'Index',     exchange: 'CAPITALCOM', full: 'U.S. Dollar Index',      basePrice: 104.20, pip: 0.001,  digits: 3 },
];

export const TIMEFRAMES = [
    { label: '1m',  value: '1' },
    { label: '5m',  value: '5' },
    { label: '15m', value: '15' },
    { label: '30m', value: '30' },
    { label: '1h',  value: '60' },
    { label: '4h',  value: '240' },
    { label: '1D',  value: 'D' },
    { label: '1W',  value: 'W' },
];

// Flag mapping for Forex pair symbols
export const PAIR_FLAGS = {
    'EUR': 'eu', 'GBP': 'gb', 'USD': 'us', 'JPY': 'jp',
    'CHF': 'ch', 'CAD': 'ca', 'AUD': 'au', 'NZD': 'nz',
    'XAU': null,  // Gold — use icon
};
