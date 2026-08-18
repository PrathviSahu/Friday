"""scripts/verify_persistence.py — DEP-002 Persistence Simulation and Audit.

Tests write, read, and simulated ephemeral container reset behavior across
friday.db, career.db, and embeddings.db.
"""

import sqlite3
import tempfile
import shutil
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "backend" / "data"


def audit_persistence_model():
    print("=" * 70)
    print("🔍 DEP-002: DATABASE PERSISTENCE AUDIT & RESTART SIMULATION")
    print("=" * 70)

    db_files = {
        "friday.db": DATA_DIR / "friday.db",
        "career.db": DATA_DIR / "career.db",
        "embeddings.db": DATA_DIR / "embeddings.db",
    }

    schema_inventory = {}
    for name, path in db_files.items():
        if path.exists():
            with sqlite3.connect(path) as conn:
                tables = [
                    r[0] for r in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    ).fetchall()
                ]
                schema_inventory[name] = tables
        else:
            schema_inventory[name] = []

    print("\n📦 Active SQLite Schema Inventory:")
    for db, tbls in schema_inventory.items():
        print(f"  • {db} ({len(tbls)} tables): {', '.join(tbls)}")

    # Simulation: Write -> Ephemeral Reset -> Re-seed
    print("\n🧪 Testing Simulated Ephemeral Container Reset:")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_data = Path(tmp_dir) / "data"
        tmp_data.mkdir(parents=True, exist_ok=True)
        test_db = tmp_data / "friday.db"

        # Step 1: Initialize and write
        with sqlite3.connect(test_db) as conn:
            conn.execute("CREATE TABLE todos (id TEXT PRIMARY KEY, text TEXT, priority TEXT, done INT)")
            conn.execute("INSERT INTO todos VALUES ('todo_1', 'Deploy to Render', 'high', 0)")
            conn.commit()

        # Verify record exists
        with sqlite3.connect(test_db) as conn:
            cnt1 = conn.execute("SELECT COUNT(*) FROM todos").fetchone()[0]
        print(f"  1. Record written: {cnt1} row present.")

        # Step 2: Simulate Ephemeral Container Wipe (Render Free spin-down / redeploy)
        shutil.rmtree(tmp_data)
        tmp_data.mkdir(parents=True, exist_ok=True)
        print("  2. Container redeploy / cold restart: Ephemeral volume wiped.")

        # Step 3: Startup re-init
        test_db_fresh = tmp_data / "friday.db"
        with sqlite3.connect(test_db_fresh) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS todos (id TEXT PRIMARY KEY, text TEXT, priority TEXT, done INT)")
            cnt2 = conn.execute("SELECT COUNT(*) FROM todos").fetchone()[0]
        print(f"  3. Fresh container startup: {cnt2} rows (data lost without durable volume).")

    print("\n📋 PERSISTENCE ASSESSMENT:")
    print("  • Status: PERSISTENCE RISK (Render Free tier storage is EPHEMERAL).")
    print("  • GDrive Snapshot Sync: Uploads periodic backups, but is asynchronous and non-transactional.")
    print("  • Recommendation for Production Durability:")
    print("    Option 1: Attach Render Persistent Disk (/app/data on Render Starter/Team plan).")
    print("    Option 2: Use Turso / LibSQL (Hosted SQLite over HTTP with automatic edge sync).")
    print("    Option 3: External PostgreSQL / Neon DB for persistent multi-tenant storage.")


if __name__ == "__main__":
    audit_persistence_model()
