# Submission Summary

## Team

**Team Name:** 404_Not_Found  
**Members:**  
Anand | Lead Developer / AI Architect  
(Fill in other members here) | (Role)  
**Contact Email:** (Your Email Here)  

---

## Problem Statement

**Selected Problem:** PS-01  
**Problem Title:** Client Onboarding  

Currently, onboarding a B2B client requires five manual, disconnected administrative tasks (CRM data-entry, Drive folder creation, Notion project setup, and mailing) taking up critical hours and risking human transposition errors. Our system integrates all of these steps into a 3-second automated workflow triggered by a single webhook, saving Account Managers countless hours while dynamically generating intensely personalized client communications using an integrated LLM.

---

## System Overview

When a new client submits an onboarding form, our backend instantly intercepts the webhook data. It algorithmically validates the input for duplicate records or incorrect dates, pausing dynamically to ask the manager for confirmation if anything looks suspicious. Once strictly validated, the system automatically writes a highly personalized welcome email using AI, provisions a nested Google Drive folder structure, duplicates a live Notion project page, saves the client’s data perfectly into Airtable, and delivers a final automated summary report back to the Account Manager.

---

## Tools and Technologies

List every tool, library, framework, API, and model your system uses. For each one, state what it does in your system, not just what it is.

| Tool or Technology | Version or Provider | What It Does in Your System |
|---|---|---|
| FastAPI & Uvicorn | Python 3.x | Backend web framework that receives the initial webhook and mounts the UI. |
| LangGraph | LangChain | Orchestration framework that deterministically validates the incoming payload data against strict business rules before allowing tools to trigger. |
| Llama-3.3-70b-versatile | Groq LPU API | Large Language Model used to write deeply personalized introduction paragraphs based on client signup notes, and drafts background auto-replies. |
| Google Drive API | Google Cloud | Cloud Storage connector that magically generates a recurring nested folder hierarchy (e.g. Invoices, Assets) explicitly assigned to the client. |
| Notion API | Notion Client | Workspace module that dynamically reads the live blocks of a master template page and replicates them perfectly into a brand new isolated client board. |
| PyAirtable | Airtable API | CRM Database connector that scans for duplicate companies and inserts the final verified client record into the CRM table. |
| Vanilla JS & HTML | Native Web | The interactive interactive dashboard frontend that connects to the FastAPI backend and visually displays the AI pipeline. |

---

## LLM Usage

**Model(s) used:** Llama-3.3-70b-versatile  
**Provider(s):** Groq  
**Access method:** API key  

List every place in your system where an LLM is called. For each call, describe what the LLM receives as input, what decision or output it produces, and how that output affects the next step.

| Step | LLM Input | LLM Output | Effect on System |
|---|---|---|---|
| Step 1: Welcome Email Personalization | The Client's distinct Name, Service Plan tier, and any Custom Form Notes (e.g., industry details). | A perfectly formulated, professional 2-paragraph HTML string acknowledging their specific industry/notes. | The output is seamlessly injected into the templated SendGrid HTML structure before the email physically triggers. |
| Background Service: Auto-Replies | The raw incoming body text and subject line of unread emails pulled from the company Gmail inbox via IMAP. | A contextual, polite, and responsive text body answering the client's direct question. | The response text is sent back to the client natively via SMTP without human intervention. |

---

## Algorithms and Logic

Our backend is anchored entirely by a LangGraph State Machine that enforces strict deterministic routing. We utilize algorithmic edge-case validation checks (`node_check_date`, `node_check_duplicate`) which use the Python Datetime library and exact PyAirtable formula queries (via `match()`) to ensure absolute data validity.

If a soft error is algorithmically triggered (e.g. an unknown manager name is typed), the system injects a `warning` array into the JSON response. Instead of crashing, the `agent.main.py` router intercepts the output and throws an HTTP 409 Conflict. This triggers a native Javascript modal in the frontend dashboard, forcing the Account Manager to explicitly input a manual override `ignore_warnings: true` boolean before the orchestrator is legally allowed to touch the Google Drive or Notion APIs. 

If the Google Drive API drops a packet, we use a custom `max_retries = 2` algorithmic iterative sleep loop (`asyncio.sleep(2)`) to force the pipeline to reconnect and heal itself.

---

## Deterministic vs Agentic Breakdown

This section is verified. Do not overstate the agentic percentage. Judges have access to your code and will check.

**Estimated breakdown:**

| Layer | Percentage | Description |
|---|---|---|
| Deterministic automation | 85% | What always happens the same way regardless of LLM output (Langgraph validation sequence, Google Drive folder creation, Airtable queries, Notion Block migrations). |
| LLM-driven and agentic | 15% | What the LLM decides, routes, interprets, or generates in a way that affects system behavior (Processing raw client notes into personalized email copy, analyzing unread emails for auto-reply dispatching). |

**Total must equal 100%.**

We purposefully isolated the LLM to the 15% communication strata. B2B infrastructure requires absolute reliability; if we allowed an LLM to control the 85% orchestration logic directly (via a ReAct agent), it could hallucinate parameters and permanently overwrite massive Notion or Google Drive hierarchies. By isolating the AI to copywriting, we retain 100% database safety.

---

## Edge Cases Handled

List the edge cases from your problem statement that your system handles, and briefly describe the handling logic for each.

| Edge Case | How Your System Handles It |
|---|---|
| Email Bounces | SMTP connection errors are caught in an explicit `try/except` chain in the email tool, causing the Orchestrator to throw a Hard Error and abort the pipeline natively before it wastes time building Cloud Folders. |
| Updated Notion Template | The Notion tool does NOT use a hardcoded python dictionary. It uses `blocks.children.list(TEMPLATE)` to dynamically scrub the Notion database and pull live children blocks every time. |
| Duplicate Brand Name | We query the `Client Name` Airtable column using `match()`. If found, a soft warning is flagged causing the UI to pause and throw a manual override confirmation block. |
| Contract Start in Past | Evaluated deterministically against `date.today()`. Soft warning triggers the JS manual override modal. |
| Unrecognised AM | Safely evaluated against the `VALID_MANAGERS` list in the `.env` file. Soft warning triggers the JS manual override prompt. |
| Drive API Failure | Wrapped in an explicit `max_retries=2` recursive/iterative loop to heal momentary Google latency issues. If 3 consecutive failures hit, a manual instructions payload is returned. |

---

## Repository

**GitHub Repository Link:** (Paste your GitHub Link here before submitting)  
**Branch submitted:** main  
**Commit timestamp of final submission:** (Paste your commit hash here e.g. 8f4b3c2 - 2026-04-03 14:00:00 UTC)  

---

## Deployment

**Is your system deployed?** Yes  

**Deployment link:** (Paste your Render Link here, e.g., https://your-agent.onrender.com/dashboard)  
**Platform used:** Render.com  
**What can be tested at the link:** The entire interactive UI dashboard is hosted. You can submit the form to trigger the complete backend pipeline live.  

---

## Known Limitations

1. **Auto-responder loop**: The IMAP auto-responder currently replies to all unread emails without advanced threading rules limiters. If a client has an automated out-of-office autoreply on, it might cause a brief bot-to-bot chat loop. 
2. **Single-Tenant Notion Tokens**: The system uses a single master Notion integration token. It does not utilize full OAuth user-switching, meaning all Notion pages are technically generated by the identical master system bot rather than the specific junior Account Manager launching the webhook.

---

## Anything Else

To ensure our managers are never kept in the dark if a catastrophic failure occurs, we implemented an automated "Red Alert" system. If a junior employee intentionally attempts to force an invalid webhook configuration (like a duplicate email) through the system, the Langgraph engine will halt, construct an HTML crash report, and actively email the Senior Manager an urgent warning via SMTP before killing the server!
