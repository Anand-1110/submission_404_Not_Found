import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from agent.tools.email_tool import _send

async def handle_inbound_email(sender_email: str, subject: str, text_body: str) -> dict:
    """
    Analyzes an inbound email from a client and uses an LLM to generate an 
    appropriate, polite, and contextual auto-reply.
    """
    grok_key = os.getenv("GROK_API_KEY", "").strip()
    
    if not grok_key:
        return {"success": False, "error": "No GROK_API_KEY present to handle auto-replies."}
        
    try:
        # Construct the AI Brain using Grok
        llm = ChatOpenAI(
            api_key=grok_key, 
            base_url="https://api.groq.com/openai/v1",
            model="llama-3.3-70b-versatile", 
            temperature=0.5
        )
        
        prompt = PromptTemplate.from_template(
            """You are an enthusiastic customer success agent at Scrollhouse.
A client just sent an email.
Client Email Address: {sender_email}
Subject Line: {subject}
Message Body:
{text_body}

Instructions:
1. Determine what the client is asking or stating.
2. Reply professionally and warmly.
3. If they are asking a complex question about their account, say that their Account Manager has been notified and will follow up shortly.
4. Keep the response to 2 short paragraphs max.
5. Sign off as "The Scrollhouse Auto-Agent".

Respond ONLY with the email content, no markdown blocks, no internal monologues."""
        )
        
        chain = prompt | llm
        
        res = await chain.ainvoke({
            "sender_email": sender_email,
            "subject": subject,
            "text_body": text_body
        })
        
        reply_text = res.content
        
        # Render the text into a simple HTML format
        reply_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:20px;font-family:Inter,Arial,sans-serif;color:#374151;">
  <div style="line-height:1.6;">
    {reply_text.replace(chr(10), '<br>')}
  </div>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0;">
  <p style="font-size:12px;color:#9ca3af;">Auto-generated reply powered by Scrollhouse AI.</p>
</body>
</html>"""

        # Dispatch the reply back to the client
        reply_subject = f"Re: {subject}" if not subject.startswith("Re:") else subject
        
        send_result = await _send(sender_email, reply_subject, reply_html)
        
        return {
            "success": send_result.get("success"),
            "reply_drafted": reply_text,
            "send_result": send_result
        }
        
    except Exception as e:
        print(f"[LLM REPLY ERROR] {str(e)}")
        return {"success": False, "error": str(e)}
