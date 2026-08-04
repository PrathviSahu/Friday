"""technical_analysis.py — Real Technical Analysis Engine (v3).

Computes genuine indicators from live OHLCV candle data (no more hardcoded
"RSI is at 64" text). All indicator math is pure — `analyze_candles(candles)`
works on a list of {open, high, low, close, volume} dicts, which makes it
trivially unit-testable. `analyze_symbol()` fetches live candles and wraps
the result in a natural-language spoken summary.

Indicators: SMA, EMA, RSI (Wilder), MACD, Bollinger Bands, ATR, Stochastic,
VWAP. Patterns: doji, hammer, shooting star, bullish/bearish engulfing.
Trend: price-vs-EMA, golden/death cross, support/resistance, momentum.
"""

import logging
from typing import Optional

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False


# ═══════════════════════════════════════════════════════════════════════════════
# Pure indicator math (numpy or pure-python fallback)
# ═══════════════════════════════════════════════════════════════════════════════

def _sma(values, period: int) -> list:
    if not values:
        return []
    if _HAS_NUMPY:
        arr = np.asarray(values, dtype=float)
        out = np.full(len(arr), np.nan)
        for i in range(period - 1, len(arr)):
            out[i] = arr[i - period + 1:i + 1].mean()
        return out.tolist()
    out = [None] * len(values)
    window_sum = 0.0
    for i, v in enumerate(values):
        window_sum += v
        if i >= period:
            window_sum -= values[i - period]
        if i >= period - 1:
            out[i] = window_sum / period
    return out


def _ema(values, period: int) -> list:
    if not values:
        return []
    k = 2.0 / (period + 1)
    out = [None] * len(values)
    ema = None
    for i, v in enumerate(values):
        if ema is None:
            ema = v
        else:
            ema = v * k + ema * (1 - k)
        out[i] = ema
    return out


def _rsi(values, period: int = 14) -> list:
    """Wilder-smoothed RSI. Returns list aligned with `values` (None until warm)."""
    if not values:
        return []
    out = [None] * len(values)
    if len(values) < period + 1:
        return out
    gains, losses = [], []
    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for idx in range(period, len(values)):
        if idx > period:
            avg_gain = (avg_gain * (period - 1) + gains[idx - 1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[idx - 1]) / period
        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))
        out[idx] = rsi
    return out


def _macd(values, fast=12, slow=26, signal=9) -> dict:
    """Returns {macd, signal, histogram} lists aligned with `values`."""
    n = len(values)
    ema_fast = _ema(values, fast)
    ema_slow = _ema(values, slow)
    macd_line = [None] * n
    for i in range(n):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            macd_line[i] = ema_fast[i] - ema_slow[i]
    # Signal = EMA of macd_line (only where macd is not None)
    signal_line = [None] * n
    k = 2.0 / (signal + 1)
    ema_val = None
    for i in range(n):
        if macd_line[i] is None:
            continue
        if ema_val is None:
            ema_val = macd_line[i]
        else:
            ema_val = macd_line[i] * k + ema_val * (1 - k)
        signal_line[i] = ema_val
    histogram = [None] * n
    for i in range(n):
        if macd_line[i] is not None and signal_line[i] is not None:
            histogram[i] = macd_line[i] - signal_line[i]
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def _bollinger(values, period: int = 20, num_std: float = 2.0) -> dict:
    n = len(values)
    upper, middle, lower = [None] * n, [None] * n, [None] * n
    for i in range(period - 1, n):
        window = values[i - period + 1:i + 1]
        mean = sum(window) / period
        variance = sum((x - mean) ** 2 for x in window) / period
        std = variance ** 0.5
        middle[i] = mean
        upper[i] = mean + num_std * std
        lower[i] = mean - num_std * std
    return {"upper": upper, "middle": middle, "lower": lower}


def _atr(highs, lows, closes, period: int = 14) -> list:
    n = len(closes)
    out = [None] * n
    if n < 2:
        return out
    trs = []
    for i in range(1, n):
        tr = max(highs[i] - lows[i],
                 abs(highs[i] - closes[i - 1]),
                 abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    if len(trs) < period:
        return out  # not enough data to warm up
    atr = sum(trs[:period]) / period
    out[period] = atr
    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period
        out[i + 1] = atr
    return out


def _stochastic(highs, lows, closes, k_period: int = 14, d_period: int = 3) -> dict:
    n = len(closes)
    raw_k = [None] * n
    for i in range(k_period - 1, n):
        hi = max(highs[i - k_period + 1:i + 1])
        lo = min(lows[i - k_period + 1:i + 1])
        if hi == lo:
            raw_k[i] = 50.0
        else:
            raw_k[i] = 100.0 * (closes[i] - lo) / (hi - lo)
    k_line = raw_k[:]
    d_line = [None] * n
    for i in range(d_period - 1, n):
        vals = [x for x in raw_k[i - d_period + 1:i + 1] if x is not None]
        if len(vals) == d_period:
            d_line[i] = sum(vals) / d_period
    return {"k": k_line, "d": d_line}


def _vwap(candles) -> list:
    out = []
    cum_vol = 0.0
    cum_pv = 0.0
    for c in candles:
        vol = float(c.get("volume", 0) or 0)
        typical = (float(c["high"]) + float(c["low"]) + float(c["close"])) / 3.0
        cum_vol += vol
        cum_pv += typical * vol
        out.append(cum_pv / cum_vol if cum_vol > 0 else typical)
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# Pattern & trend detection
# ═══════════════════════════════════════════════════════════════════════════════

def _detect_patterns(candles) -> list:
    """Return list of pattern names detected on the most recent candles."""
    if len(candles) < 3:
        return []
    patterns = []
    c = candles[-1]
    prev = candles[-2]
    body = abs(c["close"] - c["open"])
    rng = (c["high"] - c["low"]) or 1e-9
    upper_wick = c["high"] - max(c["open"], c["close"])
    lower_wick = min(c["open"], c["close"]) - c["low"]

    # Doji: tiny body
    if body / rng < 0.1:
        patterns.append("Doji")
    # Hammer: long lower wick, small body, near top
    if lower_wick >= 2 * body and lower_wick >= 0.6 * rng and upper_wick <= 0.3 * rng:
        patterns.append("Hammer")
    # Shooting star: long upper wick, small body, near bottom
    if upper_wick >= 2 * body and upper_wick >= 0.6 * rng and lower_wick <= 0.3 * rng:
        patterns.append("Shooting Star")
    # Bullish engulfing
    if (c["close"] > c["open"] and prev["close"] < prev["open"]
            and c["close"] >= prev["open"] and c["open"] <= prev["close"]):
        patterns.append("Bullish Engulfing")
    # Bearish engulfing
    if (c["close"] < c["open"] and prev["close"] > prev["open"]
            and c["close"] <= prev["open"] and c["open"] >= prev["close"]):
        patterns.append("Bearish Engulfing")
    return patterns


def _swing_points(candles, lookback: int = 30) -> tuple:
    """Return (support, resistance) from recent swing lows/highs."""
    if len(candles) < 5:
        return None, None
    window = candles[-lookback:]
    swing_lows = []
    swing_highs = []
    for i in range(1, len(window) - 1):
        if window[i]["low"] < window[i - 1]["low"] and window[i]["low"] < window[i + 1]["low"]:
            swing_lows.append(window[i]["low"])
        if window[i]["high"] > window[i - 1]["high"] and window[i]["high"] > window[i + 1]["high"]:
            swing_highs.append(window[i]["high"])
    support = min(swing_lows) if swing_lows else None
    resistance = max(swing_highs) if swing_highs else None
    return support, resistance


# ═══════════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_candles(candles: list) -> dict:
    """Compute full indicator + pattern + trend analysis from OHLCV candles.

    `candles`: list of dicts with keys open/high/low/close/volume (and time).
    Returns a structured dict; fields are None when there is insufficient data.
    """
    if not candles:
        return {"error": "No candle data", "summary": "No data available for analysis."}

    closes = [float(c["close"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    opens = [float(c["open"]) for c in candles]
    price = closes[-1]

    rsi_series = _rsi(closes, 14)
    macd = _macd(closes)
    bb = _bollinger(closes)
    atr_series = _atr(highs, lows, closes, 14)
    stoch = _stochastic(highs, lows, closes)
    ema_9 = _ema(closes, 9)
    ema_20 = _ema(closes, 20)
    ema_50 = _ema(closes, 50)
    vwap = _vwap(candles)

    # Last valid values
    def last_valid(series):
        for v in reversed(series):
            if v is not None:
                return round(float(v), 4)
        return None

    rsi = last_valid(rsi_series)
    macd_val = last_valid(macd["macd"])
    macd_signal = last_valid(macd["signal"])
    hist = last_valid(macd["histogram"])
    atr = last_valid(atr_series)
    stoch_k = last_valid(stoch["k"])
    stoch_d = last_valid(stoch["d"])

    # Trend classification
    trend = "neutral"
    confidence = 0.5
    if ema_20[-1] is not None and ema_50[-1] is not None:
        if price > ema_20[-1] > ema_50[-1]:
            trend, confidence = "bullish", 0.8
        elif price < ema_20[-1] < ema_50[-1]:
            trend, confidence = "bearish", 0.8
        elif price > ema_20[-1]:
            trend, confidence = "bullish", 0.6

    # Golden / death cross (EMA 20 crossing EMA 50)
    cross = None
    if ema_20[-1] is not None and ema_50[-1] is not None and len(ema_20) >= 2 \
            and ema_20[-2] is not None and ema_50[-2] is not None:
        if ema_20[-2] <= ema_50[-2] and ema_20[-1] > ema_50[-1]:
            cross = "golden_cross"
        elif ema_20[-2] >= ema_50[-2] and ema_20[-1] < ema_50[-1]:
            cross = "death_cross"

    # Momentum: % change over last 5 candles
    momentum = None
    if len(closes) >= 6 and closes[-6]:
        momentum = round((closes[-1] / closes[-6] - 1.0) * 100.0, 2)

    support, resistance = _swing_points(candles)
    patterns = _detect_patterns(candles)

    # RSI / MACD readings
    rsi_state = None
    if rsi is not None:
        rsi_state = "overbought" if rsi >= 70 else ("oversold" if rsi <= 30 else "neutral")
    macd_state = None
    if macd_val is not None and macd_signal is not None:
        macd_state = "bullish" if macd_val > macd_signal else "bearish"

    return {
        "symbol": candles[-1].get("_symbol"),
        "price": round(price, 6),
        "indicators": {
            "rsi": rsi,
            "rsi_state": rsi_state,
            "macd": macd_val,
            "macd_signal": macd_signal,
            "macd_histogram": hist,
            "macd_state": macd_state,
            "bollinger_upper": last_valid(bb["upper"]),
            "bollinger_middle": last_valid(bb["middle"]),
            "bollinger_lower": last_valid(bb["lower"]),
            "atr": atr,
            "stochastic_k": stoch_k,
            "stochastic_d": stoch_d,
            "sma_200": last_valid(_sma(closes, 200)),
            "ema_9": last_valid(ema_9),
            "ema_20": last_valid(ema_20),
            "ema_50": last_valid(ema_50),
            "vwap": last_valid(vwap),
        },
        "trend": {
            "bias": trend,
            "confidence": confidence,
            "golden_death_cross": cross,
            "momentum_pct": momentum,
            "support": round(support, 6) if support else None,
            "resistance": round(resistance, 6) if resistance else None,
        },
        "patterns": patterns,
        "candle_count": len(candles),
    }


def _build_summary(analysis: dict, symbol: str) -> str:
    ind = analysis.get("indicators", {})
    trend = analysis.get("trend", {})
    bias = trend.get("bias", "neutral")
    rsi = ind.get("rsi")
    rsi_state = ind.get("rsi_state")
    macd_state = ind.get("macd_state")
    support = trend.get("support")
    resistance = trend.get("resistance")
    momentum = trend.get("momentum_pct")
    patterns = analysis.get("patterns", [])
    cross = trend.get("golden_death_cross")

    parts = [f"Prem, technical analysis for {symbol}."]
    parts.append(f"Market structure is {bias} with {int((trend.get('confidence') or 0.5) * 100)}% confidence.")
    if rsi is not None:
        parts.append(f"RSI at {rsi:.1f} — {rsi_state}.")
    if macd_state:
        parts.append(f"MACD is {macd_state}.")
    if cross:
        parts.append(f"{'Golden cross' if cross == 'golden_cross' else 'Death cross'} detected on the EMA 20/50.")
    if support:
        parts.append(f"Support at {support:,.4f}.")
    if resistance:
        parts.append(f"Resistance at {resistance:,.4f}.")
    if patterns:
        parts.append(f"Recent patterns: {', '.join(patterns)}.")
    if momentum is not None:
        direction = "up" if momentum >= 0 else "down"
        parts.append(f"Momentum is {direction} {abs(momentum):.2f}% over the last 5 candles.")
    return " ".join(parts)


def analyze_symbol(symbol: str = "FX:EURUSD", interval: str = "15") -> dict:
    """Fetch live OHLCV and return full analysis + spoken summary."""
    from services.chart_data import fetch_ohlcv

    data = fetch_ohlcv(symbol, interval)
    candles = data.get("candles", [])
    if not candles:
        return {
            "symbol": symbol,
            "interval": interval,
            "error": data.get("error", "No data"),
            "summary": f"Sorry Prem, I could not fetch chart data for {symbol}.",
        }
    # Tag candles so analyze_candles can echo the symbol back
    for c in candles:
        c["_symbol"] = symbol
    analysis = analyze_candles(candles)
    analysis["symbol"] = symbol
    analysis["interval"] = interval
    analysis["summary"] = _build_summary(analysis, symbol)
    return analysis
