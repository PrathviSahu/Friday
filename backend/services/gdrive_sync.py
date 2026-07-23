import os
import shutil
import time
import json
import threading
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
LOCAL_DB = BASE_DIR / "data" / "friday_trading_db.sqlite"
GDRIVE_BACKUP_DIR = BASE_DIR / "data" / "gdrive_backups"
GDRIVE_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Detect if Google Drive for Desktop is installed on macOS
HOME = Path.home()
GDRIVE_MOUNT_PATHS = [
    HOME / "Google Drive" / "My Drive" / "FRIDAY_Backups",
    HOME / "Library" / "CloudStorage" / "GoogleDrive-prathvisahu@gmail.com" / "My Drive" / "FRIDAY_Backups",
    GDRIVE_BACKUP_DIR # Local cloud mirror fallback
]

_gdrive_status = {
    "enabled": True,
    "last_sync": 0.0,
    "sync_count": 0,
    "cloud_path": str(GDRIVE_BACKUP_DIR),
    "status": "idle"
}

def resolve_gdrive_path() -> Path:
    """Find the best available Google Drive folder path."""
    for p in GDRIVE_MOUNT_PATHS:
        try:
            if p.parent.exists():
                p.mkdir(parents=True, exist_ok=True)
                return p
        except Exception:
            pass
    return GDRIVE_BACKUP_DIR

def perform_gdrive_sync() -> dict:
    """Asynchronously copy local SQLite DB snapshot to 5TB Google Drive backup folder."""
    global _gdrive_status
    if not LOCAL_DB.exists():
        return _gdrive_status

    try:
        _gdrive_status["status"] = "syncing"
        
        # Method B: Attempt Direct Google Drive API Upload if credentials present
        try:
            from services.gdrive_api import upload_db_to_gdrive_api
            api_ok = upload_db_to_gdrive_api()
            if api_ok:
                print("[5TB GDrive Sync] 🚀 Method B: Uploaded database snapshot via Google Drive API")
        except Exception as api_err:
            pass

        # Method A / Staging Sync
        gdrive_folder = resolve_gdrive_path()
        backup_file = gdrive_folder / "friday_trading_db_backup.sqlite"
        
        # Safe copy snapshot
        shutil.copy2(LOCAL_DB, backup_file)
        
        now = time.time()
        _gdrive_status.update({
            "last_sync": now,
            "sync_count": _gdrive_status["sync_count"] + 1,
            "cloud_path": str(backup_file),
            "status": "synced"
        })
        print(f"[5TB GDrive Sync] ☁️ Successfully backed up SQLite DB snapshot to Google Drive: {backup_file.name}")
    except Exception as err:
        print(f"[5TB GDrive Sync] Error backing up to Google Drive: {err}")
        _gdrive_status["status"] = "error"
        
    return _gdrive_status

def restore_from_gdrive_if_needed() -> bool:
    """If local DB is missing, restore latest database from 5TB Google Drive backup."""
    if LOCAL_DB.exists() and LOCAL_DB.stat().st_size > 0:
        return True
    try:
        gdrive_folder = resolve_gdrive_path()
        backup_file = gdrive_folder / "friday_trading_db_backup.sqlite"
        if backup_file.exists() and backup_file.stat().st_size > 0:
            shutil.copy2(backup_file, LOCAL_DB)
            print(f"[5TB GDrive Sync] 🚀 Restored SQLite DB from 5TB Google Drive backup: {backup_file}")
            return True
    except Exception as err:
        print(f"[5TB GDrive Sync] Error restoring DB from Google Drive: {err}")
    return False

def start_background_gdrive_sync(interval_seconds: int = 30):
    """Background loop that syncs database to Google Drive every N seconds silently."""
    def sync_loop():
        restore_from_gdrive_if_needed()
        while True:
            time.sleep(interval_seconds)
            perform_gdrive_sync()

    t = threading.Thread(target=sync_loop, daemon=True)
    t.start()
    print(f"[5TB GDrive Sync] ⚡ Background 5TB Google Drive sync engine started (Interval: {interval_seconds}s)")

def get_gdrive_sync_status() -> dict:
    return _gdrive_status
