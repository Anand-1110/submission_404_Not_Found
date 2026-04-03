# Scrollhouse — Client Onboarding Automation Agent

> **Hackathon-ready** full-stack automation agent that handles your entire client onboarding in < 60 seconds — zero manual work.

---

## What it does

When a new client is added, the agent automatically:

| Step | Tool | Action |
|------|------|--------|
| 1 | **n8n** | Receives webhook trigger from your signup form |
| 2 | **LangGraph** | Validates email, checks duplicates, verifies date |
| 3 | **LangChain → Email** | Sends personalised welcome email via SendGrid |
| 4 | **LangChain → Drive** | Creates `[Client] Name/` folder + 5 subfolders + shares |
| 5 | **LangChain → Notion** | Creates client page from master template |
| 6 | **LangChain → Airtable** | Creates CRM record with Drive + Notion links |
| 7 | **Email** | Sends completion summary to account manager |
| 8 | **LangSmith** | Saves full audit log to `logs/audit.jsonl` |

---

## Project Structure

```
Agent/
├── dashboard/           # ✨ Beautiful live-status web UI
│   ├── index.html
│   ├── style.css
│   └── app.js
├── agent/               # 🐍 Python FastAPI + LangChain/LangGraph backend
│   ├── main.py          # Webhook server (uvicorn)
│   ├── validator.py     # LangGraph validation state machine
│   ├── orchestrator.py  # LangChain tool runner
│   ├── logger.py        # Audit log (JSONL)
│   └── tools/
│       ├── email_tool.py
│       ├── drive_tool.py
│       ├── notion_tool.py
│       └── airtable_tool.py
├── n8n/
│   └── workflow.json    # Importable n8n workflow
├── .env.example         # API key template
├── requirements.txt
└── README.md
```

---

## Quick Start

### 1. Open the Dashboard (no setup needed)

Just open `dashboard/index.html` in your browser. Click **▶ Run Demo** to watch the full pipeline animate live.

### 2. Run the Python Agent (optional — for real integrations)

```powershell
# Install dependencies
pip install -r requirements.txt

# Copy env template and fill in your API keys
copy .env.example .env
notepad .env

# Start the webhook server
uvicorn agent.main:app --reload --port 8000
```

### 3. Import the n8n Workflow

1. Install n8n: `npx -y n8n`
2. Open `http://localhost:5678`
3. Click **Import** → select `n8n/workflow.json`
4. Activate the workflow

---

## API Keys You Need

| Service | Where to get it |
|---------|-----------------|
| **SendGrid** | [sendgrid.com](https://sendgrid.com) → Settings → API Keys |
| **Google Drive** | [console.cloud.google.com](https://console.cloud.google.com) → Service Account JSON |
| **Notion** | [notion.so/my-integrations](https://notion.so/my-integrations) |
| **Airtable** | [airtable.com/account](https://airtable.com/account) → Personal Access Token |
| **OpenAI** (optional) | [platform.openai.com](https://platform.openai.com) |
| **LangSmith** (optional) | [smith.langchain.com](https://smith.langchain.com) |

---

## Mock Mode (default)

Set `MOCK_TOOLS=true` in `.env` (already the default). The agent will simulate all API calls — perfect for demos and testing without real credentials.

---

## Testing the Webhook

```powershell
# Test happy path
Invoke-WebRequest -Uri http://localhost:8000/webhook/onboard `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"client_name":"Nova Digital","client_email":"ceo@novadigital.io","service_plan":"growth","start_date":"2026-05-01","account_manager":"Sarah J."}'

# Test validation error (duplicate client)
Invoke-WebRequest -Uri http://localhost:8000/webhook/onboard `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"client_name":"Acme Corp","client_email":"contact@acme.com","service_plan":"starter","start_date":"2026-05-01"}'
```

---

## Hackathon Demo Script

1. Open `dashboard/index.html`
2. Fill in a new client form → hit "Trigger Onboarding Agent"
3. Watch all 8 pipeline steps light up in real time
4. Show the result card with Drive / Notion / Airtable links
5. Try a duplicate name (e.g. "Acme Corp") → see error branch activate

**That's your full demo: signup → automated → 60 seconds.**

---

## Tech Stack

- **n8n** — workflow orchestration & webhook
- **FastAPI + uvicorn** — Python webhook server
- **LangGraph** — validation state machine with branching
- **LangChain** — sequential tool runner
- **LangSmith** — observability & audit logging
- **SendGrid** — transactional email
- **Google Drive API** — folder creation
- **Notion API** — page creation
- **Airtable API** — CRM records
