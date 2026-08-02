"""
connection.py — Centralized, thread-safe SQLite connection factory for F.R.I.D.A.Y.
Enforces WAL (Write-Ahead Logging) mode, foreign key constraints, and standard timeout handling.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'data' / 'friday_brain.db'

def get_db_connection() -> sqlite3.Connection:
    """Returns a SQLite connection with WAL mode and row factory enabled."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn
