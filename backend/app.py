from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from backend/.env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os

from services.brain import respond, get_proactive_suggestion
from services.tts import generate_speech
from services.voice_auth import is_guest_permitted, set_guest_permission
from services.memory import get_all_memories, save_fact
from services.system_control import get_spotify_current_track, set_spotify_position, duck_spotify_volume, unduck_spotify_volume

from services.todos import get_todos, add_todo, toggle_todo, delete_todo, clear_done, update_todo_text
from services.system_stats import get_system_stats
from services.weather import get_weather
from services.web_search import search_web_instant
from services.reminders import add_reminder, get_active_reminders
from services.mac_controls import (
    get_display_status,
    set_brightness,
    set_dark_mode,
    set_system_volume,
    set_system_mute,
    lock_display,
)

# Ensure temp_audio directory exists
AUDIO_DIR = Path('temp_audio')
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="FRIDAY AI Core", version="2.0.0")

# Enable CORS securely for local frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount('/temp_audio', StaticFiles(directory='temp_audio'), name='temp_audio')


class ChatTextRequest(BaseModel):
    text: str
    is_boss: bool = True
    silence_tts: bool = False


class TTSRequest(BaseModel):
    text: str


class PermissionRequest(BaseModel):
    allow: bool


class SaveMemoryRequest(BaseModel):
    key: str
    value: str


class SearchRequest(BaseModel):
    query: str


class ReminderRequest(BaseModel):
    message: str
    seconds: int


class BrightnessRequest(BaseModel):
    level: float


class DarkModeRequest(BaseModel):
    enabled: bool


class VolumeRequest(BaseModel):
    level: int


class MuteRequest(BaseModel):
    muted: bool


class TodoCreateRequest(BaseModel):
    text: str
    priority: str = "normal"  # "high" | "normal" | "low"


class TodoTextRequest(BaseModel):
    text: str


@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "F.R.I.D.A.Y. AI Core v2.0",
        "guest_permitted": is_guest_permitted()
    }


@app.post("/api/chat/text")
def chat_text_endpoint(req: ChatTextRequest):
    """Text-based chat endpoint for FRIDAY AI brain with memory learning"""
    try:
        res = respond(req.text, is_boss=req.is_boss, silence_tts=req.silence_tts)
        return res
    except Exception as e:
        import traceback
        print(f"[Error] Chat endpoint error: {e}")
        traceback.print_exc()
        return {
            "reply": "I apologize Prem, I had a momentary connection hiccup. Could you repeat that?",
            "action": "none"
        }


@app.get("/api/memory")
def get_memories_endpoint():
    """Retrieve all stored long-term memories"""
    return {"status": "ok", "memories": get_all_memories()}


@app.post("/api/memory")
def save_memory_endpoint(req: SaveMemoryRequest):
    """Manually add or edit a memory fact"""
    save_fact(req.key, req.value)
    return {"status": "ok", "memories": get_all_memories()}


@app.post("/api/permission")
def set_permission_endpoint(req: PermissionRequest):
    """Grant or revoke guest voice permission"""
    set_guest_permission(req.allow)
    return {"status": "ok", "guest_permitted": is_guest_permitted()}


@app.get("/api/spotify/current-track")
def get_spotify_track_endpoint():
    """Retrieve details of currently playing track on Spotify"""
    return get_spotify_current_track()


class SpotifySeekRequest(BaseModel):
    seconds: float

@app.post("/api/spotify/seek")
def spotify_seek_endpoint(req: SpotifySeekRequest):
    """Seek to specific position in currently playing Spotify track"""
    ok = set_spotify_position(req.seconds)
    return {"status": "ok" if ok else "error"}


@app.post("/api/spotify/duck")
def spotify_duck_endpoint():
    """Lower Spotify volume while FRIDAY is speaking."""
    ok = duck_spotify_volume()
    return {"status": "ok" if ok else "ignored"}


@app.post("/api/spotify/unduck")
def spotify_unduck_endpoint():
    """Restore Spotify volume after FRIDAY finishes speaking."""
    ok = unduck_spotify_volume()
    return {"status": "ok" if ok else "ignored"}


# ── macOS Display & Hardware Controls ─────────────────────────────────────────
@app.get("/api/system/display")
def get_display_endpoint():
    """Return live brightness, dark mode, system volume, and mute status."""
    return get_display_status()


@app.post("/api/system/display/brightness")
def set_brightness_endpoint(req: BrightnessRequest):
    """Set main display brightness (0-100 or 0.0-1.0)."""
    ok = set_brightness(req.level)
    return {"status": "ok" if ok else "error", "brightness": req.level}


@app.post("/api/system/display/dark-mode")
def set_dark_mode_endpoint(req: DarkModeRequest):
    """Toggle macOS Dark Mode on or off."""
    ok = set_dark_mode(req.enabled)
    return {"status": "ok" if ok else "error", "dark_mode": req.enabled}


@app.post("/api/system/display/volume")
def set_volume_endpoint(req: VolumeRequest):
    """Set system output volume (0-100)."""
    ok = set_system_volume(req.level)
    return {"status": "ok" if ok else "error", "volume": req.level}


@app.post("/api/system/display/mute")
def set_mute_endpoint(req: MuteRequest):
    """Mute or unmute system audio output."""
    ok = set_system_mute(req.muted)
    return {"status": "ok" if ok else "error", "muted": req.muted}


@app.post("/api/system/display/lock")
def lock_display_endpoint():
    """Immediately lock display / trigger screen saver."""
    ok = lock_display()
    return {"status": "ok" if ok else "error"}


@app.get("/api/proactive")
def proactive_endpoint():
    """Return a time-aware proactive suggestion FRIDAY can speak spontaneously."""
    return get_proactive_suggestion()


@app.get("/api/system/stats")
def system_stats_endpoint():
    """Return live CPU, RAM, Disk, and Battery stats."""
    return get_system_stats()


@app.get("/api/weather")
def weather_endpoint():
    """Return live weather data."""
    return get_weather()


@app.post("/api/search")
def web_search_endpoint(req: SearchRequest):
    """Search DuckDuckGo instant answer snippets."""
    return search_web_instant(req.query)


@app.get("/api/reminders")
def get_reminders_endpoint():
    """Get active timers and reminders."""
    return {"reminders": get_active_reminders()}


@app.post("/api/reminders")
def add_reminder_endpoint(req: ReminderRequest):
    """Set a timer/reminder."""
    item = add_reminder(req.message, req.seconds)
    return {"status": "ok", "reminder": item}


# ── Todo endpoints ──────────────────────────────────────────

@app.get("/api/todos")
def get_todos_endpoint():
    """Get all todos"""
    return {"todos": get_todos()}


@app.post("/api/todos")
def create_todo_endpoint(req: TodoCreateRequest):
    """Add a new todo"""
    item = add_todo(req.text, req.priority)
    return {"status": "ok", "todo": item}


@app.patch("/api/todos/{todo_id}/toggle")
def toggle_todo_endpoint(todo_id: str):
    """Toggle a todo's done state"""
    item = toggle_todo(todo_id)
    if not item:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"status": "ok", "todo": item}


@app.patch("/api/todos/{todo_id}/text")
def update_todo_endpoint(todo_id: str, req: TodoTextRequest):
    """Edit todo text"""
    item = update_todo_text(todo_id, req.text)
    if not item:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"status": "ok", "todo": item}


@app.delete("/api/todos/done")
def clear_done_endpoint():
    """Remove all completed todos"""
    count = clear_done()
    return {"status": "ok", "removed": count}


@app.delete("/api/todos/{todo_id}")
def delete_todo_endpoint(todo_id: str):
    """Delete a todo by id"""
    ok = delete_todo(todo_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"status": "ok"}


@app.post("/api/tts")
async def tts_endpoint(req: TTSRequest):
    """Generate British female voice audio using Edge-TTS"""
    try:
        file_path = await generate_speech(req.text, AUDIO_DIR)
        # Verify generated audio file exists on disk before returning URL
        if not file_path.exists() or file_path.stat().st_size == 0:
            raise HTTPException(status_code=500, detail="Generated audio file is missing or empty")
        return {"audio_url": f"http://localhost:8000/temp_audio/{file_path.name}"}
    except Exception as e:
        print(f"[Error] TTS generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


from database.chart_db import get_chart_drawings, save_chart_drawings


class ChartSaveRequest(BaseModel):
    symbol: str
    drawings_data: dict


@app.get("/api/trading/chart-db")
def get_chart_drawings_endpoint(symbol: str = "OANDA:NAS100USD"):
    """Fetch saved chart drawings & layout data from SQLite database."""
    return get_chart_drawings(symbol)


@app.post("/api/trading/chart-db")
def save_chart_drawings_endpoint(req: ChartSaveRequest):
    """Save chart drawings & layout data to SQLite database."""
    ok = save_chart_drawings(req.symbol, req.drawings_data)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to save chart drawings")
    return {"status": "ok", "symbol": req.symbol.upper()}


from services.gdrive_sync import start_background_gdrive_sync, perform_gdrive_sync, get_gdrive_sync_status

# Start background 5TB Google Drive sync engine on server startup
start_background_gdrive_sync(interval_seconds=30)


@app.get("/api/gdrive/status")
def get_gdrive_status_endpoint():
    """Get 5TB Google Drive background sync status."""
    return get_gdrive_sync_status()


@app.post("/api/gdrive/sync-now")
def trigger_gdrive_sync_endpoint():
    """Trigger an instant background backup to Google Drive."""
    res = perform_gdrive_sync()
    return {"status": "ok", "gdrive": res}


from services.market_data import fetch_live_market_prices
from services.indian_market_data import get_indian_market_prices, is_market_open


@app.get("/api/trading/live-prices")
def get_live_prices_endpoint():
    """Get live real-time market prices with micro tick fluctuations."""
    prices = fetch_live_market_prices()
    try:
        indian = get_indian_market_prices()
        if indian:
            prices.update(indian)
    except Exception as e:
        print("[Live Prices] Error merging Indian prices:", e)
    return prices


@app.get("/api/trading/indian-prices")
def get_indian_prices_endpoint():
    """Get live Indian market data (NSE/BSE) via Yahoo Finance. Refreshes every 3 min."""
    data = get_indian_market_prices()
    return {
        "market_open": is_market_open(),
        "prices": data,
        "timestamp": __import__('time').time(),
    }

@app.get("/api/trading/ohlcv")
def get_ohlcv_endpoint(symbol: str = "FX:EURUSD", interval: str = "5"):
    """
    Fetch OHLCV candle data — Forex optimised, 24/5 always live.
    Supports FX pairs, Gold, DXY, Crypto, US stocks, Indices.
    interval: 1, 5, 15, 30, 60, 240 (minutes), D (daily), W (weekly)
    """
    import yfinance as yf

    # TV symbol → Yahoo Finance ticker (Forex-first)
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

    yf_interval_key = str(interval)
    period, yf_interval = INTERVAL_MAP.get(yf_interval_key, ('5d', '5m'))

    # Resolve ticker
    yf_ticker = SYMBOL_MAP.get(symbol, symbol)

    # Determine decimal precision: Forex pairs = 5dp, JPY pairs = 3dp, Gold/indices = 2dp
    is_jpy = 'JPY' in symbol.upper()
    is_fx  = symbol.startswith('FX:')
    if is_jpy:
        digits = 3
    elif is_fx:
        digits = 5
    else:
        digits = 4

    try:
        tk  = yf.Ticker(yf_ticker)
        df  = tk.history(period=period, interval=yf_interval, auto_adjust=True)
        if df is None or df.empty:
            return {"candles": [], "symbol": symbol, "yf_ticker": yf_ticker, "error": "No data returned"}

        candles = []
        for ts, row in df.iterrows():
            t = int(ts.timestamp())
            candles.append({
                "time":   t,
                "open":   round(float(row['Open']),  digits),
                "high":   round(float(row['High']),  digits),
                "low":    round(float(row['Low']),   digits),
                "close":  round(float(row['Close']), digits),
                "volume": int(row.get('Volume', 0) or 0),
            })

        print(f"[OHLCV] ✅ {symbol} ({yf_ticker}) {yf_interval}/{period} → {len(candles)} candles")
        return {"candles": candles, "symbol": symbol, "yf_ticker": yf_ticker, "interval": yf_interval, "count": len(candles)}
    except Exception as e:
        print(f"[OHLCV] ❌ Error fetching {yf_ticker}: {e}")
        return {"candles": [], "symbol": symbol, "error": str(e)}



@app.get("/api/trading/search")
def search_trading_symbols(q: str = ""):
    """Live real-time search across ALL 5000+ stocks on Earth (NSE, BSE, NASDAQ, NYSE, Forex, Crypto)."""
    query = q.strip()
    if not query:
        return {"results": []}

    results = []
    seen = set()

    # Helper to append formatted ticker
    def add_item(sym, name_str, exch_str, type_str):
        if not sym or sym in seen:
            return
        seen.add(sym)

        if sym.endswith(".NS"):
            ticker = sym[:-3]
            tv_symbol = f"NSE:{ticker}"
            exchange = "NSE"
            stype = "stock"
            logo_img = f"https://www.google.com/s2/favicons?domain={ticker.lower()}.com&sz=64"
            logo_img2 = "https://flagcdn.com/h24/in.png"
        elif sym.endswith(".BO"):
            ticker = sym[:-3]
            tv_symbol = f"BSE:{ticker}"
            exchange = "BSE"
            stype = "stock"
            logo_img = f"https://www.google.com/s2/favicons?domain={ticker.lower()}.com&sz=64"
            logo_img2 = "https://flagcdn.com/h24/in.png"
        elif "=X" in sym:
            tv_symbol = f"FX:{sym.replace('=X', '')}"
            exchange = "FX"
            stype = "forex"
            logo_img = "https://flagcdn.com/h24/eu.png"
            logo_img2 = "https://flagcdn.com/h24/us.png"
        elif "-USD" in sym:
            ticker = sym.replace("-USD", "USDT")
            tv_symbol = f"BINANCE:{ticker}"
            exchange = "BINANCE"
            stype = "crypto"
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

    # Try yfinance.Search first
    try:
        import yfinance as yf
        yf_search = yf.Search(query, max_results=12)
        for item in yf_search.quotes:
            sym = item.get("symbol")
            name = item.get("shortname") or item.get("longname") or sym
            exch = item.get("exchDisp") or ""
            qtype = item.get("quoteType") or ""
            add_item(sym, name, exch, qtype)
    except Exception as e:
        print("[yfinance Search Warning]", e)

    # Fallback to direct requests if yfinance returns empty
    if not results:
        try:
            import requests
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={requests.utils.quote(query)}&quotesCount=12"
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
            resp = requests.get(url, headers=headers, timeout=4)
            if resp.ok:
                for item in resp.json().get("quotes", []):
                    sym = item.get("symbol")
                    name = item.get("shortname") or item.get("longname") or sym
                    exch = item.get("exchDisp") or ""
                    qtype = item.get("quoteType") or ""
                    add_item(sym, name, exch, qtype)
        except Exception as err:
            print("[Direct Search Error]", err)

    return {"results": results}


# ── Watchlist DB endpoints ────────────────────────────────────────────────────

from database.watchlist_db import (
    get_watchlist, add_watchlist_item, remove_watchlist_item, seed_default_watchlist
)

# Seed default watchlist on startup (only if table is empty)
DEFAULT_WATCHLIST_SEED = [
    { "symbol": "CAPITALCOM:DXY",  "name": "DXY",    "full": "U.S. Dollar Index",         "logoImg": "https://flagcdn.com/h24/us.png",  "logoBg": "#059669", "type": "index",    "exchange": "CAPITALCOM", "isPositive": False, "price": "101.148", "change": "-0.045", "changePct": "-0.04%" },
    { "symbol": "OANDA:XAUUSD",    "name": "XAUUSD",  "full": "Gold Spot / U.S. Dollar",   "logoImg": "https://assets.coingecko.com/coins/images/32324/small/gold.png", "logoImg2": "https://flagcdn.com/h24/us.png", "logoBg": "#d97706", "type": "commodity", "exchange": "OANDA", "isPositive": True,  "flagged": True },
    { "symbol": "FX:USDCHF",       "name": "USDCHF",  "full": "USD / Swiss Franc",         "logoImg": "https://flagcdn.com/h24/us.png",  "logoImg2": "https://flagcdn.com/h24/ch.png", "logoBg": "#2563eb", "type": "forex", "exchange": "FX", "isPositive": False },
    { "symbol": "FX:USDCAD",       "name": "USDCAD",  "full": "USD / Canadian Dollar",     "logoImg": "https://flagcdn.com/h24/us.png",  "logoImg2": "https://flagcdn.com/h24/ca.png", "logoBg": "#dc2626", "type": "forex", "exchange": "FX", "isPositive": False },
    { "symbol": "FX:EURAUD",       "name": "EURAUD",  "full": "EUR / Australian Dollar",   "logoImg": "https://flagcdn.com/h24/eu.png",  "logoImg2": "https://flagcdn.com/h24/au.png", "logoBg": "#089981", "type": "forex", "exchange": "FX", "isPositive": True  },
    { "symbol": "OANDA:NAS100USD", "name": "NASDAQ",  "full": "US Tech 100 Index",         "logoImg": "https://flagcdn.com/h24/us.png",  "logoBg": "#0891b2", "type": "index",    "exchange": "OANDA", "isPositive": False, "flagged": True },
    { "symbol": "FX:EURUSD",       "name": "EURUSD",  "full": "EUR / U.S. Dollar",         "logoImg": "https://flagcdn.com/h24/eu.png",  "logoImg2": "https://flagcdn.com/h24/us.png", "logoBg": "#089981", "type": "forex", "exchange": "FX", "isPositive": True  },
    { "symbol": "FX:GBPUSD",       "name": "GBPUSD",  "full": "GBP / U.S. Dollar",         "logoImg": "https://flagcdn.com/h24/gb.png",  "logoImg2": "https://flagcdn.com/h24/us.png", "logoBg": "#1e54e4", "type": "forex", "exchange": "FX", "isPositive": False },
    { "symbol": "FX:NZDUSD",       "name": "NZDUSD",  "full": "NZD / U.S. Dollar",         "logoImg": "https://flagcdn.com/h24/nz.png",  "logoImg2": "https://flagcdn.com/h24/us.png", "logoBg": "#f23645", "type": "forex", "exchange": "FX", "isPositive": False },
    { "symbol": "BINANCE:BTCUSDT", "name": "BTCUSD",  "full": "Bitcoin / Tether",          "logoImg": "https://assets.coingecko.com/coins/images/1/small/bitcoin.png", "logoBg": "#f59e0b", "type": "crypto", "exchange": "BINANCE", "isPositive": False, "flagged": True },
    { "symbol": "FX:GBPJPY",       "name": "GBPJPY",  "full": "GBP / Japanese Yen",        "logoImg": "https://flagcdn.com/h24/gb.png",  "logoImg2": "https://flagcdn.com/h24/jp.png", "logoBg": "#b91c1c", "type": "forex", "exchange": "FX", "isPositive": False },
]
seed_default_watchlist(DEFAULT_WATCHLIST_SEED)


class WatchlistAddRequest(BaseModel):
    symbol:     str
    name:       str
    full:       str = ""
    logoImg:    str = ""
    logoImg2:   str = ""
    logoBg:     str = "#2962ff"
    logoText:   str = ""
    type:       str = ""
    exchange:   str = ""
    isPositive: bool = True
    flagged:    bool = False
    price:      str = "—"
    change:     str = "—"
    changePct:  str = "—"


def _row_to_frontend(row: dict) -> dict:
    """Convert DB snake_case row → camelCase for frontend."""
    return {
        "symbol":     row.get("symbol", ""),
        "name":       row.get("name", ""),
        "full":       row.get("full_name", ""),
        "logoImg":    row.get("logo_img", ""),
        "logoImg2":   row.get("logo_img2", "") or None,
        "logoBg":     row.get("logo_bg", "#2962ff"),
        "logoText":   row.get("logo_text", ""),
        "type":       row.get("type", ""),
        "exchange":   row.get("exchange", ""),
        "isPositive": bool(row.get("is_positive", True)),
        "flagged":    bool(row.get("flagged", False)),
        "price":      row.get("price", "—"),
        "change":     row.get("change", "—"),
        "changePct":  row.get("change_pct", "—"),
    }


@app.get("/api/watchlist")
def get_watchlist_endpoint():
    """Return all watchlist symbols ordered by position."""
    rows = get_watchlist()
    return {"items": [_row_to_frontend(r) for r in rows]}


@app.post("/api/watchlist")
def add_watchlist_endpoint(req: WatchlistAddRequest):
    """Add or update a symbol in the watchlist DB."""
    ok = add_watchlist_item(req.model_dump())
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to save watchlist item")
    return {"status": "ok", "symbol": req.symbol.upper()}


@app.delete("/api/watchlist/{symbol}")
def delete_watchlist_endpoint(symbol: str):
    """Remove a symbol from the watchlist DB."""
    ok = remove_watchlist_item(symbol)
    if not ok:
        raise HTTPException(status_code=404, detail=f"{symbol.upper()} not found in watchlist")
    return {"status": "ok", "symbol": symbol.upper()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)