import os
import time
from dotenv import load_dotenv

load_dotenv()

def cleanup_airtable():
    print("Checking Airtable...")
    try:
        from pyairtable import Api
        key = os.getenv("AIRTABLE_API_KEY")
        base = os.getenv("AIRTABLE_BASE_ID")
        table_name = os.getenv("AIRTABLE_TABLE_NAME", "Clients")
        if not key or mock_mode(): return
        
        api = Api(key)
        tb = api.table(base, table_name)
        records = tb.all()
        if records:
            tb.batch_delete([r['id'] for r in records])
            print(f" 🗑️ Airtable: Deleted {len(records)} test records.")
        else:
            print(" ⏭️ Airtable: Already clean.")
    except Exception as e:
        print(f" [Airtable Error] {e}")

def cleanup_notion():
    print("Checking Notion...")
    try:
        from notion_client import Client
        key = os.getenv("NOTION_API_KEY")
        parent = os.getenv("NOTION_PARENT_PAGE_ID")
        if not key or mock_mode(): return
        
        notion = Client(auth=key)
        
        # Notion blocks.children.list grabs everything under the parent page.
        results = notion.blocks.children.list(block_id=parent)
        idx = 0
        for block in results.get("results", []):
            if block.get("type") == "child_page":
                notion.pages.update(page_id=block["id"], archived=True)
                idx += 1
                time.sleep(0.3) # Avoid rate limits
                
        print(f" 🗑️ Notion: Archived {idx} test pages.")
    except Exception as e:
        print(f" [Notion Error] {e}")

def cleanup_drive():
    print("Checking Google Drive...")
    try:
        from googleapiclient.discovery import build
        from google.oauth2 import service_account

        cred_path = os.getenv("GOOGLE_CREDENTIALS_JSON", "credentials.json")
        parent = os.getenv("DRIVE_PARENT_FOLDER_ID")
        
        if not os.path.exists(cred_path) or mock_mode() or not parent:
            return

        creds = service_account.Credentials.from_service_account_file(
            cred_path,
            scopes=["https://www.googleapis.com/auth/drive"],
        )
        service = build("drive", "v3", credentials=creds)
        
        # Find all files/folders inside the main CRM drive folder
        query = f"'{parent}' in parents"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])
        
        idx = 0
        for f in files:
            service.files().delete(fileId=f['id']).execute()
            idx += 1
            time.sleep(0.2)
            
        print(f" 🗑️ Google Drive: Permanently deleted {idx} test client folders.")
    except Exception as e:
        print(f" [Drive Error] {e}")

def mock_mode():
    return os.getenv("MOCK_TOOLS", "true").lower() == "true"

if __name__ == "__main__":
    print("====================================")
    print("🧹 STARTING TEST DATA CLEANUP SCRIPT")
    print("====================================")
    
    if mock_mode():
        print("WARNING: MOCK_TOOLS is enabled. Real databases won't be touched.")
        
    cleanup_airtable()
    cleanup_notion()
    cleanup_drive()
    print("====================================")
    print("Cleanup Complete! System is zeroed out.")
