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

### Phase 3: The Orchestration Pipeline (70% Agentic ReAct)
5. **The Autonomous Loop**: The payload is passed to a LangChain ReAct loop powered natively by `Llama-3.3-70b-versatile` running via Groq. The agent is given explicit instructions to fully deploy the environment but is deliberately forced to figure out the operational API calls on its own! 
6. **Dynamic Tool Execution**: The agent evaluates its available `@tools`. It actively chooses to run the `Google Drive API` first. It captures the returned Folder URL. 
7. **Recursive Payload Passing**: The agent then reads the output of the Drive step and physically injects it as an argument into the `Notion API` tool to ensure the Notion database contains the new client's cloud storage linkage.
8. **Finalizing Infrastructure**: The agent triggers the `Airtable API` tool to cement the entire CRM row.
9. **Dispatching Email**: Finally, perceiving that the infrastructure tools succeeded, the LLM actively drafts highly personalized introduction copy using the client's signup notes, and automatically calls the `Email API` to fire the SendGrid email before self-terminating!

### Phase 4: Autonomous "Auto-Reply" (Background Listener)
10. **IMAP Polling**: Running quietly alongside the FastAPI server is a continuous background loop (`imap_listener.py`). Every 15 seconds, it queries the main Gmail inbox looking for incoming emails flagged as **UNREAD**.
11. **Intercept & Analyze**: If a client replies to our welcome email, the IMAP listener catches it. It passes the client's email body back to **Llama 3**, instructing the AI to act as an enthusiastic customer success agent.
12. **AI Reply deployed**: Llama 3 writes a polite response addressing their question. The system instantly emails this generated reply back to the client and marks the original message as "READ" in the inbox to prevent an infinite loop.
