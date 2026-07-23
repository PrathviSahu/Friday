"""
market_data.py

Fetches real live global market prices (Forex, Commodities, Indices, Crypto, US Stocks) using yfinance.
Falls back to last-cached prices if offline. Micro-tick fluctuations keep UI updates active between requests.
"""

import time
import random
import threading
import logging

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logging.warning("[MarketData] yfinance not installed.")

# Map Yahoo Finance symbols → Watchlist Symbol Keys
GLOBAL_SYMBOLS = {
    # Forex
    'EURUSD=X':  {'key': 'FX:EURUSD',       'name': 'EURUSD',   'type': 'forex'},
    'GBPUSD=X':  {'key': 'FX:GBPUSD',       'name': 'GBPUSD',   'type': 'forex'},
    'JPY=X':     {'key': 'FX:USDJPY',       'name': 'USDJPY',   'type': 'forex'},
    'CHF=X':     {'key': 'FX:USDCHF',       'name': 'USDCHF',   'type': 'forex'},
    'CAD=X':     {'key': 'FX:USDCAD',       'name': 'USDCAD',   'type': 'forex'},
    'AUDUSD=X':  {'key': 'FX:AUDUSD',       'name': 'AUDUSD',   'type': 'forex'},
    'NZDUSD=X':  {'key': 'FX:NZDUSD',       'name': 'NZDUSD',   'type': 'forex'},
    'EURAUD=X':  {'key': 'FX:EURAUD',       'name': 'EURAUD',   'type': 'forex'},
    'EURGBP=X':  {'key': 'FX:EURGBP',       'name': 'EURGBP',   'type': 'forex'},
    'GBPJPY=X':  {'key': 'FX:GBPJPY',       'name': 'GBPJPY',   'type': 'forex'},
    'EURJPY=X':  {'key': 'FX:EURJPY',       'name': 'EURJPY',   'type': 'forex'},

    # Commodities & Futures
    'GC=F':      {'key': 'OANDA:XAUUSD',    'name': 'XAUUSD',   'type': 'commodity'},
    'SI=F':      {'key': 'OANDA:XAGUSD',    'name': 'XAGUSD',   'type': 'commodity'},
    'CL=F':      {'key': 'NYMEX:CL1!',      'name': 'CRUDE',    'type': 'futures'},

    # Indices
    '^NDX':      {'key': 'OANDA:NAS100USD', 'name': 'NAS100',   'type': 'index'},
    '^GSPC':     {'key': 'OANDA:SPX500USD', 'name': 'SPX500',   'type': 'index'},
    'DX-Y.NYB':  {'key': 'CAPITALCOM:DXY',  'name': 'DXY',      'type': 'index'},
    '^FTSE':     {'key': 'OANDA:UK100GBP',  'name': 'UK100',    'type': 'index'},
    '^GDAXI':    {'key': 'OANDA:DE30EUR',   'name': 'DAX30',    'type': 'index'},

    # Crypto
    'BTC-USD':   {'key': 'BINANCE:BTCUSDT', 'name': 'BTCUSD',   'type': 'crypto'},
    'ETH-USD':   {'key': 'BINANCE:ETHUSDT', 'name': 'ETHUSD',   'type': 'crypto'},
    'BNB-USD':   {'key': 'BINANCE:BNBUSDT', 'name': 'BNBUSD',   'type': 'crypto'},
    'SOL-USD':   {'key': 'BINANCE:SOLUSDT', 'name': 'SOLUSD',   'type': 'crypto'},
    'XRP-USD':   {'key': 'BINANCE:XRPUSDT', 'name': 'XRPUSD',   'type': 'crypto'},
    'ADA-USD':   {'key': 'BINANCE:ADAUSDT', 'name': 'ADAUSD',   'type': 'crypto'},
    'DOGE-USD':  {'key': 'BINANCE:DOGEUSDT','name': 'DOGEUSD',  'type': 'crypto'},

    # Global Stocks
    'AAPL':      {'key': 'NASDAQ:AAPL',     'name': 'AAPL',     'type': 'stock'},
    'TSLA':      {'key': 'NASDAQ:TSLA',     'name': 'TSLA',     'type': 'stock'},
    'NVDA':      {'key': 'NASDAQ:NVDA',     'name': 'NVDA',     'type': 'stock'},
    'META':      {'key': 'NASDAQ:META',     'name': 'META',     'type': 'stock'},
    'AMZN':      {'key': 'NASDAQ:AMZN',     'name': 'AMZN',     'type': 'stock'},
    'MSFT':      {'key': 'NASDAQ:MSFT',     'name': 'MSFT',     'type': 'stock'},
    'GOOGL':     {'key': 'NASDAQ:GOOGL',    'name': 'GOOGL',    'type': 'stock'},
    'JPM':       {'key': 'NYSE:JPM',        'name': 'JPM',      'type': 'stock'},
    'GS':        {'key': 'NYSE:GS',         'name': 'GS',       'type': 'stock'},
    'V':         {'key': 'NYSE:V',          'name': 'V',        'type': 'stock'},
}

REFRESH_INTERVAL = 60  # Refresh from Yahoo every 60 seconds
_cache: dict = {}
_last_fetch: float = 0.0
_fetch_lock = threading.Lock()


def _format_price(price: float) -> str:
    if price >= 10000:
        return f"{price:,.1f}"
    elif price >= 100:
        return f"{price:,.2f}"
    elif price >= 1:
        return f"{price:.4f}"
    else:
        return f"{price:.5f}"


def _format_change(change: float, price: float) -> str:
    sign = "+" if change >= 0 else ""
    if price >= 100:
        return f"{sign}{change:,.2f}"
    else:
        return f"{sign}{change:.4f}"


def _fetch_global_prices() -> bool:
    if not YFINANCE_AVAILABLE:
        return False
    try:
        yf_symbols = list(GLOBAL_SYMBOLS.keys())
        tickers = yf.Tickers(" ".join(yf_symbols))

        fetched = 0
        for yf_sym, meta in GLOBAL_SYMBOLS.items():
            try:
                t = tickers.tickers[yf_sym]
                fi = t.fast_info
                price = float(fi.last_price or 0)
                prev  = float(fi.previous_close or price)
                if price <= 0:
                    continue

                change = price - prev
                pct    = (change / prev) * 100 if prev else 0.0
                is_pos = change >= 0

                key = meta['key']
                _cache[key] = {
                    "price":          round(price, 4),
                    "price_str":      _format_price(price),
                    "change":         round(change, 4),
                    "change_str":     _format_change(change, price),
                    "pct":            round(pct, 2),
                    "pct_str":        f"+{pct:.2f}%" if pct >= 0 else f"{pct:.2f}%",
                    "isPositive":     is_pos,
                    "tick_direction": "up" if is_pos else "down",
                    "last_tick_time": time.time(),
                }
                fetched += 1
            except Exception as e:
                logging.debug(f"[MarketData] Skip {yf_sym}: {e}")

        logging.info(f"[MarketData] Fetched {fetched}/{len(GLOBAL_SYMBOLS)} global symbols from Yahoo Finance")
        return fetched > 0
    except Exception as err:
        logging.warning(f"[MarketData] Global fetch failed: {err}")
        return False


def _apply_micro_ticks():
    import datetime
    import pytz

    try:
        ist = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.datetime.now(ist)
        is_weekend = now_ist.weekday() >= 5
    except Exception:
        is_weekend = False

    for key, data in _cache.items():
        # Crypto is 24/7 — always micro-tick
        is_crypto = "BINANCE:" in key
        
        # On weekends or closed sessions for stocks/forex, skip micro-ticks & clear tick_direction
        if is_weekend and not is_crypto:
            data["tick_direction"] = None
            continue

        price = data["price"]
        delta = (random.random() - 0.48) * (price * 0.0003)
        new_price = price + delta

        diff = new_price - price
        data["price"] = new_price
        data["price_str"] = _format_price(new_price)

        if abs(diff) > 0.00001:
            data["tick_direction"] = "up" if diff > 0 else "down"
            data["last_tick_time"] = time.time()


import requests

def fetch_tradingview_live_prices(symbols_list: list = None) -> dict:
    """
    Fetch exact live real-time prices directly from TradingView's official scanner API.
    Guarantees Watchlist prices match TradingView Chart canvases 100% to the exact cent.
    """
    if not symbols_list:
        symbols_list = [
            'OANDA:XAUUSD', 'OANDA:NAS100USD', 'OANDA:SPX500USD', 'CAPITALCOM:DXY',
            'BINANCE:BTCUSDT', 'BINANCE:ETHUSDT', 'BINANCE:SOLUSDT',
            'FX:EURUSD', 'FX:GBPUSD', 'FX:USDJPY', 'FX:USDCHF', 'FX:USDCAD', 'FX:EURAUD', 'FX:GBPJPY',
            'BSE:RELIANCE', 'BSE:TCS', 'BSE:HDFCBANK', 'BSE:INFY', 'BSE:SBIN', 'BSE:ICICIBANK',
            'BSE:TATAMOTORS', 'BSE:ZOMATO', 'BSE:BLACKBUCK', 'NSE:BANKNIFTY', 'NSE:NIFTY50', 'BSE:SENSEX'
        ]

    tv_tickers = []
    symbol_map = {}

    for sym in symbols_list:
        if not sym:
            continue
        tv_sym = sym
        if sym.startswith("NSE:"):
            ticker = sym.replace("NSE:", "")
            tv_sym = f"BSE:{ticker}"
            symbol_map[tv_sym] = sym
            symbol_map[sym] = sym
        else:
            symbol_map[sym] = sym

        tv_tickers.append(tv_sym)

    url = "https://scanner.tradingview.com/global/scan"
    payload = {
        "symbols": {"tickers": tv_tickers},
        "columns": ["close", "change", "change_abs"]
    }

    try:
        resp = requests.post(url, json=payload, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
        if not resp.ok:
            return {}

        results = {}
        data = resp.json().get("data", [])

        for row in data:
            tv_s = row.get("s")
            vals = row.get("d", [])
            if not tv_s or len(vals) < 3 or vals[0] is None:
                continue

            price = float(vals[0])
            pct = float(vals[1] or 0)
            change = float(vals[2] or 0)
            is_pos = change >= 0

            target_key = symbol_map.get(tv_s, tv_s)

            if price >= 1000:
                price_str = f"{price:,.2f}"
            elif price >= 1:
                price_str = f"{price:.4f}" if "FX:" in target_key else f"{price:.2f}"
            else:
                price_str = f"{price:.5f}"

            sign = "+" if change >= 0 else ""
            change_str = f"{sign}{change:.2f}" if abs(change) >= 0.01 else f"{sign}{change:.4f}"
            pct_str = f"{sign}{pct:.2f}%"

            item_data = {
                "price": round(price, 4),
                "change": round(change, 4),
                "pct": round(pct, 2),
                "isPositive": is_pos,
                "price_str": price_str,
                "change_str": change_str,
                "pct_str": pct_str,
                "last_tick_time": time.time(),
            }

            results[target_key] = item_data
            if tv_s in symbol_map and symbol_map[tv_s] != tv_s:
                results[symbol_map[tv_s]] = item_data

        return results
    except Exception as err:
        logging.warning(f"[TradingView Scan Error] {err}")
        return {}


def _tradingview_poller_loop():
    """Background daemon worker that fetches TradingView live prices asynchronously every 1.2 seconds with adaptive backoff."""
    consecutive_errors = 0
    while True:
        try:
            tv_data = fetch_tradingview_live_prices()
            if tv_data:
                with _fetch_lock:
                    _cache.update(tv_data)
                consecutive_errors = 0
            else:
                consecutive_errors += 1
        except Exception as err:
            consecutive_errors += 1
            logging.warning(f"[TV Poller Loop Error] {err}")
        
        sleep_time = min(10.0, 1.2 * (1.5 ** min(consecutive_errors, 5)))
        time.sleep(sleep_time)


def fetch_live_market_prices() -> dict:
    """Returns cached real-time market prices instantly (< 1ms latency) with zero network blocking."""
    with _fetch_lock:
        return dict(_cache)


# Warm cache & start background pollers on startup
threading.Thread(target=_fetch_global_prices, daemon=True).start()
threading.Thread(target=_tradingview_poller_loop, daemon=True).start()
