"""
Dedolytics ABM Outreach Bot — AI-generated enterprise email campaigns.

Generates hyper-personalized HTML emails using Gemini AI with dynamic
case study injection, then dispatches via Google Workspace SMTP with
sender rotation.
"""

import smtplib
from email.message import EmailMessage
import os
import time
import random
import uuid
import db
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# Load our 3 email accounts
EMAIL_ACCOUNTS = [
    {"email": os.getenv("EMAIL_1_ADDRESS"), "password": os.getenv("EMAIL_1_PASSWORD")},
    {"email": os.getenv("EMAIL_2_ADDRESS"), "password": os.getenv("EMAIL_2_PASSWORD")},
    {"email": os.getenv("EMAIL_3_ADDRESS"), "password": os.getenv("EMAIL_3_PASSWORD")},
]

SENDER_NAMES = ["Paul", "Ed", "Will"]

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY and GEMINI_API_KEY != "your-gemini-api-key-here":
    genai.configure(api_key=GEMINI_API_KEY)


def generate_abm_email_with_gemini(persona, company, contact_name, industry_note, sender_name):
    """
    Uses Gemini to craft a hyper-personalized HTML ABM email based on the Dedolytics case studies.
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your-gemini-api-key-here":
        return "Subject: Chat about Data\nHi, let's chat about data at your company."

    model = genai.GenerativeModel("gemini-2.0-flash")

    first_name = contact_name.split()[0] if contact_name else persona

    # Dynamic Case Study Injection Based on Dedolytics Portfolio
    case_study_text = ""
    case_study_url = ""
    if "retail" in industry_note.lower() or "merchandising" in industry_note.lower():
        case_study_text = "We recently built a 'RedSticker' Power BI dashboard for a similar retail enterprise that tracked over $5.1M in markdowns and caught budget overruns at the category level before they escalated."
        case_study_url = "https://www.dedolytics.org/projects/redsticker.html"
    elif "supply chain" in industry_note.lower() or "inventory" in industry_note.lower():
        case_study_text = "We recently deployed a Replenishment Intelligence Suite for a partner that maintained a 96.79% CSL across $88.86M in stock while identifying critical allocation gaps."
        case_study_url = "https://www.dedolytics.org/projects/inventory.html"
    else:
        case_study_text = "We recently built an Executive Command Center for a partner that gave the C-suite instant, automated visibility into KPI variance, cutting decision latency from days to hours."
        case_study_url = "https://www.dedolytics.org/projects/executive.html"

    prompt = f"""
    You are {sender_name}, a Partner at Dedolytics (https://www.dedolytics.org), a premium data consulting firm specializing in Power BI, SQL, and Snowflake.

    Write a highly professional, short, punchy cold email to {first_name} (the {persona}) at {company} in RAW HTML format.

    Instructions:
    1. Do not use generic corporate jargon. Be extremely direct and value-focused.
    2. Start the very first line of your output with "Subject: " followed by a catchy subject line.
    3. The rest of your output must be the raw HTML code for the email body. DO NOT output markdown code blocks (e.g. no ```html). Just the HTML.
    4. Use professional fonts (font-family: Arial, Helvetica, sans-serif;) and styling that looks clean and modern.

    Content requirements:
    - Paragraph 1: Acknowledge their role scaling data operations at {company}.
    - Paragraph 2: Mention this exact scenario, and hyperlink the relevant phase to the case study URL: "{case_study_text}". (Link: {case_study_url})
    - Paragraph 3: End with a low-friction call to action asking for a quick 10-minute chat next week to show them the semantic model. Include this exact HTML anchor tag to let them book time: <a href="https://calendar.google.com/calendar/u/0/appointments/schedules/AcZssZ2HePxAUUQzDdORvH9M7ZxCnczzZHTq6w_Ubpjy2STAQTLqYfAgCC9bqNidQSiguEqe1_1kJ_lx">Book some time with us</a>

    Formatting and Signature requirement:
    - At the bottom of the email, include a highly professional email signature for {sender_name}.
    - The signature MUST include the Dedolytics logo image: <img src="https://www.dedolytics.org/assets/images/logo.jpeg" alt="Dedolytics Logo" width="150" />
    - The signature must include your title (Partner), company name hyperlinked (Dedolytics), and website URL.
    - Structure it cleanly using HTML tables or divs for a premium feel.
    """

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Clean up if Gemini accidentally outputs markdown blocks
        if "```html" in text:
            text = text.replace("```html", "").replace("```", "").strip()
        return text
    except Exception as e:
        print(f"      [-] Gemini email generation failed: {e}")
        fallback = f"Subject: Data Analytics at {company}\n\nHi {first_name},\n\nI noticed your role scaling the data team at {company}. We build premium Power BI & Snowflake dashboards that track millions in variance. {case_study_text} \n\nOpen to a quick intro chat?\n\nBest,\n{sender_name}"
        return fallback


def _html_to_plain_text(html_body):
    """Extracts a meaningful plain-text version from HTML for the text/plain MIME part."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_body, "html.parser")
    for tag in soup(["style", "script"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n\n".join(lines)


def _insert_tracking_pixel(html_body, tracking_id, base_url):
    """Inserts a 1x1 invisible tracking pixel into the HTML email body."""
    pixel_url = f"{base_url}/pixel/{tracking_id}.png"
    pixel_tag = (
        f'<img src="{pixel_url}" width="1" height="1" alt="" '
        f'style="display:block;width:1px;height:1px;border:0;opacity:0;" />'
    )
    # Insert before </body> if present
    lower = html_body.lower()
    idx = lower.rfind("</body>")
    if idx != -1:
        return html_body[:idx] + pixel_tag + html_body[idx:]
    # Fall back to before </html>
    idx = lower.rfind("</html>")
    if idx != -1:
        return html_body[:idx] + pixel_tag + html_body[idx:]
    # Last resort: append
    return html_body + pixel_tag


def send_email(to_address, subject, html_body, sender_email, sender_password, sender_name, tracking_id=None):
    """Sends an HTML email via Google Workspace SMTP with optional tracking pixel."""
    # Insert tracking pixel if configured
    tracking_base_url = os.getenv("TRACKING_BASE_URL", "")
    if tracking_id and tracking_base_url:
        html_body = _insert_tracking_pixel(html_body, tracking_id, tracking_base_url)

    if not sender_email or not sender_password:
        print("      [!] Email simulation (Credentials missing)")
        return {"success": True, "simulated": True}

    try:
        msg = EmailMessage()
        # Use a meaningful plain-text version (spam filters penalize empty/generic text parts)
        plain_text = _html_to_plain_text(html_body)
        msg.set_content(plain_text)
        msg.add_alternative(html_body, subtype="html")

        msg["Subject"] = subject
        msg["From"] = f"{sender_name} <{sender_email}>"
        msg["To"] = to_address

        # Reply-To ensures responses reach a monitored inbox
        msg["Reply-To"] = "hello@dedolytics.org"

        # List-Unsubscribe — required by Gmail/Yahoo since Feb 2024 for bulk senders
        msg["List-Unsubscribe"] = "<mailto:unsubscribe@dedolytics.org?subject=Unsubscribe>"

        # Always BCC the founder for tracking
        msg["Bcc"] = "hello@dedolytics.org"

        # Connect to Gmail SMTP server
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return {"success": True}
    except smtplib.SMTPRecipientsRefused as e:
        print(f"      [-] Hard bounce for {to_address}: {e}")
        return {"success": False, "bounce_status": "hard_bounce", "bounce_message": str(e)}
    except smtplib.SMTPException as e:
        error_str = str(e)
        if any(code in error_str for code in ["421", "450", "451", "452"]):
            print(f"      [-] Soft bounce for {to_address}: {e}")
            return {"success": False, "bounce_status": "soft_bounce", "bounce_message": error_str}
        print(f"      [-] SMTP error for {to_address}: {e}")
        return {"success": False, "bounce_status": None, "bounce_message": error_str}
    except Exception as e:
        print(f"      [-] Failed to send SMTP email to {to_address} from {sender_email}: {e}")
        return {"success": False, "bounce_status": None, "bounce_message": str(e)}


def run_outreach_cycle():
    """Reads enriched jobs, generates ABM emails, and dispatches them."""
    print(f"\n--- Starting ABM AI Outreach Cycle at {time.strftime('%Y-%m-%d %H:%M:%S')} ---")

    # get_pending_outreach_jobs returns: j.id, j.title (persona), j.company, c.id, c.name, c.email, j.description (industry_note)
    pending_jobs = db.get_pending_outreach_jobs()

    print(f"[*] Found {len(pending_jobs)} enriched targets ready for ABM outreach.")

    success_count = 0

    # Filter out empty accounts
    valid_accounts = [acc for acc in EMAIL_ACCOUNTS if acc["email"] and acc["password"]]

    if not valid_accounts:
        print("[!] No valid email accounts found in .env. Will run simulation.")
        valid_accounts = [{"email": "simulation@example.com", "password": ""}]

    for i, (job_id, persona, company, contact_id, contact_name, email, industry_note) in enumerate(pending_jobs):
        sender_account = valid_accounts[i % len(valid_accounts)]
        sender_email = sender_account["email"]
        sender_password = sender_account["password"]

        sender_name = random.choice(SENDER_NAMES)

        print(
            f"\n[*] Drafting ABM HTML Email for {contact_name} ({persona}) at {company} (Using {sender_email} as {sender_name})"
        )

        # 1. Generate Email Content
        raw_email = generate_abm_email_with_gemini(persona, company, contact_name, industry_note, sender_name)

        lines = raw_email.split("\n", 1)
        subject = lines[0].replace("Subject:", "").strip() if "Subject:" in lines[0] else f"Analytics at {company}"
        html_body = lines[1].strip() if len(lines) > 1 else raw_email

        print(f"      [~] Subject: {subject}")
        print("      [~] HTML Generation successful. Dispatching...")

        # 2. Generate tracking ID for read-receipt pixel
        tracking_id = str(uuid.uuid4())
        print(f"      [~] Tracking ID: {tracking_id}")

        # 3. Send via SMTP (with tracking pixel injection)
        result = send_email(
            email, subject, html_body, sender_email, sender_password, sender_name, tracking_id=tracking_id
        )

        if result.get("success"):
            print(f"      [+] Email Sent Successfully to {email} via {sender_email}")

            # 4. Log and Update DB Status
            db.log_email(job_id, contact_id, sender_email, "ABM_Dynamic_Case_Study", subject)
            db.mark_job_emailed(job_id)

            # 5. Create email event for tracking pixel reads
            try:
                db.create_email_event(contact_id, "abm_outreach", tracking_id)
                print(f"      [+] Email event created with tracking ID for read receipts")
            except Exception as ev_err:
                print(f"      [!] Could not create email event: {ev_err}")

            success_count += 1
        else:
            # Handle bounces
            bounce_status = result.get("bounce_status")
            if bounce_status:
                print(f"      [-] Bounce detected ({bounce_status}): {result.get('bounce_message', '')}")
                try:
                    db.record_bounce(tracking_id, bounce_status, result.get("bounce_message", ""))
                except Exception as b_err:
                    print(f"      [!] Could not record bounce: {b_err}")

        time.sleep(2)  # Anti-spam delay between emails

    print(f"\n[*] Outreach Complete. Successfully emailed {success_count} prospects.")
    print(f"--- Finished Outreach Cycle at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")


if __name__ == "__main__":
    run_outreach_cycle()
