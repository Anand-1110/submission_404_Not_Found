
import os
import requests
import json
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Load environment variables
load_dotenv()

# --- Configurations ---
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY", "").strip()
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "").strip()
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME", "Clients").strip()

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "").strip()
NOTION_PARENT_PAGE_ID = os.getenv("NOTION_PARENT_PAGE_ID", "").strip()

DRIVE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "credentials.json")
DRIVE_CREDENTIALS_CONTENT = os.getenv("GOOGLE_CREDENTIALS_JSON_CONTENT", "")
DRIVE_PARENT_FOLDER_ID = os.getenv("DRIVE_PARENT_FOLDER_ID", "").strip()

def cleanup_airtable():
    print(f"--- Cleaning Airtable [{AIRTABLE_TABLE_NAME}] ---")
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        print("[SKIP] Airtable credentials missing.")
        return

    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}"}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"[ERROR] Failed to fetch Airtable records: {response.status_code} {response.text}")
            return
            
        records = response.json().get("records", [])
        if not records:
            print("[INFO] No records found to delete.")
            return

        print(f"[INFO] Found {len(records)} records. Deleting...")
        for i in range(0, len(records), 10):
            batch = records[i:i+10]
            record_ids = [r['id'] for r in batch]
            params = [('records[]', r_id) for r_id in record_ids]
            requests.delete(url, headers=headers, params=params)
        print("[SUCCESS] Airtable cleaned.")
    except Exception as e:
        print(f"[ERROR] Airtable cleanup failed: {e}")

def cleanup_notion():
    print(f"\n--- Cleaning Notion [Parent ID: {NOTION_PARENT_PAGE_ID}] ---")
    if not NOTION_API_KEY or not NOTION_PARENT_PAGE_ID:
        print("[SKIP] Notion credentials missing.")
        return

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    url = f"https://api.notion.com/v1/blocks/{NOTION_PARENT_PAGE_ID}/children"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"[ERROR] Failed to fetch Notion children: {response.status_code} {response.text}")
            return
            
        child_pages = [r for r in response.json().get("results", []) if r['type'] == 'child_page']
        if not child_pages:
            print("[INFO] No child pages found.")
            return

        print(f"[INFO] Found {len(child_pages)} pages. Archiving...")
        for page in child_pages:
            archive_url = f"https://api.notion.com/v1/pages/{page['id']}"
            requests.patch(archive_url, headers=headers, json={"archived": True})
        print("[SUCCESS] Notion cleaned.")
    except Exception as e:
        print(f"[ERROR] Notion cleanup failed: {e}")

def cleanup_drive():
    print(f"\n--- Cleaning Google Drive [Parent ID: {DRIVE_PARENT_FOLDER_ID}] ---")
    if not DRIVE_PARENT_FOLDER_ID:
        print("[SKIP] Drive Parent Folder ID missing.")
        return

    try:
        SCOPES = ["https://www.googleapis.com/auth/drive"]
        if DRIVE_CREDENTIALS_CONTENT:
            info = json.loads(DRIVE_CREDENTIALS_CONTENT)
            creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        else:
            creds = service_account.Credentials.from_service_account_file(DRIVE_CREDENTIALS_JSON, scopes=SCOPES)
        
        service = build("drive", "v3", credentials=creds)
        
        # 1. List all items in the parent folder
        query = f"'{DRIVE_PARENT_FOLDER_ID}' in parents and trashed = false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get("files", [])
        
        if not items:
            print("[INFO] No Google Drive folders found to clean.")
            return

        print(f"[INFO] Found {len(items)} items. Moving to Trash...")
        for item in items:
            service.files().update(fileId=item['id'], body={"trashed": True}).execute()
            print(f"[SUCCESS] Trashed: {item['name']}")
            
        print("[SUCCESS] Google Drive cleaned.")
    except Exception as e:
        print(f"[ERROR] Google Drive cleanup failed: {e}")

if __name__ == "__main__":
    # cleanup_airtable()  # Already cleaned but good to keep as part of a full cleanup
    # cleanup_notion()    # Already cleaned
    cleanup_drive()
    print("\n✨ All systems clear! Go for it.")
