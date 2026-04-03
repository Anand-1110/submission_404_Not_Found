"""
Credential Tester — run this BEFORE starting the real agent.
Tests each API connection independently so you know exactly what's working.

Usage:
    cd e:\\Agent
    python agent/test_credentials.py
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

load_dotenv()

PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "


def section(title: str):
    print(f"\n{'─' * 55}")
    print(f"  {title}")
    print(f"{'─' * 55}")


# ── Email (Gmail or SendGrid) ─────────────────────────────────────────────────

def test_sendgrid():
    use_gmail = os.getenv("USE_GMAIL", "false").lower() == "true"

    if use_gmail:
        # ── Gmail SMTP test ────────────────────────────────────────────────────
        section("Gmail — Email")
        gmail_address = os.getenv("GMAIL_ADDRESS", "")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD", "")
        from_email = os.getenv("FROM_EMAIL", gmail_address)

        if not gmail_address:
            print(f"  {FAIL} GMAIL_ADDRESS not set in .env")
            return False
        if not gmail_password:
            print(f"  {FAIL} GMAIL_APP_PASSWORD not set in .env")
            return False

        try:
            import smtplib
            import ssl as ssl_module
            ctx = ssl_module.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as server:
                server.login(gmail_address, gmail_password)
            print(f"  {PASS} Gmail SMTP connected — account: {gmail_address}")
            print(f"  {PASS} FROM email: {from_email}")
            return True
        except smtplib.SMTPAuthenticationError:
            print(f"  {FAIL} Gmail authentication failed")
            print(f"       → Make sure you used an App Password (not your Gmail password)")
            print(f"       → Create one at: myaccount.google.com/apppasswords")
            return False
        except Exception as e:
            print(f"  {FAIL} Gmail SMTP error: {e}")
            return False
    else:
        # ── SendGrid API test ──────────────────────────────────────────────────
        section("SendGrid — Email")
        key = os.getenv("SENDGRID_API_KEY", "")
        from_email = os.getenv("FROM_EMAIL", "")
        manager_email = os.getenv("MANAGER_EMAIL", "")

        if not key or "PASTE" in key or key.startswith("SG.your"):
            print(f"  {FAIL} SENDGRID_API_KEY not set in .env")
            return False
        if not from_email:
            print(f"  {FAIL} FROM_EMAIL not set in .env")
            return False
        if not manager_email:
            print(f"  {WARN} MANAGER_EMAIL not set — completion summaries won't be sent")

        try:
            import ssl as ssl_module
            import certifi
            from sendgrid import SendGridAPIClient
            sg = SendGridAPIClient(key)
            response = sg.client.user.profile.get()
            if response.status_code == 200:
                import json
                profile = json.loads(response.body)
                print(f"  {PASS} SendGrid connected — account: {profile.get('email', 'unknown')}")
                print(f"  {PASS} FROM email: {from_email}")
                return True
            else:
                print(f"  {FAIL} SendGrid returned status {response.status_code}")
                return False
        except ImportError:
            print(f"  {FAIL} sendgrid package not installed — run: pip install sendgrid")
            return False
        except Exception as e:
            print(f"  {FAIL} SendGrid error: {e}")
            return False


# ── Google Drive ──────────────────────────────────────────────────────────────

def test_google_drive():
    section("Google Drive — Folder Creation")
    creds_file = os.getenv("GOOGLE_CREDENTIALS_JSON", "credentials.json")
    parent_id = os.getenv("DRIVE_PARENT_FOLDER_ID", "")

    if not os.path.exists(creds_file):
        print(f"  {FAIL} credentials.json not found at: {os.path.abspath(creds_file)}")
        print(f"       Download from: Google Cloud Console → Service Accounts → Keys → JSON")
        return False
    if not parent_id:
        print(f"  {WARN} DRIVE_PARENT_FOLDER_ID not set — folders will be created at Drive root")

    try:
        from googleapiclient.discovery import build
        from google.oauth2 import service_account

        creds = service_account.Credentials.from_service_account_file(
            creds_file,
            scopes=["https://www.googleapis.com/auth/drive"],
        )
        service = build("drive", "v3", credentials=creds)
        about = service.about().get(fields="user").execute()
        email = about.get("user", {}).get("emailAddress", "unknown")
        print(f"  {PASS} Google Drive connected — service account: {email}")
        if parent_id:
            # Check we can see the parent folder
            folder = service.files().get(fileId=parent_id, fields="name,id").execute()
            print(f"  {PASS} Parent folder accessible: '{folder['name']}'")
            print(f"       ⚠️  Make sure you shared this folder with: {email}")
        return True
    except ImportError:
        print(f"  {FAIL} google packages not installed — run: pip install google-api-python-client google-auth")
        return False
    except Exception as e:
        print(f"  {FAIL} Google Drive error: {e}")
        return False


# ── Notion ────────────────────────────────────────────────────────────────────

def test_notion():
    section("Notion — Page Creation")
    key = os.getenv("NOTION_API_KEY", "")
    parent_id = os.getenv("NOTION_PARENT_PAGE_ID", "")

    if not key or key.startswith("secret_your"):
        print(f"  {FAIL} NOTION_API_KEY not set in .env")
        return False
    if not parent_id:
        print(f"  {FAIL} NOTION_PARENT_PAGE_ID not set in .env")
        return False

    try:
        from notion_client import Client
        notion = Client(auth=key)
        # Fetch the parent page to verify access
        page = notion.pages.retrieve(page_id=parent_id)
        title_objs = page.get("properties", {}).get("title", {}).get("title", [])
        title = title_objs[0]["text"]["content"] if title_objs else "(untitled)"
        print(f"  {PASS} Notion connected")
        print(f"  {PASS} Parent page accessible: '{title}'")
        return True
    except ImportError:
        print(f"  {FAIL} notion-client package not installed — run: pip install notion-client")
        return False
    except Exception as e:
        print(f"  {FAIL} Notion error: {e}")
        print(f"       Make sure you've shared the parent page with your integration!")
        return False


# ── Airtable ──────────────────────────────────────────────────────────────────

def test_airtable():
    section("Airtable — CRM Records")
    key = os.getenv("AIRTABLE_API_KEY", "")
    base_id = os.getenv("AIRTABLE_BASE_ID", "")
    table = os.getenv("AIRTABLE_TABLE_NAME", "Clients")

    if not key or "your_" in key:
        print(f"  {FAIL} AIRTABLE_API_KEY not set in .env")
        return False
    if not base_id or base_id.startswith("appXXX"):
        print(f"  {FAIL} AIRTABLE_BASE_ID not set in .env")
        return False

    try:
        from pyairtable import Api
        api = Api(key)
        tbl = api.table(base_id, table)
        # Try listing 1 record to test access
        records = tbl.all(max_records=1)
        print(f"  {PASS} Airtable connected — base: {base_id}")
        print(f"  {PASS} Table '{table}' accessible ({len(records)} existing records)")
        return True
    except ImportError:
        print(f"  {FAIL} pyairtable package not installed — run: pip install pyairtable")
        return False
    except Exception as e:
        print(f"  {FAIL} Airtable error: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "═" * 55)
    print("  Scrollhouse Agent — Credential Tester")
    print("═" * 55)

    mock = os.getenv("MOCK_TOOLS", "true").lower()
    if mock == "true":
        print(f"\n  {WARN}  MOCK_TOOLS=true in your .env")
        print("  Change it to MOCK_TOOLS=false to use real APIs!\n")

    results = {
        "SendGrid": test_sendgrid(),
        "Google Drive": test_google_drive(),
        "Notion": test_notion(),
        "Airtable": test_airtable(),
    }

    print("\n" + "═" * 55)
    print("  Summary")
    print("═" * 55)
    all_ok = True
    for name, ok in results.items():
        icon = PASS if ok else FAIL
        print(f"  {icon}  {name}")
        if not ok:
            all_ok = False

    if all_ok:
        print(f"\n  🚀 All credentials valid! Start the agent with:")
        print(f"     uvicorn agent.main:app --reload --port 8000\n")
    else:
        print(f"\n  ⚠️  Fix the issues above, then re-run this script.\n")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
