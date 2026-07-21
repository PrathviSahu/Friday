// Market assets dataset with categories: Forex, Crypto, Stocks, Indices, Commodities
export const MARKET_ASSETS = [
    // ── Forex ──
    { symbol: 'EURUSD=X', name: 'EUR/USD', category: 'Forex', basePrice: 1.0845, changePct: 0.18, bid: 1.0844, ask: 1.0846, spread: '0.2', sparkline: [1.082, 1.083, 1.0825, 1.084, 1.0845] },
    { symbol: 'GBPUSD=X', name: 'GBP/USD', category: 'Forex', basePrice: 1.2730, changePct: -0.25, bid: 1.2729, ask: 1.2731, spread: '0.3', sparkline: [1.276, 1.275, 1.274, 1.273, 1.2730] },
    { symbol: 'USDJPY=X', name: 'USD/JPY', category: 'Forex', basePrice: 156.40, changePct: 0.42, bid: 156.38, ask: 156.42, spread: '0.4', sparkline: [155.8, 156.0, 156.2, 156.3, 156.40] },
    { symbol: 'AUDUSD=X', name: 'AUD/USD', category: 'Forex', basePrice: 0.6650, changePct: 0.12, bid: 0.6649, ask: 0.6651, spread: '0.3', sparkline: [0.664, 0.6645, 0.6648, 0.6650] },

    // ── Crypto ──
    { symbol: 'BTC-USD', name: 'Bitcoin', category: 'Crypto', basePrice: 67450.0, changePct: 2.85, bid: 67448.0, ask: 67452.0, spread: '4.0', sparkline: [65200, 65800, 66400, 67100, 67450] },
    { symbol: 'ETH-USD', name: 'Ethereum', category: 'Crypto', basePrice: 3520.5, changePct: 1.94, bid: 3520.0, ask: 3521.0, spread: '1.0', sparkline: [3440, 3470, 3490, 3510, 3520.5] },
    { symbol: 'SOL-USD', name: 'Solana', category: 'Crypto', basePrice: 148.2, changePct: 4.12, bid: 148.1, ask: 148.3, spread: '0.2', sparkline: [142, 144, 145, 147, 148.2] },
    { symbol: 'BNB-USD', name: 'Binance Coin', category: 'Crypto', basePrice: 585.0, changePct: -0.85, bid: 584.8, ask: 585.2, spread: '0.4', sparkline: [591, 589, 587, 586, 585.0] },

    // ── Stocks ──
    { symbol: 'RELIANCE.NS', name: 'Reliance Industries', category: 'Stocks', basePrice: 2980.0, changePct: 1.45, bid: 2979.5, ask: 2980.5, spread: '1.0', sparkline: [2940, 2955, 2970, 2980] },
    { symbol: 'NVDA', name: 'NVIDIA Corp', category: 'Stocks', basePrice: 124.5, changePct: 3.65, bid: 124.4, ask: 124.6, spread: '0.2', sparkline: [119, 121, 123, 124.5] },
    { symbol: 'AAPL', name: 'Apple Inc', category: 'Stocks', basePrice: 224.2, changePct: 0.95, bid: 224.1, ask: 224.3, spread: '0.2', sparkline: [221, 222, 223.5, 224.2] },
    { symbol: 'TSLA', name: 'Tesla Inc', category: 'Stocks', basePrice: 254.8, changePct: -1.82, bid: 254.6, ask: 255.0, spread: '0.4', sparkline: [260, 258, 256, 254.8] },

    // ── Commodities ──
    { symbol: 'GC=F', name: 'Gold (XAU/USD)', category: 'Commodities', basePrice: 2345.6, changePct: 0.84, bid: 2345.4, ask: 2345.8, spread: '0.4', sparkline: [2325, 2330, 2338, 2345.6] },
    { symbol: 'CL=F', name: 'Crude Oil WTI', category: 'Commodities', basePrice: 81.40, changePct: -0.65, bid: 81.38, ask: 81.42, spread: '0.04', sparkline: [82.1, 81.9, 81.6, 81.40] },
    { symbol: 'SI=F', name: 'Silver Futures', category: 'Commodities', basePrice: 30.15, changePct: 1.22, bid: 30.14, ask: 30.16, spread: '0.02', sparkline: [29.7, 29.9, 30.0, 30.15] },

    // ── Indices ──
    { symbol: '^GSPC', name: 'S&P 500', category: 'Indices', basePrice: 5475.2, changePct: 0.45, bid: 5475.0, ask: 5475.4, spread: '0.4', sparkline: [5450, 5460, 5470, 5475.2] },
    { symbol: '^IXIC', name: 'NASDAQ Composite', category: 'Indices', basePrice: 17730.5, changePct: 0.78, bid: 17730.0, ask: 17731.0, spread: '1.0', sparkline: [17580, 17640, 17700, 17730.5] },
    { symbol: '^NSEI', name: 'NIFTY 50', category: 'Indices', basePrice: 23550.0, changePct: 0.62, bid: 23548.0, ask: 23552.0, spread: '4.0', sparkline: [23400, 23480, 23520, 23550] },
];

export const TECHNICAL_INDICATORS = [
    { id: 'EMA50', name: 'EMA 50', category: 'Trend', defaultColor: '#3b82f6' },
    { id: 'EMA200', name: 'EMA 200', category: 'Trend', defaultColor: '#ef4444' },
    { id: 'VWAP', name: 'VWAP', category: 'Volume', defaultColor: '#eab308' },
    { id: 'RSI', name: 'RSI (14)', category: 'Momentum', defaultColor: '#a855f7' },
    { id: 'MACD', name: 'MACD (12, 26, 9)', category: 'Momentum', defaultColor: '#06b6d4' },
    { id: 'Bollinger', name: 'Bollinger Bands (20, 2)', category: 'Volatility', defaultColor: '#10b981' },
    { id: 'Supertrend', name: 'Supertrend (10, 3)', category: 'Trend', defaultColor: '#f97316' },
    { id: 'ATR', name: 'ATR (14)', category: 'Volatility', defaultColor: '#ec4899' },
];

export const AI_PATTERNS = [
    { name: 'Bullish Flag', confidence: 92, type: 'Bullish', target: '+3.4%' },
    { name: 'Order Block (4H Demand)', confidence: 88, type: 'Institutional', target: 'Ref 2335' },
    { name: 'Fair Value Gap (FVG)', confidence: 95, type: 'Imbalance', target: 'Filled 50%' },
    { name: 'Break of Structure (BOS)', confidence: 89, type: 'Structure', target: 'Higher High' },
];

export const ECONOMIC_NEWS = [
    { id: 1, title: 'US Core CPI Inflation MoM', impact: 'High', time: '18:30', forecast: '0.3%', previous: '0.3%', currency: 'USD', sentiment: 'Hawkish' },
    { id: 2, title: 'FOMC Press Conference', impact: 'High', time: '23:30', forecast: '5.50%', previous: '5.50%', currency: 'USD', sentiment: 'Volatile' },
    { id: 3, title: 'ECB Interest Rate Decision', impact: 'Medium', time: '17:45', forecast: '4.25%', previous: '4.50%', currency: 'EUR', sentiment: 'Dovish' },
    { id: 4, title: 'India Manufacturing PMI', impact: 'Low', time: '10:30', forecast: '58.4', previous: '57.9', currency: 'INR', sentiment: 'Bullish' },
];
