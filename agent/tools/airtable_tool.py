"""
Airtable Tool — creates a CRM record with all client info + resource links
---------------------------------------------------------------------------
Real implementation: pip install pyairtable
Mock mode: set MOCK_TOOLS=true in .env

Required env vars:
  AIRTABLE_API_KEY   — Personal Access Token from airtable.com/account
  AIRTABLE_BASE_ID   — e.g. appXXXXXXXXXXXXXX
  AIRTABLE_TABLE_NAME — e.g. "Clients"
"""

import os
import asyncio
from datetime import datetime

MOCK = os.getenv("MOCK_TOOLS", "true").lower() == "true"
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY", "").strip()
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "").strip()
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME", "Clients").strip()


async def create_airtable_record(payload: dict, upstream_results: dict) -> dict:
    """
    Creates a record in Airtable Clients table.
    Includes links to Drive folder and Notion page.
    """
    await asyncio.sleep(0.9)

    drive_url = upstream_results.get("drive", {}).get("folder_url", "")
    notion_url = upstream_results.get("notion", {}).get("page_url", "")

    fields = {
        "Client Name": payload["client_name"],
        "Email": payload["client_email"],
        "Service Plan": payload["service_plan"].capitalize(),
        "Start Date": payload["start_date"],
        "Account Manager": payload["account_manager"],
        "Status": "Onboarding",
        "Drive Folder": drive_url,
        "Notion Page": notion_url,
        "Notes": payload.get("notes", ""),
        "Onboarded At": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "Source": "Onboarding Agent (auto)",
    }

    if MOCK:
        mock_id = f"rec{''.join([str(ord(c)) for c in payload['client_name'][:3]])}"
        print(f"[MOCK AIRTABLE] Created record '{payload['client_name']}' → {mock_id}")
        return {
            "success": True,
            "mock": True,
            "record_id": mock_id,
            "fields": fields,
            "table": AIRTABLE_TABLE_NAME,
            "created_at": datetime.utcnow().isoformat(),
        }

    # ── Real Airtable implementation ──────────────────────────────────────────
    try:
        from pyairtable import Api
        api = Api(AIRTABLE_API_KEY)
        table = api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)
        record = table.create(fields)
        return {
            "success": True,
            "record_id": record["id"],
            "fields": record["fields"],
            "table": AIRTABLE_TABLE_NAME,
            "created_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
