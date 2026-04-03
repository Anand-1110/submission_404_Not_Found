# 🎯 Panel Defense & Interview Questions
Here are well-crafted, comprehensive answers concerning the Scrollhouse Agent's architecture, specifically prepared for your presentation/panel defense.

---

## On your API and model setup

**1. What model are you using and why did you choose it over alternatives available to you today?**
We are using `llama-3.3-70b-versatile` hosted via Groq. We chose it because Groq’s LPU architecture provides near-instantaneous inference speeds (crucial for real-time background auto-replies). Furthermore, the large 70B parameter Meta Llama model guarantees the high-quality, nuanced reasoning needed to act as an autonomous customer success agent. It is exceptionally fast and cost-effective compared to OpenAI’s GPT-4o, while performing similarly on text generation.

**2. What is the rate limit on the API you are calling most frequently, and how does your system behave when it hits that limit?**
The most frequent external API calls are to Groq (LLM) and Airtable (CRM). Groq enforces TPM (Tokens Per Minute) and RPM (Requests Per Minute) limits. In our architecture, the `ChatOpenAI` wrapper from LangChain has built-in automatic retries with exponential backoff. If it ultimately fails (returns a 429 Too Many Requests), our code catches the exception securely, writes the error into our `audit.jsonl` system log, and fails gracefully without crashing the FastAPI server.

**3. If your API key stops working mid-demo, what happens to the rest of the pipeline?**
The pipeline is designed with a resilient fallback system. In `email_tool.py`, the AI generation is wrapped in a `try/except` block. If the Groq key is revoked, invalid, or hits a billing wall, the system natively falls back to injecting a static, generic pre-written HTML paragraph into the welcome email. The rest of the pipeline (Google Drive creation, Notion duplication, Airtable logging) will execute perfectly unaffected.

**4. How are you managing secrets and environment variables? Where does the API key live in your codebase?**
All secrets are managed entirely outside the source code using a `.env` file loaded via the `python-dotenv` library. The `.env` file holds the Groq API key, Airtable tokens, and Gmail app passwords. There is a strict `.gitignore` file blocking `.env` and `credentials.json` (Google Drive service accounts) from ever being pushed to version control. Keys are accessed dynamically via `os.getenv()`.

**5. What happens if the LLM returns a malformed response? Does your system handle that or does it crash?**
Because we are utilizing the LLM exclusively for copywriting rather than strict JSON structured data-routing, a "malformed" response does not break the code. We use strict Prompt Engineering to forbid markdown blocks and force the LLM to output pure string copy. If it produces strangely formatted text, it simply results in an oddly formatted email paragraph being injected into our HTML, but it is impossible for the text output to crash the underlying Python instances.

**6. Did you encounter any token limit constraints during building, and if so, how did you handle them?**
Because this workflow processes short CRM input strings (Names, Service Plans) and small inbound email replies rather than massive document analysis (RAG), maximum context limit constraints were not an issue. To handle outbound token constraints, we explicitly prompt-engineered the model to enforce brevity: e.g., *"Keep it to 2 short paragraphs max."*

---

## On your architecture and tools

**7. Why did you pick the specific orchestration framework or approach you used?**
We utilized **LangGraph** for validation and **LangChain** for tool chaining because it allows us to enforce heavily structured, deterministic constraints within an AI system. LangGraph establishes clear, state-based boundaries (e.g., "Halt the graph if the Airtable duplicate check returns True"), while LangChain makes it radically trivial to swap out underlying models (e.g., our seamless, one-line transition from xAI to the Groq API using standard LangChain wrappers).

**8. Walk us through one full agent loop from trigger to output. What happens at each step?**
1. The Account Manager submits the React/JS Dashboard form.
2. An HTTP POST request hits `@app.post("/webhook/onboard")` in FastAPI.
3. LangGraph validation triggers (`node_check_duplicate`), querying Airtable for the provided email. If the client is unique, it proceeds.
4. The Orchestrator fires 4 tools sequentially:
   - **Email Tool**: Queries LLM for custom copy, merges it into HTML, and dispatches via Gmail SMTP.
   - **Drive Tool**: Generates a Service Account authenticated Google Drive folder.
   - **Notion Tool**: Deep-copies an Agency project-board template.
   - **Airtable Tool**: Logs the compiled URLs and ID data back into the CRM.
5. In the background, an IMAP listener continuous polls the Inbox. When the client replies to the welcome email, it intercepts the text, passes it to the LLM for classification, and immediately deploys an intelligent Auto-Reply.

**9. Which parts of your system are deterministic and which parts depend on LLM output? Where exactly is that boundary?**
**Deterministic:** The routing (FastAPI), Duplicate Validation (Airtable API SDK), Folder Generation (Drive SDK), Project Board duplication (Notion API), and Record Creation (Airtable SDK).
**LLM Dependent:** The stylistic copywriting of the outbound Welcome Email, and the reasoning/classification of the inbound Auto-Reply mechanism.
**The Boundary:** The LLM strictly controls *what is said* in the email generation functions, but hardcoded deterministic Python controls *who it is sent to* and *how the infrastructure is built*.

**10. If the LLM hallucinates or produces an incorrect classification at a decision point, what does your system do?**
We intentionally isolated the LLM away from critical infrastructural decision-making nodes to prevent devastating hallucinations. Our validation node (Duplicate Checks) computes deterministically using raw code, not prompting. The highest risk of hallucination occurs in the Auto-Reply tool (e.g., confidently quoting the wrong price). To combat this, we explicitly hardcoded system prompt instructions demanding the AI defer complex questions to human Account Managers rather than hallucinating answers.

---

## On the problem you chose

**11. What is the actual business cost of the problem you solved, and does your system fully address it?**
B2B digital agencies burn massive manual hours acting as human APIs—copy-pasting data across Notion, Drive, email clients, and Airtable. This administrative choke-point limits how many clients an agency can onboard simultaneously, resulting in poor customer experience (delays in workspace generation) and high operational overhead. Our system addresses this entirely by compressing a 45-minute manual administration task into a 12-second automated backend process.

**12. Which edge cases from the problem statement did you not handle, and why?**
We do not handle massive PDF email attachments in the auto-reply system, nor do we handle deep, multi-turn AI email conversations where deep historical context is required. The IMAP listener acts as a highly effective "frontline triage" agent to catch initial replies, but we intentionally leave long-term strategic agency communication to the human managers, as full autonomous AI delegation in high-level B2B client services is currently too risky.
