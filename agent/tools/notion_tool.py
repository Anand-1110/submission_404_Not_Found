"""
Notion Tool — creates client page from a master template
---------------------------------------------------------
Real implementation: pip install notion-client
Mock mode: set MOCK_TOOLS=true in .env

Required env vars:
  NOTION_API_KEY        — from notion.so/my-integrations
  NOTION_PARENT_PAGE_ID — the page ID under which client pages live
  NOTION_TEMPLATE_ID    — optional: ID of template page to duplicate
"""

import os
import asyncio
from datetime import datetime

MOCK = os.getenv("MOCK_TOOLS", "true").lower() == "true"
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "").strip()
NOTION_PARENT_PAGE_ID = os.getenv("NOTION_PARENT_PAGE_ID", "").strip()


def _build_notion_page(payload: dict) -> dict:
    """Build Notion API page body with rich content blocks."""
    return {
        "parent": {"page_id": NOTION_PARENT_PAGE_ID},
        "icon": {"emoji": "🏢"},
        "cover": {"external": {"url": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1200"}},
        "properties": {
            "title": {
                "title": [{"text": {"content": f"Client: {payload['client_name']}"}}]
            }
        },
        "children": [
            {
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"text": {"content": f"✅ Auto-created by Scrollhouse Onboarding Agent on {datetime.utcnow().strftime('%Y-%m-%d')}"}}],
                    "icon": {"emoji": "🤖"},
                    "color": "green_background",
                },
            },
            {
                "object": "block",
                "type": "heading_1",
                "heading_1": {"rich_text": [{"text": {"content": payload["client_name"]}}]},
            },
            {
                "object": "block",
                "type": "table_of_contents",
                "table_of_contents": {"color": "default"},
            },
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"text": {"content": "Client Details"}}]},
            },
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"text": {"content": f"📧 Email: {payload['client_email']}"}}]},
            },
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"text": {"content": f"📦 Plan: {payload['service_plan'].capitalize()}"}}]},
            },
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"text": {"content": f"📅 Start Date: {payload['start_date']}"}}]},
            },
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"text": {"content": f"👤 Account Manager: {payload['account_manager']}"}}]},
            },
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"text": {"content": "Onboarding Checklist"}}]},
            },
            {"object": "block", "type": "to_do", "to_do": {"rich_text": [{"text": {"content": "Kickoff call scheduled"}}], "checked": False}},
            {"object": "block", "type": "to_do", "to_do": {"rich_text": [{"text": {"content": "Contract signed"}}], "checked": False}},
            {"object": "block", "type": "to_do", "to_do": {"rich_text": [{"text": {"content": "Drive folder shared with client"}}], "checked": True}},
            {"object": "block", "type": "to_do", "to_do": {"rich_text": [{"text": {"content": "Welcome email sent"}}], "checked": True}},
            {"object": "block", "type": "to_do", "to_do": {"rich_text": [{"text": {"content": "Initial strategy session"}}], "checked": False}},
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"text": {"content": "Notes"}}]},
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "text": {"content": payload.get("notes") or "No additional notes provided."}
                    }]
                },
            },
        ],
    }


async def create_notion_page(payload: dict) -> dict:
    """Create a new Notion page for the client."""
    await asyncio.sleep(1.0)

    if MOCK:
        mock_id = f"mock_notion_{payload['client_name'].lower().replace(' ', '-')}"
        mock_url = f"https://notion.so/{mock_id}"
        print(f"[MOCK NOTION] Created page '{payload['client_name']}' → {mock_url}")
        return {
            "success": True,
            "mock": True,
            "page_id": mock_id,
            "page_url": mock_url,
            "created_at": datetime.utcnow().isoformat(),
        }

    # ── Real Notion implementation ────────────────────────────────────────────
    try:
        from notion_client import Client
        notion = Client(auth=NOTION_API_KEY)
        
        # ── Start Page Shell ──────────────────────────────────
        page_body = {
            "parent": {"page_id": NOTION_PARENT_PAGE_ID},
            "icon": {"emoji": "🏢"},
            "properties": {
                "title": {
                    "title": [{"text": {"content": f"Client: {payload['client_name']}"}}]
                }
            }
        }

        # ── Pull Live Template Blocks ──────────────────────────
        template_id = os.getenv("NOTION_TEMPLATE_ID")
        if template_id:
            blocks_response = notion.blocks.children.list(block_id=template_id)
            raw_blocks = blocks_response.get("results", [])
            
            clean_blocks = []
            for b in raw_blocks:
                b_type = b.get("type")
                if not b_type or b_type == "unsupported":
                    continue
                # Strip out metadata like id, created_time, parent, etc.
                clean_b = {"object": "block", "type": b_type, b_type: b[b_type]}
                clean_blocks.append(clean_b)
                
            page_body["children"] = clean_blocks
        else:
            # Fallback to the hardcoded dictionary if no template ID is defined
            page_body = _build_notion_page(payload)

        # ── Execute ───────────────────────────────────────────
        response = notion.pages.create(**page_body)
        page_id = response["id"]
        page_url = response.get("url", f"https://notion.so/{page_id.replace('-','')}")
        return {
            "success": True,
            "page_id": page_id,
            "page_url": page_url,
            "created_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        err_msg = str(e)
        print(f"[ERROR] Notion failed for parent '{NOTION_PARENT_PAGE_ID}': {err_msg}")
        return {
            "success": False, 
            "error": err_msg,
            "manual_override_required": f"Please ensure your Notion Integration is added to the parent page '{NOTION_PARENT_PAGE_ID}'."
        }
