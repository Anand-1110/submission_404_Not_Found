# 🚀 Scrollhouse Client Onboarding AI Agent

## 📖 Project Overview
This project is a **Fully Autonomous AI Agent** designed to automate the complete client onboarding pipeline for a digital agency called Scrollhouse. It seamlessly integrates a frontend web form with a Python-based backend that orchestrates data validation, cloud storage provisioning, workspace generation, CRM logging, and intelligent email communications.

---

## 🛠️ Technology Stack Used

### **Core Languages & Frameworks**
- **Python**: The backbone of the entire backend logic and agent orchestration.
- **FastAPI**: Used to quickly spin up webhook endpoints (`/webhook/onboard` and `/webhook/inbound`) to listen for frontend data and background events.
- **JavaScript/HTML/CSS**: Powers the frontend dashboard interface where account managers trigger the agent.

### **AI & Logic Libraries**
- **LangChain**: Used as the AI orchestration framework to process prompts and communicate with the LLM API.
- **LangGraph**: Used to construct a stateful validation node-graph. It enforces strict rules (like checking for duplicate accounts) before allowing the onboarding tools to execute.
- **Groq (LPU AI Engine)**: The incredibly fast AI inference engine used to power the text generation.
- **Llama-3.3-70b-versatile**: Meta's flagship open-source LLM, working via Groq to write personalized email copy and process inbound auto-replies.

### **Third-Party API Integrations**
- **Gmail SMTP & IMAP**: Used to send programmatic emails out and read inbound emails in the background.
- **Google Drive API** (via Service Accounts): Used to automatically generate project folders and manipulate file permissions.
- **Notion API**: Used to programmatically duplicate project management templates into new client boards.
- **Airtable API**: Used to permanently store the onboarding records as a dynamic CRM database.

---

## ⚙️ The Complete Workflow Step-by-Step

### Phase 1: Initiation
1. **The Dashboard Form**: An Account Manager fills out the client's details (Name, Email, Service Plan, and custom Notes) on the frontend dashboard.
2. **Webhook Trigger**: Hitting "Run Demo" posts this JSON payload to the FastAPI backend at `http://localhost:8000/webhook/onboard`.

### Phase 2: AI Validation (LangGraph)
3. **Duplicate Checking**: Before any folders or emails are sent, the system enters the `node_check_duplicate` state. It secretly queries the live **Airtable** database to see if the client's exact email address already exists.
4. **Pass/Fail**: If a duplicate is found, the onboarding halts immediately, throwing an error on the dashboard to prevent spamming the client. If clean, it proceeds.

### Phase 3: The Orchestration Pipeline
5. **AI Welcome Email**: The agent passes the client's custom "Notes" to the **Llama 3 AI**. The AI drafts a highly personalized introductory email acknowledging the client's specific business goals. The backend then injects this AI copy into an HTML template and sends it via **Gmail**.
6. **Workspace Generation**: The backend reaches out to the **Google Drive API** to create a fresh folder specifically named for the client, generating a secure sharing link.
7. **Task Management**: The system calls the **Notion API** to create a brand new client portal page cloned from a standard agency template.
8. **CRM Logging**: Finally, the system logs the client's Name, Email, and links to both the Drive folder and Notion page squarely into **Airtable**.
9. **Final Summary**: The system sends a concluding "Onboarding Summary" email to the Account Manager, alerting them that everything was successfully provisioned.

### Phase 4: Autonomous "Auto-Reply" (Background Listener)
10. **IMAP Polling**: Running quietly alongside the FastAPI server is a continuous background loop (`imap_listener.py`). Every 15 seconds, it queries the main Gmail inbox looking for incoming emails flagged as **UNREAD**.
11. **Intercept & Analyze**: If a client replies to our welcome email, the IMAP listener catches it. It passes the client's email body back to **Llama 3**, instructing the AI to act as an enthusiastic customer success agent.
12. **AI Reply deployed**: Llama 3 writes a polite response addressing their question. The system instantly emails this generated reply back to the client and marks the original message as "READ" in the inbox to prevent an infinite loop.
