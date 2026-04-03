"""
LangChain ReAct Orchestrator
-----------------------
This is a true Agentic implementation. Instead of a hard-coded script, 
the LLM is granted tools and autonomy to orchestrate the integration sequence.
It interprets results dynamically and closes the loop.
"""

import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

from agent.tools.email_tool import send_welcome_email, send_completion_summary
from agent.tools.drive_tool import create_drive_folder
from agent.tools.notion_tool import create_notion_page
from agent.tools.airtable_tool import create_airtable_record

async def run_orchestrator(payload: dict, run_id: str, logger) -> dict:
    """
    Run the onboarding via LLM orchestration loop.
    Returns a dict with all created resource URLs/IDs to satisfy frontend rendering.
    """
    run_results = {}

    @tool
    async def agent_create_drive_folder() -> str:
        """Call this tool FIRST. Creates a Google Drive workspace folder for the client."""
        logger.info(run_id, "🤖 Agent decided to provision Cloud Storage...")
        res = await create_drive_folder(payload)
        run_results["drive"] = res
        if res.get("success"):
            return f"Successfully created drive folder. Folder URL: {res.get('folder_url')}"
        return f"Failed to create folder: {res.get('error')}"

    @tool
    async def agent_create_notion_page(drive_url: str) -> str:
        """Call this tool SECOND. Creates a Notion Project Board. Must pass the drive_url you obtained from the first step."""
        logger.info(run_id, "🤖 Agent decided to provision Notion workspace...")
        res = await create_notion_page(payload)
        run_results["notion"] = res
        if res.get("success"):
            return f"Successfully created Notion board. Notion URL: {res.get('page_url')}"
        return f"Failed to create Notion: {res.get('error')}"

    @tool
    async def agent_create_airtable_record(drive_url: str, notion_url: str) -> str:
        """Call this tool THIRD. Logs the new client into the CRM. You must pass both the newly generated Drive URL and Notion URL."""
        logger.info(run_id, "🤖 Agent decided to log records into Airtable CRM...")
        res = await create_airtable_record(payload, run_results)
        run_results["airtable"] = res
        if res.get("success"):
            return f"Successfully created Airtable CRM record. ID: {res.get('record_id')}"
        return f"Failed to create Airtable record: {res.get('error')}"

    @tool
    async def agent_send_welcome_email() -> str:
        """Call this tool FOURTH, only after the infrastructure is built. Sends the personalized welcome email to the client."""
        logger.info(run_id, "🤖 Agent decided to invoke Email Dispatch...")
        res = await send_welcome_email(payload)
        run_results["email"] = res
        if res.get("success"):
            return f"Successfully sent welcome email."
        return f"Failed to send email: {res.get('error')}"

    tools = [
        agent_create_drive_folder,
        agent_create_notion_page,
        agent_create_airtable_record,
        agent_send_welcome_email
    ]
    tool_map = {t.name: t for t in tools}

    # ── Connect Brain ────────────────────────────────────────────────────────
    grok_key = os.getenv("GROK_API_KEY", "")
    llm = ChatOpenAI(
        api_key=grok_key, 
        base_url="https://api.groq.com/openai/v1", 
        model="llama-3.3-70b-versatile", 
        temperature=0.1
    ).bind_tools(tools)

    system_prompt = (
        "You are the Scrollhouse Autonomous Onboarding Agent.\n"
        "Your job is to orchestrate the provisioning of a new B2B client.\n\n"
        "You have absolute agency, but you MUST evaluate and execute your tools logically:\n"
        "1. First, create the Drive folder to secure cloud storage.\n"
        "2. Second, map the Notion page. You must pass the generated Drive URL to this tool.\n"
        "3. Third, create the Airtable record. You must pass the Notion and Drive URLs securely into the CRM.\n"
        "4. Finally, dispatch the welcome email to the client now that the infrastructure is ready.\n\n"
        "Evaluate the JSON response from each tool before proceeding. Once the email is dispatched and all 4 succeed, output 'Onboarding Fully Complete'."
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Client Payload:\n{json.dumps(payload, indent=2)}")
    ]

    # ── Execute Agent Loop (Native LangChain Core) ───────────────────────────
    logger.info(run_id, "Initiating LLM Agent execution Loop (ReAct)...")
    
    max_iterations = 6
    for i in range(max_iterations):
        ai_msg = await llm.ainvoke(messages)
        messages.append(ai_msg)
        
        if not ai_msg.tool_calls:
            # LLM decided it is finished
            break
            
        for tool_call in ai_msg.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            selected_tool = tool_map.get(tool_name)
            
            if selected_tool:
                try:
                    # Invoke tool dynamically
                    tool_result = await selected_tool.ainvoke(tool_args)
                except Exception as e:
                    tool_result = str(e)
            else:
                tool_result = f"Error: Tool {tool_name} not found."
                
            messages.append(ToolMessage(tool_call_id=tool_call["id"], content=str(tool_result)))
            
    logger.success(run_id, "LLM Agent loop achieved termination objective ✓")

    # Final silent step outside LLM purview
    summary_result = await send_completion_summary(payload, run_results, run_id)
    run_results["summary"] = summary_result

    return run_results
