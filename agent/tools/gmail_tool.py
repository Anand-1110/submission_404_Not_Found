"""
Gmail SMTP Tool (alternative to SendGrid)
-----------------------------------------
Use this if you prefer Gmail over SendGrid.
Set USE_GMAIL=true in .env and provide GMAIL_ADDRESS + GMAIL_APP_PASSWORD.

Get a Gmail App Password:
  1. Go to myaccount.google.com/security
  2. Enable 2-Step Verification
  3. Search "App passwords" → Generate → Select "Mail"
  4. Copy the 16-char password → GMAIL_APP_PASSWORD in .env
"""

import os
import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

GMAIL_ADDRESS  = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASSWORD", "")


async def send_via_gmail(to_email: str, subject: str, html_body: str) -> dict:
    """Send email via Gmail SMTP (uses App Password, not your real password)."""
    await asyncio.sleep(0)   # make it awaitable

    if not GMAIL_ADDRESS or not GMAIL_APP_PASS:
        return {"success": False, "error": "GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set in .env"}

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = GMAIL_ADDRESS
        msg["To"]      = to_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASS)
            server.sendmail(GMAIL_ADDRESS, to_email, msg.as_string())

        return {
            "success": True,
            "provider": "gmail",
            "to": to_email,
            "sent_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
