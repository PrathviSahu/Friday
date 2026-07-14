"""Market data proxy.

Feeds are resolved per asset class so they can use DIFFERENT providers:
  - forex        -> Twelve Data   (your API key; real-time-ish, free tier)
  - equities/index (Indian NSE/BSE) -> Yahoo Finance (free, no key, but
    delayed). Twelve Data's FREE tier does not cover NSE/BSE.

Why the split: you asked for forex and Indian-stock feeds to stay separate,
and Twelve Data's free plan excludes Indian exchanges. When you later add a
broker API (Zerodha/Upstox) for live trade execution, flip EQUITY_PROVIDER to
'broker' and the equity path upgrades to true real-time with no UI changes.

Env: TWELVE_DATA_API_KEY  (backend/.env or environment)
"""
from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime
from typing import Any, Optional

import httpx

# ── config ────────────────────────────────────────────────────────────────────
TD_BASE = "https://api.twelvedata.com"
YH_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
YH_SEARCH = "https://query1.finance.yahoo.com/v1/finance/search"

EQUITY_PROVIDER = "yahoo"  # 'yahoo' now; later 'broker' / 'twelvedata' (paid)

_load_dotenv_done = False


def _load_dotenv() -> None:
    global _load_dotenv_done
    if _load_dotenv_done:
        return
    _load_dotenv_done = True
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except FileNotFoundError:
        pass


_load_dotenv()
API_KEY = os.environ.get("TWELVE_DATA_API_KEY") or os.environ.get("TWELVEDATA_API_KEY") or ""

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "application/json",
}

INDEX_MAP = {"NSEI": "NIFTY", "BSESN": "SENSEX"}


def to_twelvedata(symbol: str):
    s = (symbol or "").strip()
    if s.endswith(".NS"):
        return "equity", f"{s[:-3]}:NS"
    if s.endswith(".BO"):
        return "equity", f"{s[:-3]}:BSE"
    if s.endswith("=X"):
        base = s[:-2]
        if len(base) == 6:
            return "forex", f"{base[:3]}/{base[3:]}"
        return "forex", base
    if s.startswith("^"):
        return "index", INDEX_MAP.get(s[1:], s[1:])
    return "equity", s


def from_twelvedata(td_symbol: str) -> str:
    s = (td_symbol or "").strip()
    if ":" in s:
        head, tail = s.split(":", 1)
        if tail == "NS":
            return f"{head}.NS"
        if tail == "BSE":
            return f"{head}.BO"
        return head
    if "/" in s and len(s.replace("/", "")) == 6:
        return f"{s.replace('/', '')}=X"
    if s in INDEX_MAP.values():
        inv = {v: f"^{k}" for k, v in INDEX_MAP.items()}
        return inv.get(s, s)
    return s


def provider_for(symbol: str) -> str:
    klass, _ = to_twelvedata(symbol)
    if klass == "forex":
        return "td"
    return EQUITY_PROVIDER  # 'yahoo' (or 'broker' later)


INTERVAL_MAP = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "1h": "1h",
    "1d": "1day",
}
YH_INTERVAL_RANGE = {
    "1m": ("1d", "1m"),
    "5m": ("5d", "5m"),
    "15m": ("1mo", "15m"),
    "1h": ("3mo", "1h"),
    "1d": ("1y", "1d"),
}

_CACHE: dict[str, tuple[Any, float]] = {}
_TTL = {"klines": 60.0, "quote": 10.0, "search": 600.0}


def _cache_get(key: str, ttl: float) -> Optional[Any]:
    """Return the cached value for `key` if it is younger than `ttl`, else None."""
    hit = _CACHE.get(key)
    if hit is None:
        return None
    value, ts = hit
    if time.time() - ts > ttl:
        _CACHE.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: Any) -> Any:
    """Store `value` under `key` with the current timestamp and return it (for `return _cache_set(...)`)."""
    _CACHE[key] = (value, time.time())
    return value


_td_client: Optional[httpx.AsyncClient] = None
_yh_client: Optional[httpx.AsyncClient] = None
_crumb: Optional[str] = None


# ── Twelve Data ────────────────────────────────────────────────────────────────
def _require_key() -> None:
    if not API_KEY:
        raise RuntimeError("TWELVE_DATA_API_KEY is not set (add it to backend/.env or the environment)")


async def _td_client_get() -> httpx.AsyncClient:
    global _td_client
    if _td_client is None or _td_client.is_closed:
        _td_client = httpx.AsyncClient(headers={"Accept": "application/json"}, timeout=15.0, follow_redirects=True)
    return _td_client


async def _td_get(path: str, params: dict) -> Any:
    _require_key()
    client = await _td_client_get()
    params = dict(params)
    params["apikey"] = API_KEY
    for attempt in range(3):
        try:
            resp = await client.get(f"{TD_BASE}/{path}", params=params)
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Twelve Data request failed: {exc}") from exc
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and data.get("status") == "error":
                raise RuntimeError(data.get("message", "Twelve Data error"))
            return data
        if resp.status_code == 429:
            await asyncio.sleep(1.5 * (attempt + 1))
            continue
        if resp.status_code in (401, 403):
            raise RuntimeError("Twelve Data rejected the API key (check TWELVE_DATA_API_KEY)")
        raise RuntimeError(f"Twelve Data upstream returned {resp.status_code}")
    raise RuntimeError("Twelve Data upstream kept rate-limiting")


def _parse_ts(ts: str) -> int:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return int(datetime.strptime(ts, fmt).timestamp())
        except ValueError:
            continue
    return 0


async def _td_time_series(td_symbol: str, interval: str) -> dict:
    yf = INTERVAL_MAP.get(interval, "5min")
    data = await _td_get("time_series", {"symbol": td_symbol, "interval": yf, "outputsize": 320})
    values = list(reversed(data.get("values") or []))
    candles = []
    for v in values:
        try:
            t = _parse_ts(v["datetime"])
            if not t:
                continue
            candles.append(
                {
                    "time": t,
                    "open": round(float(v["open"]), 2),
                    "high": round(float(v["high"]), 2),
                    "low": round(float(v["low"]), 2),
                    "close": round(float(v["close"]), 2),
                    "volume": int(float(v.get("volume") or 0)),
                }
            )
        except (KeyError, ValueError):
            continue
    meta = data.get("meta") or {}
    last = candles[-1]["close"] if candles else None
    prev = meta.get("previous_close") or (candles[0]["open"] if candles else None)
    return {"interval": yf, "candles": candles, "last": last, "previousClose": prev}


async def _td_quotes(td_symbols: list[str]) -> list[dict]:
    if not td_symbols:
        return []
    data = await _td_get("quote", {"symbol": ",".join(td_symbols)})
    if isinstance(data, dict) and "symbol" in data and "price" in data:
        by_td = {data["symbol"]: data}
    elif isinstance(data, dict):
        by_td = data
    else:
        return []
    out = []
    for td in td_symbols:
        raw = by_td.get(td)
        if not raw:
            continue
        price = raw.get("price") or raw.get("close")
        if price is None:
            continue
        out.append(
            {
                "symbol": from_twelvedata(td),
                "name": raw.get("name"),
                "exchange": raw.get("exchange"),
                "price": round(float(price), 2),
                "previousClose": round(float(raw.get("previous_close") or 0), 2) or None,
                "changePercent": round(float(raw.get("percent_change") or 0), 2)
                if raw.get("percent_change") is not None
                else None,
            }
        )
    return out


async def _td_search(q: str) -> list[dict]:
    data = await _td_get("symbol_search", {"symbol": q, "outputsize": 12})
    out = []
    for item in data.get("data") or []:
        sym = item.get("symbol")
        if not sym:
            continue
        out.append(
            {
                "symbol": from_twelvedata(sym),
                "name": item.get("instrument_name") or item.get("description") or sym,
                "exchange": item.get("exchange") or "",
                "type": item.get("type") or "",
            }
        )
    return out


# ── Yahoo Finance (equities / indices; free, no key) ───────────────────────────
async def _yh_client_get() -> httpx.AsyncClient:
    global _yh_client
    if _yh_client is None or _yh_client.is_closed:
        _yh_client = httpx.AsyncClient(headers=HEADERS, timeout=12.0, follow_redirects=True)
    return _yh_client


async def _yh_get_json(url: str, params: Optional[dict]) -> Any:
    client = await _yh_client_get()
    for attempt in range(3):
        try:
            resp = await client.get(url, params=params)
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Yahoo request failed: {exc}") from exc
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 429:
            await asyncio.sleep(1.0 * (attempt + 1))
            continue
        raise RuntimeError(f"Yahoo upstream returned {resp.status_code}")
    raise RuntimeError("Yahoo upstream kept rate-limiting")


async def _yh_chart(symbol: str, range_: str, interval: str) -> dict:
    return (await _yh_get_json(YH_CHART.format(symbol=symbol), {"range": range_, "interval": interval, "includePrePost": "false"}))[
        "chart"
    ]["result"][0]


def _yh_normalize(result: dict) -> list[dict]:
    ts = result.get("timestamp") or []
    q = (result.get("indicators") or {}).get("quote", [{}])[0]
    candles = []
    for i, t in enumerate(ts):
        o, h, l, c = q.get("open", [])[i], q.get("high", [])[i], q.get("low", [])[i], q.get("close", [])[i]
        if o is None or c is None:
            continue
        candles.append(
            {
                "time": int(t),
                "open": round(float(o), 2),
                "high": round(float(h), 2),
                "low": round(float(l), 2),
                "close": round(float(c), 2),
                "volume": int((q.get("volume", [])[i]) or 0),
            }
        )
    return candles


async def _yh_time_series(symbol: str, interval: str) -> dict:
    range_, yf = YH_INTERVAL_RANGE.get(interval, ("1mo", "5m"))
    result = await _yh_chart(symbol, range_, yf)
    meta = result.get("meta", {})
    candles = _yh_normalize(result)
    return {
        "interval": yf,
        "candles": candles,
        "last": round(float(meta["regularMarketPrice"]), 2) if meta.get("regularMarketPrice") is not None else None,
        "previousClose": round(float(meta.get("chartPreviousClose") or meta.get("previousClose") or 0), 2) or None,
    }


async def _yh_one_quote(symbol: str) -> Optional[dict]:
    try:
        result = await _yh_chart(symbol, "1d", "1m")
    except RuntimeError:
        return None
    meta = result.get("meta", {})
    price = meta.get("regularMarketPrice")
    if price is None:
        return None
    return {
        "symbol": symbol,
        "name": meta.get("shortName") or meta.get("longName"),
        "exchange": meta.get("exchangeName"),
        "price": round(float(price), 2),
        "previousClose": round(float(meta.get("chartPreviousClose") or meta.get("previousClose") or 0), 2) or None,
        "changePercent": round(float(meta.get("regularMarketChangePercent") or 0), 2)
        if meta.get("regularMarketChangePercent") is not None
        else None,
    }


async def _yh_quotes(symbols: list[str]) -> list[dict]:
    return [q for q in await asyncio.gather(*[_yh_one_quote(s) for s in symbols]) if q]


async def _yh_search(q: str) -> list[dict]:
    try:
        data = await _yh_get_json(YH_SEARCH, {"q": q})
    except RuntimeError:
        return []
    out = []
    for item in data.get("quotes") or []:
        sym = item.get("symbol")
        if not sym:
            continue
        out.append(
            {
                "symbol": sym,
                "name": item.get("shortname") or item.get("longname") or sym,
                "exchange": item.get("exchange") or item.get("exchDisp") or "",
                "type": item.get("quoteType") or "",
            }
        )
    return out


async def _noop() -> list[dict]:
    return []


# ── public API (canonical symbols in/out; provider dispatched per asset class) ─
async def get_klines(symbol: str, interval: str = "5m") -> dict:
    key = f"klines:{symbol}:{interval}"
    cached = _cache_get(key, _TTL["klines"])
    if cached is not None:
        return cached
    if provider_for(symbol) == "td":
        result = await _td_time_series(to_twelvedata(symbol)[1], interval)
    else:
        result = await _yh_time_series(symbol, interval)
    return _cache_set(key, {"symbol": symbol, **result})


async def get_quotes(symbols: list[str]) -> list[dict]:
    if not symbols:
        return []
    key = "quote:" + ",".join(sorted(symbols))
    cached = _cache_get(key, _TTL["quote"])
    if cached is not None:
        return cached
    td_syms = [s for s in symbols if provider_for(s) == "td"]
    yh_syms = [s for s in symbols if provider_for(s) != "td"]
    out = []
    if td_syms:
        out += await _td_quotes([to_twelvedata(s)[1] for s in td_syms])
    if yh_syms:
        out += await _yh_quotes(yh_syms)
    return _cache_set(key, out)


async def search_symbols(query: str) -> list[dict]:
    q = (query or "").strip()
    if len(q) < 1:
        return []
    key = "search:" + q.lower()
    cached = _cache_get(key, _TTL["search"])
    if cached is not None:
        return cached
    td_task = _td_search(q) if API_KEY else _noop()
    yh_task = _yh_search(q)
    results = []
    try:
        results += await td_task
    except RuntimeError:
        pass
    results += await yh_task
    # dedupe by canonical symbol, prefer Yahoo for equities (richer Indian coverage)
    seen = {}
    for r in results:
        seen[r["symbol"]] = r
    return _cache_set(key, list(seen.values()))
