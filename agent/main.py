"""
Scrollhouse Client Onboarding Agent — Entry Point
--------------------------------------------------
Starts a FastAPI webhook server that:
1. Receives POST /webhook/onboard with new client data
2. Runs LangGraph validation
3. Chains LangChain tools (email → drive → notion → airtable)
4. Logs everything with LangSmith

Run:  uvicorn agent.main:app --reload --port 8000
"""

import os
import time
import json
import asyncio
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, validator
from dotenv import load_dotenv

load_dotenv()

from agent.validator import run_validation
from agent.orchestrator import run_orchestrator
from agent.logger import AgentLogger
from agent.tools.llm_reply_tool import handle_inbound_email
from agent.tools.email_tool import send_alert_email
from agent.imap_listener import start_imap_listener
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the IMAP listener in the background right as the server boots!
    imap_task = asyncio.create_task(start_imap_listener())
    yield
    imap_task.cancel()

app = FastAPI(
    title="Scrollhouse Onboarding Agent",
    description="Automates full client onboarding: email, Drive, Notion, Airtable",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # lock down in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Serve Dashboard ───────────────────────────────────────────────────────────
# Native frontend hosting so the dashboard + backend run on a single cloud server.
app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="static")

logger = AgentLogger()


# ── Data Models ────────────────────────────────────────────────────────────────

class ClientPayload(BaseModel):
    client_name: str
    client_email: str
    service_plan: str   # starter | growth | enterprise
    start_date: str     # ISO date string YYYY-MM-DD
    account_manager: str = "Unassigned"
    notes: str = ""
    ignore_warnings: bool = False

    @validator("client_name")
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("client_name cannot be empty")
        return v.strip()

    @validator("service_plan")
    def valid_plan(cls, v):
        allowed = {"starter", "growth", "enterprise"}
        if v.lower() not in allowed:
            raise ValueError(f"service_plan must be one of {allowed}")
        return v.lower()

class InboundEmailPayload(BaseModel):
    sender_email: str
    subject: str
    text_body: str


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "agent": "Scrollhouse Onboarding Agent v1.0"}


@app.post("/webhook/onboard")
async def onboard_client(payload: ClientPayload, request: Request):
    """
    Main webhook endpoint.
    Called by n8n (or any HTTP client) when a new client signup is detected.
    """
    run_id = f"run_{int(time.time())}"
    start_ts = datetime.utcnow()

    logger.info(run_id, f"━━━ New onboarding request: {payload.client_name} ({payload.client_email}) ━━━")
    logger.info(run_id, f"Plan: {payload.service_plan} | Start: {payload.start_date} | AM: {payload.account_manager}")

    # ── STEP 1: Validate ────────────────────────────────────────────────────
    logger.info(run_id, "Running LangGraph validation graph...")
    validation_result = await run_validation(payload.dict(), run_id, logger)

    if not validation_result["is_valid"]:
        logger.error(run_id, f"Validation failed: {validation_result['errors']}")
        
        # Dispatch native alert email to the Account Manager
        logger.info(run_id, "Triggering Hard Error Email Alert dispatch...")
        await send_alert_email(payload.dict(), validation_result["errors"], run_id)

        # Return 422 to frontend
        return JSONResponse(
            status_code=422,
            content={
                "status": "validation_failed",
                "run_id": run_id,
                "errors": validation_result["errors"],
                "message": "Alert sent to account manager. Onboarding halted.",
            },
        )

    # ── Check for Edge Case Warnings ─────────────────────────────────────────
    if validation_result.get("warnings") and not payload.ignore_warnings:
        logger.warning(run_id, "Validation returned warnings. Pausing for human confirmation.")
        return JSONResponse(
            status_code=409,
            content={
                "status": "requires_confirmation",
                "run_id": run_id,
                "warnings": validation_result["warnings"],
                "message": "Warnings detected. Requires manager confirmation to proceed.",
            },
        )

    logger.success(run_id, "Validation passed ✓")

    # ── STEP 2–5: Run the tool chain ────────────────────────────────────────
    logger.info(run_id, "Starting LangChain orchestrator...")
    results = await run_orchestrator(payload.dict(), run_id, logger)

    elapsed = (datetime.utcnow() - start_ts).total_seconds()
    logger.success(run_id, f"All tools completed in {elapsed:.1f}s")
    logger.info(run_id, "Saving run to audit log...")

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "run_id": run_id,
            "elapsed_seconds": elapsed,
            "client": payload.client_name,
            "results": results,
        },
    )


@app.get("/logs")
async def get_logs():
    """Return the full audit log."""
    return {"logs": logger.get_all()}


@app.post("/webhook/inbound")
async def inbound_email(payload: InboundEmailPayload):
    """
    Auto-Reply webhook endpoint.
    Called by SendGrid Inbound Parse or n8n when a client replies to an email.
    """
    logger.info("inbound", f"Received reply from {payload.sender_email} -> Trigerring LLM Auto-Reply")
    
    result = await handle_inbound_email(payload.sender_email, payload.subject, payload.text_body)
    
    if result.get("success"):
        logger.success("inbound", f"Auto-Reply deployed to {payload.sender_email} ✓")
    else:
        logger.error("inbound", f"Auto-Reply failed: {result.get('error')}")
        
    return JSONResponse(status_code=200 if result.get("success") else 500, content=result)


@app.get("/")
async def root():
    return {
        "message": "Scrollhouse Onboarding Agent is running.",
        "docs": "/docs",
        "webhook": "POST /webhook/onboard",
        "inbound": "POST /webhook/inbound"
    }
