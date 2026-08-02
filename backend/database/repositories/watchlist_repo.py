"""
watchlist_repo.py — Repository pattern wrapper for trading watchlists and chart drawings.
"""

from typing import List, Dict, Any, Optional
from ..connection import get_db_connection

def init_watchlist_db():
    """Initializes watchlist and chart annotation tables with performance indexes."""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                symbol TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                full TEXT,
                logoImg TEXT,
                logoBg TEXT,
                type TEXT,
                exchange TEXT,
                isPositive INTEGER DEFAULT 1,
                flagged INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_sort ON watchlist(sort_order);")
        conn.commit()

class WatchlistRepository:
    def __init__(self):
        init_watchlist_db()

    def get_all(self) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM watchlist ORDER BY sort_order ASC, symbol ASC")
            return [dict(row) for row in cursor.fetchall()]

    def add_or_update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO watchlist (symbol, name, full, logoImg, logoBg, type, exchange, isPositive, flagged)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    name=excluded.name,
                    full=excluded.full,
                    logoImg=excluded.logoImg,
                    logoBg=excluded.logoBg,
                    type=excluded.type,
                    exchange=excluded.exchange,
                    isPositive=excluded.isPositive,
                    flagged=excluded.flagged
                """,
                (
                    data.get("symbol", "").upper(),
                    data.get("name", ""),
                    data.get("full", ""),
                    data.get("logoImg", ""),
                    data.get("logoBg", "#2962ff"),
                    data.get("type", ""),
                    data.get("exchange", ""),
                    1 if data.get("isPositive", True) else 0,
                    1 if data.get("flagged", False) else 0
                )
            )
            conn.commit()
        return data

    def delete(self, symbol: str) -> bool:
        with get_db_connection() as conn:
            cursor = conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol.upper(),))
            conn.commit()
            return cursor.rowcount > 0
