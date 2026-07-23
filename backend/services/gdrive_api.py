import os
import json
import time
import shutil
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# Scopes required for 5TB Google Drive access
SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']

BASE_DIR = Path(__file__).parent.parent
LOCAL_DB = BASE_DIR / "data" / "friday_trading_db.sqlite"
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
SERVICE_ACCOUNT_FILE = BASE_DIR / "service_account.json"
TOKEN_FILE = BASE_DIR / "token.json"

_gdrive_api_status = {
    "connected": False,
    "method": "API",
    "account": "None",
    "folder_id": "",
    "last_sync": 0.0,
    "status": "unauthenticated"
}

def get_gdrive_service():
    """Authenticate and return Google Drive API service client."""
    global _gdrive_api_status
    creds = None

    # Option 1: Service Account JSON (Zero user prompt, ideal for background services)
    if SERVICE_ACCOUNT_FILE.exists():
        try:
            creds = service_account.Credentials.from_service_account_file(
                str(SERVICE_ACCOUNT_FILE), scopes=SCOPES
            )
            service = build('drive', 'v3', credentials=creds)
            _gdrive_api_status.update({"connected": True, "method": "ServiceAccount", "status": "authenticated"})
            return service
        except Exception as e:
            print(f"[GDrive API] Service Account auth error: {e}")

    # Option 2: OAuth 2.0 User Token JSON (token.json or credentials.json)
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception as e:
            print(f"[GDrive API] Token load error: {e}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                TOKEN_FILE.write_text(creds.to_json())
            except Exception as e:
                print(f"[GDrive API] Token refresh error: {e}")
                creds = None
        
        if not creds and CREDENTIALS_FILE.exists():
            try:
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
                creds = flow.run_local_server(port=0)
                TOKEN_FILE.write_text(creds.to_json())
            except Exception as e:
                print(f"[GDrive API] OAuth Flow error: {e}")
                return None

    if creds and creds.valid:
        try:
            service = build('drive', 'v3', credentials=creds)
            # Fetch user email details
            about = service.about().get(fields="user, storageQuota").execute()
            user_email = about.get("user", {}).get("emailAddress", "Authenticated User")
            _gdrive_api_status.update({
                "connected": True,
                "account": user_email,
                "status": "authenticated"
            })
            return service
        except Exception as e:
            print(f"[GDrive API] Service build error: {e}")

    _gdrive_api_status.update({"connected": False, "status": "unauthenticated"})
    return None


def get_or_create_gdrive_vault_folder(service) -> str:
    """Get or create the root FRIDAY_AI_Vault folder in Google Drive."""
    if not service:
        return ""
    try:
        query = "mimeType='application/vnd.google-apps.folder' and name='FRIDAY_AI_Vault' and trashed=false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])
        if files:
            folder_id = files[0]['id']
            _gdrive_api_status["folder_id"] = folder_id
            return folder_id

        # Create folder if it doesn't exist
        file_metadata = {
            'name': 'FRIDAY_AI_Vault',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        folder_id = folder.get('id')
        _gdrive_api_status["folder_id"] = folder_id
        print(f"[GDrive API] 📁 Created root folder 'FRIDAY_AI_Vault' in 5TB Google Drive (ID: {folder_id})")
        return folder_id
    except Exception as e:
        print(f"[GDrive API] Error resolving vault folder: {e}")
        return ""


def upload_db_to_gdrive_api() -> bool:
    """Upload local SQLite database snapshot directly to 5TB Google Drive via API."""
    global _gdrive_api_status
    if not LOCAL_DB.exists():
        return False
    service = get_gdrive_service()
    if not service:
        return False

    try:
        folder_id = get_or_create_gdrive_vault_folder(service)
        filename = "friday_trading_db_backup.sqlite"
        
        # Check if file already exists in vault folder
        query = f"'{folder_id}' in parents and name='{filename}' and trashed=false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])

        media = MediaFileUpload(str(LOCAL_DB), mimetype='application/x-sqlite3', resumable=True)

        if files:
            file_id = files[0]['id']
            service.files().update(fileId=file_id, media_body=media).execute()
            print(f"[GDrive API] ☁️ Updated database file in 5TB Google Drive (ID: {file_id})")
        else:
            file_metadata = {'name': filename, 'parents': [folder_id]} if folder_id else {'name': filename}
            created = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            print(f"[GDrive API] ☁️ Created new database file in 5TB Google Drive (ID: {created.get('id')})")

        _gdrive_api_status.update({
            "last_sync": time.time(),
            "status": "synced"
        })
        return True
    except Exception as e:
        print(f"[GDrive API] Error uploading database: {e}")
        _gdrive_api_status["status"] = "error"
        return False


def get_gdrive_api_status() -> dict:
    return _gdrive_api_status
