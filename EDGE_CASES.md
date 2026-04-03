# 🛡️ Edge Cases Document

This document outlines exactly how the Scrollhouse AI Onboarding Agent handles complex, unexpected scenarios while running live.

---

## 1. The Welcome Email Bounces
**What the platform does:**  
When the HTTP webhook is triggered, the system's Orchestrator attempts to dispatch the welcome email first. If the SMTP server immediately rejects the client's email address (e.g. typos like `user@gmailll.com`), the `email_tool` throws an exception. The Orchestrator safely catches this exception and **halts the entire pipeline** instantly. It prevents the system from wasting time building Google Drive folders and Notion pages for a dead account, and logs the explicit bounce error to the terminal.

## 2. You Graphically Update the Notion Master Template
**What the platform does:**  
Instead of creating brand new project boards based on an old, hard-coded Python dictionary copy, the `notion_tool` explicitly queries the Notion API to recursively fetch all children blocks from the live `NOTION_TEMPLATE_ID`. This guarantees that if a human manager adds a new checkbox or image to the master Notion template, the very next automated onboarding will 100% reflect that new change accurately without requiring a code deployment.

## 3. Duplicate Brand Name Form Submission
**What the platform does:**  
If an Account Manager tries to onboard "Acme Corp", the LangGraph AI Validator `node_check_duplicate` searches the live Airtable database in real-time. If it detects that a `Client Name` of "Acme Corp" already exists, it does *not* fatally crash the server. Instead, it flags the request with a **"Requires Manager Confirmation"** warning. This allows the system to pause, holding the data safely until a manager verifies that this is a separate branch/contract for the same brand, rather than an accidental double-entry.

## 4. Contract Start Date is Accidentally in the Past
**What the platform does:**  
If a manager mis-clicks and sets the onboarding start date to yesterday's date, the `node_check_date` validator catches the chronological paradox. Instead of throwing a lethal HTTP processing crash, it gracefully tags the payload with a **Warning Status**.

## 5. Unrecognized Account Manager Name
**What the platform does:**  
When the form is submitted, the `node_check_am` state function verifies the inputted Account Manager name against a pre-coded list of strict `VALID_MANAGERS`. If an unknown manager name is typed (e.g. a typo, or a new employee not yet in the system), the validator flags the mismatch internally. It ensures we don't pollute the CRM database with untrackable "ghost" manager assignments without alerting a supervisor.

## 6. Google Drive API Connection Drops or Rate Limits
**What the platform does:**  
If Google's servers momentarily glitch while we are trying to create the 5 nested client folders, the system will not crash. `drive_tool` executes a strict `max_retries = 2` safety loop. 
- If attempt 1 fails, the script will `asyncio.sleep(2)` seconds.
- It will then try softly connecting again.
- If it violently fails after 3 consecutive attempts, it elegantly returns a `manual_override_required` JSON payload to the Orchestrator. This payload instructs the human manager on exactly how to create the folder manually and who to share it with, ensuring the client still gets onboarded eventually.
