"""routes/watchlist.py — watchlist CRUD + default seed data."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import require_boss
from database.watchlist_db import (
    get_watchlist,
    add_watchlist_item,
    remove_watchlist_item,
    seed_default_watchlist,
)

router = APIRouter(prefix="/api", tags=["watchlist"])

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


def seed_watchlist() -> None:
    """Seed the default watchlist on startup (only if the table is empty)."""
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


@router.get("/watchlist", dependencies=[Depends(require_boss)])
def get_watchlist_endpoint():
    """Return all watchlist symbols ordered by position."""
    rows = get_watchlist()
    return {"items": [_row_to_frontend(r) for r in rows]}


@router.post("/watchlist", dependencies=[Depends(require_boss)])
def add_watchlist_endpoint(req: WatchlistAddRequest):
    """Add or update a symbol in the watchlist DB."""
    ok = add_watchlist_item(req.model_dump())
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to save watchlist item")
    return {"status": "ok", "symbol": req.symbol.upper()}


@router.delete("/watchlist/{symbol}", dependencies=[Depends(require_boss)])
def delete_watchlist_endpoint(symbol: str):
    """Remove a symbol from the watchlist DB."""
    ok = remove_watchlist_item(symbol)
    if not ok:
        raise HTTPException(status_code=404, detail=f"{symbol.upper()} not found in watchlist")
    return {"status": "ok", "symbol": symbol.upper()}
