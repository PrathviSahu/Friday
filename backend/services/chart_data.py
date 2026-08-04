"""chart_data.py — shared OHLCV candle fetching & symbol search.

Extracted from the monolithic app.py so that the trading routes, the
technical-analysis engine, and the function-calling brain all share one
symbol/interval resolution layer (TradingView-style symbol → Yahoo ticker).
"""

import logging

# TradingView symbol → Yahoo Finance ticker (Forex-first)
SYMBOL_MAP = {
    # Forex major pairs
    'FX:EURUSD': 'EURUSD=X', 'FX:GBPUSD': 'GBPUSD=X', 'FX:USDJPY': 'JPY=X',
    'FX:USDCHF': 'CHF=X',    'FX:USDCAD': 'CAD=X',    'FX:AUDUSD': 'AUDUSD=X',
    'FX:NZDUSD': 'NZDUSD=X',
    # Forex cross pairs
    'FX:EURJPY': 'EURJPY=X', 'FX:GBPJPY': 'GBPJPY=X', 'FX:EURGBP': 'EURGBP=X',
    'FX:EURAUD': 'EURAUD=X',
    # Commodities & Indices
    'OANDA:XAUUSD': 'GC=F', 'OANDA:XAGUSD': 'SI=F', 'NYMEX:CL1!': 'CL=F',
    'OANDA:NAS100USD': '^NDX', 'OANDA:SPX500USD': '^GSPC', 'CAPITALCOM:DXY': 'DX-Y.NYB',
    'OANDA:UK100GBP': '^FTSE', 'OANDA:DE30EUR': '^GDAXI',
    # Crypto
    'BINANCE:BTCUSDT': 'BTC-USD', 'BINANCE:ETHUSDT': 'ETH-USD',
    'BINANCE:SOLUSDT': 'SOL-USD',  'BINANCE:BNBUSDT': 'BNB-USD',
    # US Stocks
    'NASDAQ:AAPL': 'AAPL', 'NASDAQ:TSLA': 'TSLA', 'NASDAQ:NVDA': 'NVDA',
    'NASDAQ:META': 'META', 'NASDAQ:AMZN': 'AMZN', 'NASDAQ:MSFT': 'MSFT',
    'NASDAQ:GOOGL': 'GOOGL', 'NYSE:JPM': 'JPM', 'NYSE:GS': 'GS',
}

# TV interval → (yfinance_period, yfinance_interval)
# Forex = 24/5, use tighter windows so data is always fresh
INTERVAL_MAP = {
    '1':   ('2d',  '1m'),   # last 2 days of 1-minute candles
    '5':   ('5d',  '5m'),   # 5 days of 5-minute candles
    '15':  ('10d', '15m'),  # 10 days of 15-minute candles
    '30':  ('20d', '30m'),  # 20 days of 30-minute candles
    '60':  ('60d', '60m'),  # 60 days of 1-hour candles
    '240': ('60d', '60m'),  # 4H: fetch 1H and client resamples — yfinance has no 4H
    'D':   ('2y',  '1d'),   # 2 years of daily
    'W':   ('5y',  '1wk'),  # 5 years of weekly
}


def resolve_ticker(symbol: str) -> str:
    """Map a TradingView-style symbol to a Yahoo Finance ticker."""
    return SYMBOL_MAP.get(symbol, symbol)


def fetch_ohlcv(symbol: str = "FX:EURUSD", interval: str = "5") -> dict:
    """Fetch OHLCV candles for a symbol at a given TradingView interval.

    Returns a dict with "candles" (list of {time, open, high, low, close,
    volume}) plus metadata. On failure returns {"candles": [], "error": ...}.
    """
    import yfinance as yf

    yf_interval_key = str(interval)
    period, yf_interval = INTERVAL_MAP.get(yf_interval_key, ('5d', '5m'))
    yf_ticker = resolve_ticker(symbol)

    # Decimal precision: Forex = 5dp, JPY pairs = 3dp, others = 4dp
    is_jpy = 'JPY' in symbol.upper()
    is_fx = symbol.startswith('FX:')
    digits = 3 if is_jpy else (5 if is_fx else 4)

    try:
        tk = yf.Ticker(yf_ticker)
        df = tk.history(period=period, interval=yf_interval, auto_adjust=True)
        if df is None or df.empty:
            return {"candles": [], "symbol": symbol, "yf_ticker": yf_ticker,
                    "error": "No data returned"}

        candles = []
        for ts, row in df.iterrows():
            candles.append({
                "time":   int(ts.timestamp()),
                "open":   round(float(row['Open']),  digits),
                "high":   round(float(row['High']),  digits),
                "low":    round(float(row['Low']),   digits),
                "close":  round(float(row['Close']), digits),
                "volume": int(row.get('Volume', 0) or 0),
            })

        logging.info(f"[OHLCV] {symbol} ({yf_ticker}) {yf_interval}/{period} → {len(candles)} candles")
        return {"candles": candles, "symbol": symbol, "yf_ticker": yf_ticker,
                "interval": yf_interval, "count": len(candles)}
    except Exception as e:
        logging.warning(f"[OHLCV] Error fetching {yf_ticker}: {e}")
        return {"candles": [], "symbol": symbol, "error": str(e)}


def search_symbols(q: str = "") -> list:
    """Search the full universe (NSE/BSE/Forex/Crypto/US stocks) via Yahoo."""
    import yfinance as yf

    query = (q or "").strip()
    if not query:
        return []

    results = []
    seen = set()

    def add_item(sym, name_str, exch_str, type_str):
        if not sym or sym in seen:
            return
        seen.add(sym)

        if sym.endswith(".NS"):
            ticker = sym[:-3]
            tv_symbol, exchange, stype = f"NSE:{ticker}", "NSE", "stock"
            logo_img = f"https://www.google.com/s2/favicons?domain={ticker.lower()}.com&sz=64"
            logo_img2 = "https://flagcdn.com/h24/in.png"
        elif sym.endswith(".BO"):
            ticker = sym[:-3]
            tv_symbol, exchange, stype = f"BSE:{ticker}", "BSE", "stock"
            logo_img = f"https://www.google.com/s2/favicons?domain={ticker.lower()}.com&sz=64"
            logo_img2 = "https://flagcdn.com/h24/in.png"
        elif "=X" in sym:
            tv_symbol = f"FX:{sym.replace('=X', '')}"
            exchange, stype = "FX", "forex"
            logo_img, logo_img2 = "https://flagcdn.com/h24/eu.png", "https://flagcdn.com/h24/us.png"
        elif "-USD" in sym:
            ticker = sym.replace("-USD", "USDT")
            tv_symbol = f"BINANCE:{ticker}"
            exchange, stype = "BINANCE", "crypto"
            logo_img = "https://assets.coingecko.com/coins/images/1/small/bitcoin.png"
            logo_img2 = None
        else:
            clean_sym = sym.replace("^", "")
            tv_symbol = f"NASDAQ:{clean_sym}" if "NASDAQ" in exch_str.upper() else f"NYSE:{clean_sym}"
            exchange = "NASDAQ" if "NASDAQ" in exch_str.upper() else ("NSE" if "NSE" in exch_str.upper() else "NYSE")
            stype = "stock"
            logo_img = f"https://www.google.com/s2/favicons?domain={clean_sym.lower()}.com&sz=64"
            logo_img2 = "https://flagcdn.com/h24/us.png"

        results.append({
            "symbol": tv_symbol,
            "name": sym.replace(".NS", "").replace(".BO", "").replace("^", ""),
            "full": name_str or sym,
            "type": stype,
            "exchange": exchange,
            "logoImg": logo_img,
            "logoImg2": logo_img2,
            "logoBg": "#1d4ed8" if "NSE" in exchange or "BSE" in exchange else "#0891b2",
            "isPositive": True,
        })

    try:
        yf_search = yf.Search(query, max_results=12)
        for item in yf_search.quotes:
            add_item(item.get("symbol"),
                     item.get("shortname") or item.get("longname") or item.get("symbol"),
                     item.get("exchDisp") or "",
                     item.get("quoteType") or "")
    except Exception as e:
        logging.warning(f"[yfinance Search Warning] {e}")

    if not results:
        try:
            import requests
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={requests.utils.quote(query)}&quotesCount=12"
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
            resp = requests.get(url, headers=headers, timeout=4)
            if resp.ok:
                for item in resp.json().get("quotes", []):
                    add_item(item.get("symbol"),
                             item.get("shortname") or item.get("longname") or item.get("symbol"),
                             item.get("exchDisp") or "",
                             item.get("quoteType") or "")
        except Exception as err:
            logging.warning(f"[Direct Search Error] {err}")

    return results
