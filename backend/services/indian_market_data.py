"""
indian_market_data.py

Fetches real live Indian market data using yfinance (Yahoo Finance).
Covers NIFTY50, SENSEX, BANKNIFTY, and top NSE stocks.
Data is refreshed every 3 minutes (NSE has ~15 min delay on Yahoo).
Between refreshes, micro-tick simulation keeps prices feeling live.
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
    logging.warning("[IndianMarket] yfinance not installed. Run: pip install yfinance")

# ── Symbol map: Yahoo Finance symbol → frontend symbol key ──────────────────
INDIAN_SYMBOLS = {
    "^NSEI":         {"key": "NSE:NIFTY50",    "name": "NIFTY 50",    "type": "index"},
    "^BSESN":        {"key": "BSE:SENSEX",     "name": "SENSEX",      "type": "index"},
    "^NSEBANK":      {"key": "NSE:BANKNIFTY",  "name": "BANK NIFTY",  "type": "index"},
    "RELIANCE.NS":   {"key": "NSE:RELIANCE",   "name": "RELIANCE",    "type": "stock"},
    "TCS.NS":        {"key": "NSE:TCS",        "name": "TCS",         "type": "stock"},
    "HDFCBANK.NS":   {"key": "NSE:HDFCBANK",  "name": "HDFCBANK",    "type": "stock"},
    "INFY.NS":       {"key": "NSE:INFY",       "name": "INFY",        "type": "stock"},
    "WIPRO.NS":      {"key": "NSE:WIPRO",      "name": "WIPRO",       "type": "stock"},
    "ADANIENT.NS":   {"key": "NSE:ADANIENT",   "name": "ADANIENT",    "type": "stock"},
    "BAJFINANCE.NS": {"key": "NSE:BAJFINANCE", "name": "BAJFINANCE",  "type": "stock"},
    "SBIN.NS":       {"key": "NSE:SBIN",       "name": "SBIN",        "type": "stock"},
    "ICICIBANK.NS":  {"key": "NSE:ICICIBANK",  "name": "ICICIBANK",   "type": "stock"},
    "HINDUNILVR.NS": {"key": "NSE:HINDUNILVR", "name": "HINDUNILVR",  "type": "stock"},
    "MARUTI.NS":     {"key": "NSE:MARUTI",     "name": "MARUTI",      "type": "stock"},
    "ASIANPAINT.NS": {"key": "NSE:ASIANPAINT", "name": "ASIANPAINT",  "type": "stock"},
    "BLACKBUCK.NS":  {"key": "NSE:BLACKBUCK",  "name": "BLACKBUCK",   "type": "stock"},
    "TATAMOTORS.NS": {"key": "NSE:TATAMOTORS", "name": "TATAMOTORS",  "type": "stock"},
    "ZOMATO.NS":     {"key": "NSE:ZOMATO",     "name": "ZOMATO",      "type": "stock"},
    "PAYTM.NS":      {"key": "NSE:PAYTM",      "name": "PAYTM",       "type": "stock"},
    "SUZLON.NS":     {"key": "NSE:SUZLON",     "name": "SUZLON",      "type": "stock"},
    "SWIGGY.NS":     {"key": "NSE:SWIGGY",     "name": "SWIGGY",      "type": "stock"},
    "HAL.NS":        {"key": "NSE:HAL",        "name": "HAL",         "type": "stock"},
    "IRFC.NS":       {"key": "NSE:IRFC",       "name": "IRFC",        "type": "stock"},
    "JIOFIN.NS":     {"key": "NSE:JIOFIN",     "name": "JIOFIN",      "type": "stock"},
    "TATASTEEL.NS":  {"key": "NSE:TATASTEEL",  "name": "TATASTEEL",   "type": "stock"},
    "TITAN.NS":      {"key": "NSE:TITAN",      "name": "TITAN",       "type": "stock"},
    "BHARTIARTL.NS": {"key": "NSE:BHARTIARTL", "name": "BHARTIARTL",  "type": "stock"},
    "BEL.NS":        {"key": "NSE:BEL",        "name": "BEL",         "type": "stock"},
    "LTIMINDTREE.NS": {"key": "NSE:LTIM",       "name": "LTIMindtree",  "type": "stock"},
    "AXISBANK.NS":   {"key": "NSE:AXISBANK",   "name": "AXISBANK",    "type": "stock"},
    "SUNPHARMA.NS":  {"key": "NSE:SUNPHARMA",  "name": "SUNPHARMA",   "type": "stock"},
    "ITC.NS":        {"key": "NSE:ITC",        "name": "ITC",         "type": "stock"},
    "ONGC.NS":       {"key": "NSE:ONGC",       "name": "ONGC",        "type": "stock"},
}

REFRESH_INTERVAL = 180  # refresh from Yahoo every 3 minutes

# ── In-memory price store ───────────────────────────────────────────────────
_cache: dict = {}         # key → {price, change, pct, isPositive, tick_direction, ...}
_last_fetch: float = 0.0
_fetch_lock = threading.Lock()


def _format_price(price: float) -> str:
    if price >= 10000:
        return f"{price:,.2f}"
    elif price >= 1000:
        return f"{price:,.2f}"
    else:
        return f"{price:.2f}"


def _format_change(change: float) -> str:
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.2f}"


def _fetch_from_yahoo() -> bool:
    """Fetch latest prices from Yahoo Finance for all Indian symbols + DB watchlist items."""
    if not YFINANCE_AVAILABLE:
        return False
    try:
        # Build symbol dict including DB watchlist custom items
        target_map = dict(INDIAN_SYMBOLS)
        try:
            from database.watchlist_db import get_watchlist
            db_items = get_watchlist()
            for item in db_items:
                sym = item.get("symbol", "")
                if sym.startswith("NSE:"):
                    ticker = sym.replace("NSE:", "") + ".NS"
                    if ticker not in target_map:
                        target_map[ticker] = {"key": sym, "name": item.get("name", ticker), "type": "stock"}
                elif sym.startswith("BSE:"):
                    ticker = sym.replace("BSE:", "") + ".BO"
                    if ticker not in target_map:
                        target_map[ticker] = {"key": sym, "name": item.get("name", ticker), "type": "stock"}
        except Exception:
            pass

        yahoo_syms = list(target_map.keys())
        tickers = yf.Tickers(" ".join(yahoo_syms))

        fetched = 0
        for yahoo_sym, meta in target_map.items():
            try:
                t = tickers.tickers[yahoo_sym]
                fi = t.fast_info

                price = float(fi.last_price or 0)
                prev  = float(fi.previous_close or price)
                if price <= 0:
                    continue

                change = round(price - prev, 2)
                pct    = round((change / prev) * 100, 2) if prev else 0.0
                is_pos = change >= 0

                key = meta["key"]
                _cache[key] = {
                    "price":          price,
                    "prev_close":     prev,
                    "change":         change,
                    "pct":            pct,
                    "isPositive":     is_pos,
                    "tick_direction": "up" if is_pos else "down",
                    "last_tick_time": time.time(),
                    "name":           meta["name"],
                    "type":           meta["type"],
                    # Pre-formatted strings for frontend
                    "price_str":      _format_price(price),
                    "change_str":     _format_change(change),
                    "pct_str":        f"+{pct:.2f}%" if pct >= 0 else f"{pct:.2f}%",
                }
                fetched += 1
            except Exception as e:
                logging.debug(f"[IndianMarket] Skip {yahoo_sym}: {e}")

        logging.info(f"[IndianMarket] Fetched {fetched}/{len(target_map)} symbols from Yahoo Finance")
        return fetched > 0
    except Exception as err:
        logging.warning(f"[IndianMarket] Yahoo fetch failed: {err}")
        return False


def _apply_micro_ticks():
    """Apply tiny simulated fluctuations between real fetches to keep UI feeling live."""
    for key, data in _cache.items():
        price = data["price"]
        delta = (random.random() - 0.48) * price * 0.0003  # ±0.03% micro tick

        if price >= 1000:
            new_price = round(price + delta, 2)
        else:
            new_price = round(price + delta, 2)

        diff = new_price - price
        data["price"] = new_price
        data["price_str"] = _format_price(new_price)

        if abs(diff) > 0.001:
            data["tick_direction"] = "up" if diff > 0 else "down"
            data["last_tick_time"] = time.time()


def _indian_bg_worker():
    """Background daemon thread that refreshes Indian stock prices asynchronously without blocking API requests."""
    global _last_fetch
    while True:
        try:
            if _fetch_from_yahoo():
                _last_fetch = time.time()
        except Exception as e:
            logging.warning(f"[Indian BG Worker Error] {e}")
        time.sleep(60)


def get_indian_market_prices() -> dict:
    """Returns cached Indian market data instantly (< 1ms latency) with zero network blocking."""
    open_status = is_market_open()
    with _fetch_lock:
        if not open_status:
            for item in _cache.values():
                item["tick_direction"] = None
        return dict(_cache)


def is_market_open() -> bool:
    """Check if NSE is currently open (Mon–Fri, 9:15 AM – 3:30 PM IST)."""
    import datetime
    import pytz

    try:
        ist = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.datetime.now(ist)
        weekday = now_ist.weekday()  # 0=Mon, 6=Sun
        if weekday >= 5:  # Weekend
            return False
        market_open  = now_ist.replace(hour=9,  minute=15, second=0, microsecond=0)
        market_close = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
        return market_open <= now_ist <= market_close
    except Exception:
        return True


# Pre-warm cache and start background poller on module import
threading.Thread(target=_indian_bg_worker, daemon=True).start()
