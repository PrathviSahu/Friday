"""routes/trading.py — market data, OHLCV charts, symbol search, TA."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import require_boss
from database.chart_db import get_chart_drawings, save_chart_drawings
from services.chart_data import fetch_ohlcv, search_symbols
from services.market_data import fetch_live_market_prices
from services.indian_market_data import get_indian_market_prices, is_market_open
from services.technical_analysis import analyze_symbol
from services.permissions import require_permission

router = APIRouter(prefix="/api", tags=["trading"])


class ChartSaveRequest(BaseModel):
    symbol: str
    drawings_data: dict


@router.get("/trading/chart-db")
def get_chart_drawings_endpoint(symbol: str = "OANDA:NAS100USD"):
    """Fetch saved chart drawings & layout data from SQLite database."""
    return get_chart_drawings(symbol)


@router.post("/trading/chart-db", dependencies=[Depends(require_boss)])
def save_chart_drawings_endpoint(req: ChartSaveRequest):
    """Save chart drawings & layout data to SQLite database."""
    ok = save_chart_drawings(req.symbol, req.drawings_data)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to save chart drawings")
    return {"status": "ok", "symbol": req.symbol.upper()}


@router.get("/trading/live-prices")
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


@router.get("/trading/indian-prices")
def get_indian_prices_endpoint():
    """Get live Indian market data (NSE/BSE) via Yahoo Finance. Refreshes every 3 min."""
    data = get_indian_market_prices()
    import time
    return {
        "market_open": is_market_open(),
        "prices": data,
        "timestamp": time.time(),
    }


@router.get("/trading/ohlcv")
def get_ohlcv_endpoint(symbol: str = "FX:EURUSD", interval: str = "5"):
    """Fetch OHLCV candle data — Forex optimised, 24/5 always live.

    Supports FX pairs, Gold, DXY, Crypto, US stocks, Indices.
    interval: 1, 5, 15, 30, 60, 240 (minutes), D (daily), W (weekly)
    """
    return fetch_ohlcv(symbol, interval)


@router.get("/trading/analysis")
def trading_analysis_endpoint(symbol: str = "FX:EURUSD", interval: str = "15"):
    """Run the real technical-analysis engine on live OHLCV data.

    Returns structured indicator values + a natural-language spoken summary.
    """
    try:
        return analyze_symbol(symbol, interval)
    except Exception as e:
        return {
            "symbol": symbol,
            "interval": interval,
            "error": str(e),
            "summary": f"Sorry Prem, I could not analyze {symbol}: {e}",
        }


@router.get("/trading/search")
def search_trading_symbols(q: str = ""):
    """Live real-time search across ALL 5000+ stocks on Earth (NSE, BSE, NASDAQ, NYSE, Forex, Crypto)."""
    return {"results": search_symbols(q)}


class PaperOrderRequest(BaseModel):
    symbol: str
    side: str  # buy | sell
    quantity: int
    order_type: str = "market"  # market | limit
    limit_price: float = 0


@router.post("/trading/order", dependencies=[Depends(require_boss),
                                             Depends(require_permission("trades.execute"))])
def place_paper_order(req: PaperOrderRequest):
    """Place a PAPER (simulated) order.

    Design constraint from the roadmap: trade execution NEVER happens
    automatically — the `trades.execute` permission defaults to `ask`, so
    this endpoint returns 403 (approval_required) until the owner grants a
    short-lived one-time approval in the Permission Center.
    """
    if req.side not in ("buy", "sell"):
        raise HTTPException(400, "side must be 'buy' or 'sell'")
    if req.quantity <= 0:
        raise HTTPException(400, "quantity must be positive")
    return {
        "status": "paper_order_accepted",
        "symbol": req.symbol.upper(),
        "side": req.side,
        "quantity": req.quantity,
        "order_type": req.order_type,
        "note": "Paper/simulated only — no real execution. Confirmed by owner.",
    }
