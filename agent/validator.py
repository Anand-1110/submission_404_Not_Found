"""
LangGraph Validation Graph
---------------------------
Uses a state machine (graph) to validate incoming client data before
any tools are executed.

Nodes
  parse_input   → normalise & type-check all fields
  check_email   → validate email format
  check_dupe    → look for existing client with same name in Airtable
  check_date    → ensure start_date is not in the past
  route         → branching node: valid path vs alert-manager path

Edges
  parse_input → check_email → check_dupe → check_date → route
  route → [valid | invalid]
"""

import re
import asyncio
from datetime import date
from typing import TypedDict, Annotated
import operator

# If you have langgraph installed: from langgraph.graph import StateGraph, END
# For the demo/hackathon we provide a lightweight inline version so the
# project works without GPU / heavy deps.

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")

# ── Shared State ───────────────────────────────────────────────────────────────

class ValidationState(TypedDict):
    payload: dict
    errors: Annotated[list, operator.add]   # errors accumulate
    warnings: Annotated[list, operator.add] # warnings accumulate for manager review
    run_id: str
    logger: object


# ── Nodes ──────────────────────────────────────────────────────────────────────

async def node_parse_input(state: ValidationState) -> ValidationState:
    """Normalise payload values."""
    p = state["payload"]
    p["client_name"] = p.get("client_name", "").strip()
    p["client_email"] = p.get("client_email", "").strip().lower()
    p["service_plan"] = p.get("service_plan", "").strip().lower()
    return state


async def node_check_email(state: ValidationState) -> ValidationState:
    """Validate email format."""
    email = state["payload"]["client_email"]
    if not EMAIL_RE.match(email):
        state["errors"] = state["errors"] + [f"Invalid email address: '{email}'"]
        state["logger"].warning(state["run_id"], f"Email check FAILED: {email}")
    else:
        state["logger"].info(state["run_id"], f"Email check passed: {email}")
    return state


async def node_check_duplicate(state: ValidationState) -> ValidationState:
    """
    Check for duplicate client emails by querying Airtable directly.
    Multiple clients can have the same name, but emails must be unique.
    """
    import os
    email = state["payload"]["client_email"]
    email_lower = email.lower()

    # Keep a few demo "fake" emails for presentation purposes
    EXISTING_EMAILS = ["test@acme.com", "contact@globex.com", "ceo@initech.com"]  
    if email_lower in EXISTING_EMAILS:
        state["errors"] = state["errors"] + [f"Duplicate client email (Demo Mode): '{email}'"]
        state["logger"].warning(state["run_id"], f"Duplicate check FAILED: {email_lower}")
        return state

    key = os.getenv("AIRTABLE_API_KEY", "")
    base_id = os.getenv("AIRTABLE_BASE_ID", "")
    table_name = os.getenv("AIRTABLE_TABLE_NAME", "Clients")
    mock_mode = os.getenv("MOCK_TOOLS", "true").lower() == "true"

    if mock_mode or not key:
        state["logger"].info(state["run_id"], f"Duplicate check passed (Mock): {email}")
        return state

    # ── Real Airtable Check ────────────────────────────────────────────────
    try:
        from pyairtable import Api
        from pyairtable.formulas import match
        api = Api(key)
        table = api.table(base_id, table_name)
        
        # Search for exact email match in Airtable "Email" column
        records = table.all(formula=match({"Email": email}), max_records=1)
        
        if len(records) > 0:
            state["errors"] = state["errors"] + [f"Email already exists in CRM: '{email}'"]
            state["logger"].warning(state["run_id"], f"Duplicate check FAILED (Airtable): {email}")
        else:
            state["logger"].info(state["run_id"], f"Duplicate format passed (Airtable): {email}")
            
        # Check brand name duplicate for warning
        client_name = state["payload"]["client_name"]
        name_records = table.all(formula=match({"Client Name": client_name}), max_records=1)
        if len(name_records) > 0:
            msg = f"Brand name '{client_name}' already exists. Requires manager confirmation."
            state["warnings"] = state["warnings"] + [msg]
            state["logger"].warning(state["run_id"], msg)
            
    except Exception as e:
        # If API fails, warn but allow onboarding to proceed to avoid breaking the core flow
        state["logger"].warning(state["run_id"], f"Airtable duplicate check error: {e}")

    return state


async def node_check_date(state: ValidationState) -> ValidationState:
    """Ensure start_date is not in the past."""
    try:
        start = date.fromisoformat(state["payload"]["start_date"])
        if start < date.today():
            msg = f"start_date '{state['payload']['start_date']}' is in the past. Requires confirmation."
            state["warnings"] = state["warnings"] + [msg]
            state["logger"].warning(state["run_id"], msg)
        else:
            state["logger"].info(state["run_id"], f"Date check passed: {start}")
    except ValueError:
        state["errors"] = state["errors"] + [
            f"start_date '{state['payload']['start_date']}' is not a valid ISO date (YYYY-MM-DD)"
        ]
    return state


async def node_check_am(state: ValidationState) -> ValidationState:
    """Check if the account manager name is in the valid list."""
    import os
    manager = state["payload"].get("account_manager", "").strip()
    valid_ams = [m.strip().lower() for m in os.getenv("VALID_MANAGERS", "Ashish,Adarsh,Anand").split(",")]
    
    if manager.lower() not in valid_ams:
        msg = f"Unknown account manager '{manager}'. Requires confirmation."
        state["warnings"] = state["warnings"] + [msg]
        state["logger"].warning(state["run_id"], msg)
    else:
        state["logger"].info(state["run_id"], f"Account Manager check passed: {manager}")
        
    return state


# ── Router ─────────────────────────────────────────────────────────────────────

def route_decision(state: ValidationState) -> str:
    """Branching function — route to 'valid' or 'invalid'."""
    return "invalid" if state["errors"] else "valid"


# ── Graph Runner ───────────────────────────────────────────────────────────────

async def run_validation(payload: dict, run_id: str, logger) -> dict:
    """
    Execute the validation graph and return a result dict.
    Returns: { "is_valid": bool, "errors": list[str] }

    With real LangGraph installed this would be:
        graph = StateGraph(ValidationState)
        graph.add_node("parse", node_parse_input)
        ...
        graph.compile().invoke(initial_state)
    """
    state: ValidationState = {
        "payload": payload,
        "errors": [],
        "warnings": [],
        "run_id": run_id,
        "logger": logger,
    }

    # Sequential execution (mirrors the graph edges)
    state = await node_parse_input(state)
    state = await node_check_email(state)
    state = await node_check_duplicate(state)
    state = await node_check_date(state)
    state = await node_check_am(state)

    decision = route_decision(state)

    return {
        "is_valid": decision == "valid",
        "errors": state["errors"],
        "warnings": state["warnings"],
        "payload": state["payload"],   # normalised payload for the tools
    }
