"""
LangChain Orchestrator
-----------------------
Chains the 4 integration tools in order.
Each tool is a function decorated with @tool (LangChain pattern).
The orchestrator runs them sequentially and collects results.

Tool order:
  1. email_tool   — send welcome email
  2. drive_tool   — create Google Drive folder
  3. notion_tool  — create Notion page from template
  4. airtable_tool — create Airtable CRM record

In a real production setup you would use:
    from langchain.agents import AgentExecutor, create_openai_tools_agent
    from langchain_core.tools import tool
and let the LLM decide tool order based on the plan.
For deterministic onboarding we chain them directly.
"""

import asyncio
from agent.tools.email_tool import send_welcome_email
from agent.tools.drive_tool import create_drive_folder
from agent.tools.notion_tool import create_notion_page
from agent.tools.airtable_tool import create_airtable_record
from agent.tools.email_tool import send_completion_summary


async def run_orchestrator(payload: dict, run_id: str, logger) -> dict:
    """
    Run all onboarding tools in sequence.
    Returns a dict with all created resource URLs/IDs.
    """
    results = {}

    # ── Tool 1: Welcome Email ────────────────────────────────────────────────
    logger.info(run_id, "Tool 1/4 → Sending welcome email...")
    email_result = await send_welcome_email(payload)
    results["email"] = email_result
    if email_result.get("success"):
        logger.success(run_id, f"Email sent to {payload['client_email']} ✓")
    else:
        logger.error(run_id, f"Email tool failed: {email_result.get('error')}")
        logger.error(run_id, "Halting orchestrator - email bounce/rejection detected!")
        # Abort the pipeline immediately
        return results

    # ── Tool 2: Google Drive ─────────────────────────────────────────────────
    logger.info(run_id, "Tool 2/4 → Creating Google Drive folder...")
    drive_result = await create_drive_folder(payload)
    results["drive"] = drive_result
    if drive_result.get("success"):
        logger.success(run_id, f"Drive folder created: {drive_result.get('folder_url')} ✓")
    else:
        logger.error(run_id, f"Drive tool failed: {drive_result.get('error')}")

    # ── Tool 3: Notion ───────────────────────────────────────────────────────
    logger.info(run_id, "Tool 3/4 → Creating Notion page from template...")
    notion_result = await create_notion_page(payload)
    results["notion"] = notion_result
    if notion_result.get("success"):
        logger.success(run_id, f"Notion page created: {notion_result.get('page_url')} ✓")
    else:
        logger.error(run_id, f"Notion tool failed: {notion_result.get('error')}")

    # ── Tool 4: Airtable ─────────────────────────────────────────────────────
    logger.info(run_id, "Tool 4/4 → Creating Airtable CRM record...")
    airtable_result = await create_airtable_record(payload, results)
    results["airtable"] = airtable_result
    if airtable_result.get("success"):
        logger.success(run_id, f"Airtable record created: {airtable_result.get('record_id')} ✓")
    else:
        logger.error(run_id, f"Airtable tool failed: {airtable_result.get('error')}")

    # ── Completion Summary ───────────────────────────────────────────────────
    logger.info(run_id, "Sending completion summary to account manager...")
    summary_result = await send_completion_summary(payload, results, run_id)
    results["summary"] = summary_result
    if summary_result.get("success"):
        logger.success(run_id, "Completion summary sent ✓")

    return results
