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

_last_synced_mtime: float = 0.0

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
    """Copy the local SQLite DB snapshot to the Google Drive backup location.

    Skips the copy entirely when the database has not changed since the last
    sync, so the background loop is idle rather than writing files every tick.
    """
    global _gdrive_status, _last_synced_mtime
    if not LOCAL_DB.exists():
        return _gdrive_status

    try:
        db_mtime = LOCAL_DB.stat().st_mtime
        if db_mtime == _last_synced_mtime and _last_synced_mtime != 0.0:
            _gdrive_status["status"] = "idle"  # nothing new to back up
            return _gdrive_status

        _gdrive_status["status"] = "syncing"

        # Method B: Direct Google Drive API upload if credentials present
        try:
            from services.gdrive_api import upload_db_to_gdrive_api
            api_ok = upload_db_to_gdrive_api()
            if api_ok:
                print("[GDrive Sync] Uploaded database snapshot via Google Drive API")
        except Exception:
            pass  # API upload is optional — local sync continues below

        # Method A / Staging Sync (local folder or mounted Drive)
        gdrive_folder = resolve_gdrive_path()
        backup_file = gdrive_folder / "friday_trading_db_backup.sqlite"

        shutil.copy2(LOCAL_DB, backup_file)
        _last_synced_mtime = db_mtime

        now = time.time()
        _gdrive_status.update({
            "last_sync": now,
            "sync_count": _gdrive_status["sync_count"] + 1,
            "cloud_path": str(backup_file),
            "status": "synced"
        })
        print(f"[GDrive Sync] Backed up SQLite DB snapshot to: {backup_file.name}")
    except Exception as err:
        print(f"[GDrive Sync] Error backing up: {err}")
        _gdrive_status["status"] = "error"

    return _gdrive_status

def restore_from_gdrive_if_needed() -> bool:
    """If local DB is missing, restore latest database from Google Drive backup."""
    if LOCAL_DB.exists() and LOCAL_DB.stat().st_size > 0:
        return True
    try:
        gdrive_folder = resolve_gdrive_path()
        backup_file = gdrive_folder / "friday_trading_db_backup.sqlite"
        if backup_file.exists() and backup_file.stat().st_size > 0:
            shutil.copy2(backup_file, LOCAL_DB)
            print(f"[GDrive Sync] 🚀 Restored SQLite DB from Google Drive backup: {backup_file}")
            return True
    except Exception as err:
        print(f"[GDrive Sync] Error restoring DB from Google Drive: {err}")
    return False

_stop_event = threading.Event()
_sync_thread: list = []


def start_background_gdrive_sync(interval_seconds: int = 300):
    """Background loop that syncs database to Google Drive every N seconds silently."""
    global _sync_thread
    if _sync_thread:
        return
    _stop_event.clear()

    def sync_loop():
        restore_from_gdrive_if_needed()
        while not _stop_event.is_set():
            _stop_event.wait(interval_seconds)
            perform_gdrive_sync()

    t = threading.Thread(target=sync_loop, daemon=True, name="gdrive-sync")
    t.start()
    _sync_thread = [t]
    print(f"[GDrive Sync] Background Google Drive sync engine started (Interval: {interval_seconds}s)")


def stop_background_gdrive_sync() -> None:
    """Signal the gdrive sync worker to stop."""
    global _sync_thread
    _stop_event.set()
    _sync_thread = []


def get_gdrive_sync_status() -> dict:
    return _gdrive_status
