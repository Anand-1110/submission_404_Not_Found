"""
Airtable Table Setup Script
----------------------------
Run this ONCE to create the Clients table with all required fields.

Usage:
    cd e:\\Agent
    python agent/setup_airtable.py

Requires AIRTABLE_API_KEY and AIRTABLE_BASE_ID in .env
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

AIRTABLE_API_KEY  = os.getenv("AIRTABLE_API_KEY", "")
AIRTABLE_BASE_ID  = os.getenv("AIRTABLE_BASE_ID", "")
AIRTABLE_TABLE    = os.getenv("AIRTABLE_TABLE_NAME", "Clients")


def main():
    if not AIRTABLE_API_KEY or "your_" in AIRTABLE_API_KEY:
        print("❌ AIRTABLE_API_KEY not set in .env")
        sys.exit(1)
    if not AIRTABLE_BASE_ID or AIRTABLE_BASE_ID.startswith("appXXX"):
        print("❌ AIRTABLE_BASE_ID not set in .env")
        sys.exit(1)

    try:
        from pyairtable import Api
        from pyairtable.models.schema import (
            SingleLineTextFieldConfig, EmailFieldConfig,
            SingleSelectFieldConfig, DateFieldConfig, UrlFieldConfig
        )
    except ImportError:
        print("❌ pyairtable not installed — run: pip install pyairtable")
        sys.exit(1)

    api = Api(AIRTABLE_API_KEY)

    # Check if table already exists
    try:
        tbl = api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE)
        records = tbl.all(max_records=1)
        print(f"✅ Table '{AIRTABLE_TABLE}' already exists in base {AIRTABLE_BASE_ID}")
        print(f"   Found {len(records)} existing records — ready to use!")
        return
    except Exception:
        pass  # Table doesn't exist yet, create it

    print(f"Creating table '{AIRTABLE_TABLE}' in base {AIRTABLE_BASE_ID}...")

    # Airtable's API requires creating fields via the Meta API
    # The simplest approach: just tell user what columns to add
    print("\n" + "═" * 60)
    print("  ⚠️  Airtable Meta API requires a different token scope.")
    print("  Please create the table MANUALLY with these columns:")
    print("═" * 60)

    columns = [
        ("Client Name",    "Single line text"),
        ("Email",          "Email"),
        ("Service Plan",   "Single select  → options: Starter, Growth, Enterprise"),
        ("Start Date",     "Date"),
        ("Account Manager","Single line text"),
        ("Status",         "Single select  → options: Onboarding, Active, Churned"),
        ("Drive Folder",   "URL"),
        ("Notion Page",    "URL"),
        ("Notes",          "Long text"),
        ("Onboarded At",   "Date (include time)"),
        ("Source",         "Single line text"),
    ]

    for name, field_type in columns:
        print(f"  • {name:<22} — {field_type}")

    print("\n  After creating the table, run:")
    print("  python agent/test_credentials.py\n")


if __name__ == "__main__":
    main()
