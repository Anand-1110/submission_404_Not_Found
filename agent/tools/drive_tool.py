"""
Google Drive Tool — creates client folder with subfolders
---------------------------------------------------------
Real implementation: pip install google-api-python-client google-auth
Mock mode: set MOCK_TOOLS=true in .env
"""

import os
import asyncio
import json
from datetime import datetime

MOCK = os.getenv("MOCK_TOOLS", "true").lower() == "true"
DRIVE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "credentials.json")
DRIVE_CREDENTIALS_CONTENT = os.getenv("GOOGLE_CREDENTIALS_JSON_CONTENT", "")  # Render env var
PARENT_FOLDER_ID = os.getenv("DRIVE_PARENT_FOLDER_ID", "")


def _get_google_credentials():
    """Load credentials from JSON string (cloud) or fallback to file (local)."""
    from google.oauth2 import service_account
    SCOPES = ["https://www.googleapis.com/auth/drive"]

    if DRIVE_CREDENTIALS_CONTENT:
        # ✅ Render / Cloud: credentials stored as raw JSON string in env var
        info = json.loads(DRIVE_CREDENTIALS_CONTENT)
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    else:
        # 💻 Local: read from credentials.json file
        return service_account.Credentials.from_service_account_file(
            DRIVE_CREDENTIALS_JSON, scopes=SCOPES
        )

SUBFOLDERS = ["01_Contracts", "02_Deliverables", "03_Assets", "04_Invoices", "05_Reports"]


async def create_drive_folder(payload: dict) -> dict:
    """
    Creates:
      /Clients/{client_name}/
        ├── 01_Contracts/
        ├── 02_Deliverables/
        ├── 03_Assets/
        ├── 04_Invoices/
        └── 05_Reports/
    Sets editor permissions for the account manager email.
    """
    await asyncio.sleep(1.2)   # simulate API call

    client_name = payload["client_name"]
    folder_name = f"[Client] {client_name}"

    if MOCK:
        mock_id = f"mock_drive_{client_name.lower().replace(' ', '_')}"
        mock_url = f"https://drive.google.com/drive/folders/{mock_id}"
        print(f"[MOCK DRIVE] Created folder '{folder_name}' → {mock_url}")
        print(f"[MOCK DRIVE] Created subfolders: {SUBFOLDERS}")
        return {
            "success": True,
            "mock": True,
            "folder_name": folder_name,
            "folder_id": mock_id,
            "folder_url": mock_url,
            "subfolders": SUBFOLDERS,
            "created_at": datetime.utcnow().isoformat(),
        }

    # ── Real Google Drive implementation ─────────────────────────────────────
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            creds = _get_google_credentials()
            service = build("drive", "v3", credentials=creds)

            # Create main client folder
            folder_meta = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [PARENT_FOLDER_ID] if PARENT_FOLDER_ID else [],
            }
            folder = service.files().create(body=folder_meta, fields="id,webViewLink").execute()
            folder_id = folder["id"]
            folder_url = folder["webViewLink"]

            # Create subfolders
            for sub in SUBFOLDERS:
                sub_meta = {
                    "name": sub,
                    "mimeType": "application/vnd.google-apps.folder",
                    "parents": [folder_id],
                }
                service.files().create(body=sub_meta, fields="id").execute()

            # Share with account manager
            am_email = os.getenv("MANAGER_EMAIL", "")
            if am_email:
                service.permissions().create(
                    fileId=folder_id,
                    body={"type": "user", "role": "writer", "emailAddress": am_email},
                ).execute()

            return {
                "success": True,
                "folder_name": folder_name,
                "folder_id": folder_id,
                "folder_url": folder_url,
                "subfolders": SUBFOLDERS,
                "created_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            if attempt < max_retries:
                print(f"[Drive API] Attempt {attempt+1} failed: {e}. Retrying in 2 seconds...")
                await asyncio.sleep(2)
            else:
                return {
                    "success": False, 
                    "error": str(e),
                    "manual_override_required": f"Please manually create '{folder_name}' in Google Drive and share it with {os.getenv('MANAGER_EMAIL')}."
                }
