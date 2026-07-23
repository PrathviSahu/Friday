import sqlite3
import json
import time
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "friday_trading_db.sqlite"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def init_trading_db():
    """Initialize SQLite database table for TradingView chart drawings and layouts."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chart_drawings (
                symbol TEXT PRIMARY KEY,
                drawings_data TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
        ''')
        conn.commit()

init_trading_db()

def get_chart_drawings(symbol: str) -> dict:
    """Fetch saved chart drawings & layout data from SQLite database for a specific symbol."""
    if not symbol:
        return {}
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT drawings_data, updated_at FROM chart_drawings WHERE symbol = ?", (symbol.upper(),))
            row = cursor.fetchone()
            if row:
                return {
                    "symbol": symbol.upper(),
                    "drawings_data": json.loads(row[0]),
                    "updated_at": row[1]
                }
    except Exception as err:
        print(f"[Trading DB] Error fetching drawings for {symbol}: {err}")
    return {"symbol": symbol.upper(), "drawings_data": {}, "updated_at": time.time()}

def save_chart_drawings(symbol: str, drawings_data: dict) -> bool:
    """Save or update chart drawings & layout data in SQLite database."""
    if not symbol:
        return False
    try:
        data_str = json.dumps(drawings_data)
        now = time.time()
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO chart_drawings (symbol, drawings_data, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    drawings_data = excluded.drawings_data,
                    updated_at = excluded.updated_at
            ''', (symbol.upper(), data_str, now))
            conn.commit()
            print(f"[Trading DB] ✅ Saved drawings & layout for {symbol.upper()} to SQLite DB ({len(data_str)} bytes)")
            return True
    except Exception as err:
        print(f"[Trading DB] Error saving drawings for {symbol}: {err}")
        return False
