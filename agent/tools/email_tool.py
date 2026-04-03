"""
Email Tool — supports SendGrid OR Gmail SMTP
--------------------------------------------
Set USE_GMAIL=true in .env to use Gmail instead of SendGrid.

SendGrid setup:
  - Get API key from: https://app.sendgrid.com/settings/api_keys
  - Verify sender at: https://app.sendgrid.com/settings/sender_auth

Gmail setup (no SendGrid account needed):
  - Enable 2FA on your Google account
  - Create App Password at: myaccount.google.com/apppasswords
  - Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env
"""

import os
import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

# New: Top-level SendGrid imports for better error handling visibility
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
except ImportError:
    pass

MOCK           = os.getenv("MOCK_TOOLS", "true").lower() == "true"
USE_GMAIL      = os.getenv("USE_GMAIL", "false").lower() == "true"
USE_RESEND     = os.getenv("USE_RESEND", "false").lower() == "true"
SENDGRID_KEY   = os.getenv("SENDGRID_API_KEY", "").strip()
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
FROM_EMAIL     = os.getenv("FROM_EMAIL", "").strip()
MANAGER_EMAIL  = os.getenv("MANAGER_EMAIL", "").strip()
GMAIL_ADDRESS  = os.getenv("GMAIL_ADDRESS", "").strip()
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASSWORD", "").strip()


# ── HTML Templates ─────────────────────────────────────────────────────────────

def _welcome_html(p: dict, ai_intro: str = None) -> str:
    plan_display = p['service_plan'].capitalize()
    
    # If no AI intro is provided, fallback to the default static email paragraph
    default_intro = f"""
          <p style="color:#374151;font-size:16px;margin:0 0 16px;">Hi <strong>{p['client_name']}</strong>,</p>
          <p style="color:#374151;font-size:15px;line-height:1.6;">We're thrilled to have you on board on the
            <strong style="color:#7c3aed;">{plan_display} Plan</strong>, starting
            <strong>{p['start_date']}</strong>.
          </p>"""

    intro_block = ai_intro.replace('\n', '<br>') if ai_intro else default_intro

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Inter,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 20px;">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
        <!-- Header -->
        <tr><td style="background:linear-gradient(135deg,#7c3aed,#3b82f6);padding:40px;text-align:center;">
          <h1 style="margin:0;color:#ffffff;font-size:28px;font-weight:800;">Welcome to Scrollhouse! 🎉</h1>
          <p style="margin:12px 0 0;color:rgba(255,255,255,0.85);font-size:16px;">Your onboarding is complete</p>
        </td></tr>
        <!-- Body -->
        <tr><td style="padding:40px;">
          <div style="color:#374151;font-size:15px;line-height:1.6;margin-bottom:16px;">
            {intro_block}
          </div>
          <p style="color:#374151;font-size:15px;line-height:1.6;">
            Your account manager <strong>{p['account_manager']}</strong> will reach out within 24 hours
            to schedule your kickoff call.
          </p>
          <!-- What we've set up -->
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8f5ff;border-radius:8px;padding:24px;margin:24px 0;">
            <tr><td>
              <p style="margin:0 0 12px;font-weight:700;color:#7c3aed;font-size:14px;letter-spacing:1px;text-transform:uppercase;">What we've set up for you</p>
              <p style="margin:6px 0;color:#374151;">✅ &nbsp;Dedicated Google Drive workspace folder</p>
              <p style="margin:6px 0;color:#374151;">✅ &nbsp;Notion project page created from template</p>
              <p style="margin:6px 0;color:#374151;">✅ &nbsp;CRM profile created in our system</p>
              <p style="margin:6px 0;color:#374151;">✅ &nbsp;This welcome email (you're reading it!)</p>
            </td></tr>
          </table>
          <p style="color:#374151;font-size:15px;">Talk soon,<br/><strong>The Scrollhouse Team</strong></p>
        </td></tr>
        <!-- Footer -->
        <tr><td style="background:#f9fafb;padding:20px;text-align:center;">
          <p style="margin:0;color:#9ca3af;font-size:12px;">© 2026 Scrollhouse · You're receiving this because you signed up</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _summary_html(p: dict, results: dict, run_id: str) -> str:
    drive_url   = results.get("drive",    {}).get("folder_url", "N/A")
    notion_url  = results.get("notion",   {}).get("page_url",   "N/A")
    airtable_id = results.get("airtable", {}).get("record_id",  "N/A")
    return f"""<!DOCTYPE html>
<html>
<body style="font-family:Inter,Arial,sans-serif;background:#f4f4f4;margin:0;padding:40px 20px;">
  <div style="max-width:600px;margin:auto;background:#fff;border-radius:12px;padding:32px;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
    <h2 style="color:#22c55e;margin:0 0 8px;">✅ Onboarding Complete</h2>
    <p style="color:#6b7280;margin:0 0 24px;">Run ID: <code style="background:#f3f4f6;padding:2px 6px;border-radius:4px;">{run_id}</code></p>
    <table width="100%" cellpadding="8" style="border-collapse:collapse;">
      <tr style="background:#f8f5ff;"><td style="color:#7c3aed;font-weight:600;width:140px;">Client</td><td style="color:#111827;">{p['client_name']}</td></tr>
      <tr><td style="color:#6b7280;font-weight:500;">Email</td><td style="color:#111827;">{p['client_email']}</td></tr>
      <tr style="background:#f8f5ff;"><td style="color:#6b7280;font-weight:500;">Plan</td><td style="color:#111827;">{p['service_plan'].capitalize()}</td></tr>
      <tr><td style="color:#6b7280;font-weight:500;">Start Date</td><td style="color:#111827;">{p['start_date']}</td></tr>
      <tr style="background:#f8f5ff;"><td style="color:#6b7280;font-weight:500;">Drive Folder</td><td><a href="{drive_url}" style="color:#3b82f6;">{drive_url}</a></td></tr>
      <tr><td style="color:#6b7280;font-weight:500;">Notion Page</td><td><a href="{notion_url}" style="color:#3b82f6;">{notion_url}</a></td></tr>
      <tr style="background:#f8f5ff;"><td style="color:#6b7280;font-weight:500;">Airtable ID</td><td style="color:#111827;font-family:monospace;">{airtable_id}</td></tr>
    </table>
  </div>
</body>
</html>"""


def _alert_html(p: dict, errors: list, run_id: str) -> str:
    err_list = "".join([f"<li style='margin-bottom:6px;'>{e}</li>" for e in errors])
    return f"""<!DOCTYPE html>
<html>
<body style="font-family:Inter,Arial,sans-serif;background:#f4f4f4;margin:0;padding:40px 20px;">
  <div style="max-width:600px;margin:auto;background:#fff;border-radius:12px;padding:32px;box-shadow:0 4px 24px rgba(0,0,0,0.08);border-top: 6px solid #ef4444;">
    <h2 style="color:#ef4444;margin:0 0 8px;">🛑 Action Required: Onboarding Failed</h2>
    <p style="color:#6b7280;margin:0 0 24px;">Run ID: <code style="background:#f3f4f6;padding:2px 6px;border-radius:4px;">{run_id}</code></p>
    
    <p style="color:#374151;font-size:15px;line-height:1.6;">
      An onboarding webhook for <strong>{p['client_name']} ({p['client_email']})</strong> was halted automatically because it triggered the following critical database errors:
    </p>
    
    <div style="background:#fef2f2;border:1px solid #fca5a5;border-radius:8px;padding:16px;margin:24px 0;">
      <ul style="color:#b91c1c;margin:0;padding-left:20px;font-weight:500;">
        {err_list}
      </ul>
    </div>
    
    <p style="color:#374151;font-size:14px;line-height:1.6;">
      No databases were mutated and no welcome emails were sent. Please fix the conflicting records and submit the onboarding form again.
    </p>
  </div>
</body>
</html>"""


# ── Sender dispatch ────────────────────────────────────────────────────────────
import httpx

async def _send(to_email: str, subject: str, html_body: str) -> dict:
    """Route to SendGrid, Resend, or Gmail based on .env config."""

    if USE_RESEND:
        # ── Resend API (HTTP) ─────────────────────────────────────────────────
        try:
            url = "https://api.resend.com/emails"
            headers = {
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json"
            }
            # Use Resend's default verified domain if FROM_EMAIL is a gmail address to avoid DMARC
            sender = "onboarding@resend.dev" if "gmail.com" in FROM_EMAIL else FROM_EMAIL
            
            payload = {
                "from": f"Scrollhouse <{sender}>",
                "to": [to_email],
                "subject": subject,
                "html": html_body
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code in (200, 201):
                    return {"success": True, "provider": "resend", "to": to_email, "sent_at": datetime.utcnow().isoformat()}
                else:
                    err = resp.text
                    print(f"[ERROR] Resend failed: {resp.status_code} - {err}")
                    return {"success": False, "provider": "resend", "error": err}
        except Exception as e:
            return {"success": False, "provider": "resend", "error": str(e)}

    if USE_GMAIL:
        # ── Gmail SMTP ────────────────────────────────────────────────────────
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"]    = GMAIL_ADDRESS
            msg["To"]      = to_email
            msg.attach(MIMEText(html_body, "html"))
            
            # Using Port 587 (STARTTLS) for better cloud compatibility
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls() 
                server.login(GMAIL_ADDRESS, GMAIL_APP_PASS)
                server.sendmail(GMAIL_ADDRESS, to_email, msg.as_string())
            return {"success": True, "provider": "gmail", "to": to_email, "sent_at": datetime.utcnow().isoformat()}
        except Exception as e:
            return {"success": False, "provider": "gmail", "error": str(e)}
    else:
        # ── SendGrid ──────────────────────────────────────────────────────────
        try:
            message = Mail(
                from_email=FROM_EMAIL,
                to_emails=to_email,
                subject=subject,
                html_content=html_body,
            )
            sg = SendGridAPIClient(SENDGRID_KEY)
            response = sg.send(message)
            return {
                "success": response.status_code in (200, 202),
                "provider": "sendgrid",
                "status_code": response.status_code,
                "to": to_email,
                "sent_at": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            # Enhanced error logging for SendGrid
            err_msg = str(e)
            if hasattr(e, 'body'):
                # SendGrid often returns a 403/401 if the sender isn't verified
                err_msg = f"{e.status_code}: {e.body.decode('utf-8')}"
                if e.status_code == 403:
                    err_msg += " (HINT: Have you verified your 'Single Sender' in SendGrid Settings?)"
                if e.status_code == 401:
                    err_msg += " (HINT: Your SENDGRID_API_KEY is invalid or missing.)"
            print(f"[ERROR] SendGrid failed: {err_msg}")
            return {"success": False, "provider": "sendgrid", "error": err_msg}


# ── Public API ─────────────────────────────────────────────────────────────────

async def send_welcome_email(payload: dict) -> dict:
    await asyncio.sleep(0)

    if MOCK:
        print(f"[MOCK EMAIL] Welcome email → {payload['client_email']}")
        return {"success": True, "mock": True, "to": payload["client_email"], "sent_at": datetime.utcnow().isoformat()}

    # Check for Grok API key to use dynamic personalisation
    ai_intro = None
    grok_key = os.getenv("GROK_API_KEY", "").strip()
    if grok_key and payload.get("notes"):
        try:
            llm = ChatOpenAI(
                api_key=grok_key,
                openai_api_key=grok_key, # for compatibility
                base_url="https://api.groq.com/openai/v1",
                model="llama-3.3-70b-versatile", 
                temperature=2
            )
            prompt = PromptTemplate.from_template(
                """You are an enthusiastic Account Manager at a digital agency called Scrollhouse.
Write the first two paragraphs of a welcome email to a new client.
Client Name: {client_name}
Service Plan: {service_plan}
Client's Signup Notes: {notes}

Guidelines:
- Start with "Hi [Name],"
- Acknowledge their specific notes/industry in a highly personalized way.
- Tell them you're excited to start working on their {service_plan} plan.
- Keep it to 2 short paragraphs max.
- Use a friendly, warm, professional tone. Do not include signatures or sign-offs."""
            )
            chain = prompt | llm
            res = await chain.ainvoke({
                "client_name": payload["client_name"],
                "service_plan": payload["service_plan"],
                "notes": payload["notes"]
            })
            ai_intro = res.content
        except Exception as e:
            print(f"[WARN] Failed to generate AI intro, falling back to static: {e}")

    subject = f"Welcome to Scrollhouse, {payload['client_name']}! 🎉"
    return await _send(payload["client_email"], subject, _welcome_html(payload, ai_intro))


async def send_completion_summary(payload: dict, results: dict, run_id: str) -> dict:
    await asyncio.sleep(0)

    if not MANAGER_EMAIL:
        return {"success": False, "error": "MANAGER_EMAIL not set in .env"}

    if MOCK:
        print(f"[MOCK EMAIL] Summary → {MANAGER_EMAIL}")
        return {"success": True, "mock": True, "to": MANAGER_EMAIL}

    subject = f"[Scrollhouse] {payload['client_name']} onboarded ✓ — {run_id}"
    return await _send(MANAGER_EMAIL, subject, _summary_html(payload, results, run_id))


async def send_alert_email(payload: dict, errors: list, run_id: str) -> dict:
    """Dispatches a critical error email natively to the designated Account Manager."""
    await asyncio.sleep(0)

    if not MANAGER_EMAIL:
        return {"success": False, "error": "MANAGER_EMAIL not set in .env"}

    if MOCK:
        print(f"[MOCK EMAIL] Alert → {MANAGER_EMAIL}")
        return {"success": True, "mock": True, "to": MANAGER_EMAIL}

    subject = f"🛑 [URGENT] Onboarding Failed - {payload['client_name']}"
    return await _send(MANAGER_EMAIL, subject, _alert_html(payload, errors, run_id))
