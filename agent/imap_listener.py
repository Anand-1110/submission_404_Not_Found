import os
import imaplib
import email
import asyncio
from email.header import decode_header
from agent.tools.llm_reply_tool import handle_inbound_email
from agent.logger import AgentLogger

logger = AgentLogger()

def decode_header_value(header_value):
    if not header_value:
        return ""
    decoded_fragments = decode_header(header_value)
    result = ""
    for frag, encoding in decoded_fragments:
        if isinstance(frag, bytes):
            try:
                result += frag.decode(encoding or "utf-8", errors="ignore")
            except:
                result += frag.decode("utf-8", errors="ignore")
        else:
            result += str(frag)
    return result

def get_text_from_email(msg):
    text_content = ""
    html_content = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition"))
            if ct == "text/plain" and "attachment" not in cd:
                try: text_content += part.get_payload(decode=True).decode("utf-8", errors="ignore")
                except: pass
            elif ct == "text/html" and "attachment" not in cd:
                try: html_content += part.get_payload(decode=True).decode("utf-8", errors="ignore")
                except: pass
    else:
        ct = msg.get_content_type()
        if ct == "text/plain":
            try: text_content = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
            except: pass
        elif ct == "text/html":
            try: html_content = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
            except: pass
            
    # Prefer plain text if available, fallback to html string
    return text_content.strip() if text_content else html_content.strip()

async def start_imap_listener():
    username = os.getenv("GMAIL_ADDRESS", "").strip()
    password = os.getenv("GMAIL_APP_PASSWORD", "").strip()

    if not username or not password:
        logger.warning("inbound", "IMAP listener disabled: Missing GMAIL_ADDRESS or APP_PASSWORD in .env")
        return

    logger.info("inbound", f"Starting background IMAP listener for {username}")
    
    while True:
        try:
            # Login and select inbox
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(username, password)
            mail.select("inbox")

            # Search for ANY unread messages
            status, messages = mail.search(None, "UNSEEN")
            if status == "OK" and messages[0]:
                for num in messages[0].split():
                    # Fetching the email flags it as SEEN automatically by most IMAP servers
                    status, msg_data = mail.fetch(num, "(RFC822)")
                    if status == "OK":
                        for response_part in msg_data:
                            if isinstance(response_part, tuple):
                                msg = email.message_from_bytes(response_part[1])
                                
                                sender = decode_header_value(msg.get("From"))
                                subject = decode_header_value(msg.get("Subject"))
                                body = get_text_from_email(msg)

                                sender_email = sender
                                if "<" in sender and ">" in sender:
                                    sender_email = sender.split("<")[1].split(">")[0]

                                # Prevent infinite loops by rejecting emails from ourselves
                                if username in sender_email:
                                    continue
                                    
                                logger.info("inbound", f"IMAP caught unread email from: {sender_email}")
                                
                                # Process the email internally simulating the webhook payload
                                result = await handle_inbound_email(sender_email, subject, body)
                                
                                if result.get("success"):
                                    logger.success("inbound", f"Auto-Reply deployed to {sender_email} ✓")
                                else:
                                    logger.error("inbound", f"Auto-Reply failed: {result.get('error')}")                                
            
            # Close connection properly
            mail.logout()
            
        except Exception as e:
            logger.error("inbound", f"IMAP background loop error: {e}")

        # Pause before polling again
        await asyncio.sleep(15)
