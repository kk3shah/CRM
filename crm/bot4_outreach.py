"""
Dedolytics SMB Outreach Bot — Initial emails + automated follow-ups.

Sends AI-generated infographic emails to new leads, then sends up to 3
templated follow-up emails at 7-day intervals.

Safety: OS-level file lock prevents concurrent execution. DB-level
email_sent='yes' prevents duplicate sends to the same address.
"""

import os
import sys
import time
import uuid
import smtplib
from email.message import EmailMessage
import db
import random
import fcntl
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

# ─── SMTP Accounts ───────────────────────────────────────────────────────────
EMAIL_ACCOUNTS = [
    {"email": os.getenv("EMAIL_1_ADDRESS"), "password": os.getenv("EMAIL_1_PASSWORD")},
    {"email": os.getenv("EMAIL_2_ADDRESS"), "password": os.getenv("EMAIL_2_PASSWORD")},
    {"email": os.getenv("EMAIL_3_ADDRESS"), "password": os.getenv("EMAIL_3_PASSWORD")},
]

SENDER_NAMES = ["Paul", "Ed", "Will"]

CALENDAR_LINK = "https://calendar.google.com/calendar/u/0/appointments/schedules/AcZssZ2HePxAUUQzDdORvH9M7ZxCnczzZHTq6w_Ubpjy2STAQTLqYfAgCC9bqNidQSiguEqe1_1kJ_lx"

# ─── Follow-Up Templates ─────────────────────────────────────────────────────

FOLLOWUP_TEMPLATES = [
    # Follow-up 1 (7 days after initial email)
    {
        "subject": "Quick follow-up — {company_name} analytics",
        "body": """Hi there,

I recently sent over a custom analytics idea we put together for {company_name}. Did you get a chance to take a look?

We specialize in helping {category} businesses unlock hidden profits through data — and the first project is completely free, no strings attached.

If you have 15 minutes this week, I'd love to walk you through what we found: {calendar_link}

— {sender_name}
Dedolytics | Local Growth Data""",
    },
    # Follow-up 2 (14 days after initial email)
    {
        "subject": "Still available — free pilot audit for {company_name}",
        "body": """Hi,

Just a quick note — the free pilot offer we put together for {company_name} is still available.

Here's what that includes:
- A custom data audit (e.g., inventory or aisle optimization)
- First project/month completely free ($0)
- No technical knowledge or IT setup needed

Only 8.8% of small businesses actively use data-driven audits today — we help you get ahead of the curve.

Are you open for a quick chat? {calendar_link}

— {sender_name}
Dedolytics | {category} Efficiency""",
    },
    # Follow-up 3 / final (21 days after initial email)
    {
        "subject": "Closing out — {company_name} custom trial",
        "body": """Hi,

I wanted to reach out one last time about the free data audit we proposed for {company_name}.

I completely understand if the timing isn't right — running a {category} business keeps you busy. But if data-driven decisions are something you'd like to explore in the future, our door is always open.

The offer: $0 for the first project, then transparent flat pricing if you see value.

Wishing you continued success,

— The Dedolytics Team
dedolytics.org""",
    },
]

ECOM_FOLLOWUP_TEMPLATES = [
    # E-com Follow-up 1 (7 days)
    {
        "subject": "Quick follow-up — {company_name} revenue sprint",
        "body": """Hi there,

I recently sent over a revenue leakage idea we prepared specifically for {company_name}. Did you get a chance to take a look?

We specialize in helping {category} brands plug hidden profit leaks. Our model: First project is $0. If we don't find actionable opportunity, you don't pay us a dime in the future either.

If you have 15 minutes this week, I'd love to walk you through exactly where we think efficiency can be improved: {calendar_link}

— {sender_name}
Dedolytics | Performance Data Engineering""",
    },
    # E-com Follow-up 2 (14 days)
    {
        "subject": "Still available — Revenue Sprint for {company_name}",
        "body": """Hi,

Just a quick note — the performance audit we put together for {company_name} is still available.

In just 2 weeks, we map out full funnel leakage points, analyze AOV friction, and deliver a prioritized playbook for the {category} space.

Total cost for the first sprint: $0.

Are you open to a strategy call? {calendar_link}

— {sender_name}
Dedolytics | Performance Data Engineering""",
    },
    # E-com Follow-up 3 (21 days)
    {
        "subject": "Closing out — {company_name} revenue audit",
        "body": """Hi,

I wanted to reach out one last time about the revenue sprint we proposed for {company_name}.

I completely understand if the timing isn't right — scaling a {category} brand keeps you busy. But if finding hidden profit margins is something you'd like to explore in the future, our door is open.

The hook remains the same: First project is $0.

Best regards,

— The Dedolytics Team
dedolytics.org""",
    },
]


# ─── Email Sending ────────────────────────────────────────────────────────────


def _html_to_plain_text(html_body):
    """Extracts a meaningful plain-text version from HTML for the text/plain MIME part."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_body, "html.parser")
    # Remove style/script tags
    for tag in soup(["style", "script"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    # Collapse excessive blank lines
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n\n".join(lines)


def _insert_tracking_pixel(html_body, tracking_id, base_url):
    """Inserts a 1x1 invisible tracking pixel into the HTML email body."""
    pixel_url = f"{base_url}/pixel.php?id={tracking_id}"
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


def send_html_email(
    to_address, subject, html_body, sender_email, sender_password, sender_name, tracking_id=None, force_plain_text=False
):
    """
    Sends an email via Google Workspace SMTP.
    If force_plain_text is True, sends text/plain only (our deliverability strategy).
    Includes Reply-To and List-Unsubscribe headers required by Gmail/Yahoo bulk sender policy.
    Retries transient SMTP failures up to 3 times with exponential backoff.
    """
    # Insert tracking pixel if configured (only when sending HTML)
    tracking_base_url = os.getenv("TRACKING_BASE_URL", "")
    if tracking_id and tracking_base_url and not force_plain_text:
        html_body = _insert_tracking_pixel(html_body, tracking_id, tracking_base_url)

    if not sender_email or not sender_password:
        print("      [!] Email simulation (Credentials missing)")
        return {"success": True, "simulated": True}

    def _build_message():
        msg = EmailMessage()
        if force_plain_text:
            msg.set_content(html_body)
        else:
            plain_text = _html_to_plain_text(html_body)
            msg.set_content(plain_text)
            msg.add_alternative(html_body, subtype="html")

        msg["Subject"] = subject
        msg["From"] = f"{sender_name} <{sender_email}>"
        msg["To"] = to_address
        msg["Bcc"] = "hello@dedolytics.org"
        # Required by Gmail/Yahoo for bulk senders since Feb 2024
        msg["List-Unsubscribe"] = "<mailto:hello@dedolytics.org?subject=Unsubscribe>"
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
        # Route all replies to one monitored inbox regardless of which sender account was used
        msg["Reply-To"] = "hello@dedolytics.org"
        return msg

    # Hard bounce — no point retrying
    try:
        msg = _build_message()
    except Exception as e:
        return {"success": False, "bounce_status": None, "bounce_message": str(e)}

    max_retries = 3
    for attempt in range(max_retries):
        try:
            server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            return {"success": True}

        except smtplib.SMTPRecipientsRefused as e:
            print(f"      [-] HARD BOUNCE — recipient rejected: {to_address}: {e}")
            return {"success": False, "bounce_status": "hard_bounce", "bounce_message": str(e)}

        except smtplib.SMTPSenderRefused as e:
            print(f"      [-] Sender refused for {to_address}: {e}")
            return {"success": False, "bounce_status": "soft_bounce", "bounce_message": str(e)}

        except smtplib.SMTPDataError as e:
            print(f"      [-] SMTP data error (possible spam filter) for {to_address}: {e}")
            return {"success": False, "bounce_status": "soft_bounce", "bounce_message": str(e)}

        except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, OSError) as e:
            # Transient network/connection error — retry with backoff
            if attempt < max_retries - 1:
                wait = 2**attempt * 5  # 5s, 10s, 20s
                print(f"      [!] Transient SMTP error (attempt {attempt + 1}/{max_retries}), retrying in {wait}s: {e}")
                time.sleep(wait)
            else:
                print(f"      [-] SMTP failed after {max_retries} attempts for {to_address}: {e}")
                return {"success": False, "bounce_status": None, "bounce_message": str(e)}

        except Exception as e:
            print(f"      [-] Failed to send SMTP email to {to_address} from {sender_email}: {e}")
            return {"success": False, "bounce_status": None, "bounce_message": str(e)}

    return {"success": False, "bounce_status": None, "bounce_message": "Max retries exceeded"}


def wrap_infographic_in_email(infographic_html):
    """Wraps the infographic HTML in an email-safe layout with a brief intro line."""
    return f"""
    <html>
      <body style="margin: 0; padding: 0; background-color: #f4f4f4;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4;">
          <tr>
            <td align="center" style="padding: 20px 0;">
              <div style="width: 100%; max-width: 600px; margin: 0 auto; background-color: #ffffff;">
                {infographic_html}
              </div>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """


def _get_valid_accounts():
    """Returns valid email accounts with credentials."""
    valid = [acc for acc in EMAIL_ACCOUNTS if acc["email"] and acc["password"]]
    if not valid:
        print("[!] No valid Google Workspace accounts found in .env. Will run simulation.")
        valid = [{"email": "simulation@example.com", "password": ""}]
    return valid


def _acquire_lock():
    """Acquires OS-level execution lock. Clears stale locks left by crashed runs."""
    import psutil

    lock_file_path = "/tmp/dedolytics_outreach_lock.lock"

    if os.path.exists(lock_file_path):
        live = any(
            "bot4_outreach" in " ".join(p.info.get("cmdline") or [])
            or "daily_pipeline" in " ".join(p.info.get("cmdline") or [])
            for p in psutil.process_iter(["pid", "cmdline"])
            if p.pid != os.getpid()
        )
        if not live:
            print("[!] Stale outreach lock detected — clearing.")
            os.remove(lock_file_path)

    try:
        lock_fd = os.open(lock_file_path, os.O_CREAT | os.O_WRONLY)
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_fd
    except BlockingIOError:
        print("\n[CRITICAL ERROR] The Outreach process is ALREADY RUNNING.")
        print("[!] Terminating immediately to prevent firing duplicate emails.")
        sys.exit(1)


# ─── Initial Outreach ────────────────────────────────────────────────────────


def run_smb_outreach(dry_run: bool = False) -> dict:
    """
    Sends initial infographic emails to leads with status='generated'.
    Returns stats dict.
    """
    print(f"\n--- Starting SMB Outreach Bot at {time.strftime('%Y-%m-%d %H:%M:%S')} ---")

    if not dry_run:
        _acquire_lock()

    ready_leads = db.get_ready_smb_emails()

    if not ready_leads:
        print("[*] No un-emailed infographics ready for dispatch today.")
        return {"sent": 0, "failed": 0}

    print(f"[*] Found {len(ready_leads)} fully generated SMB leads ready to email.")

    valid_accounts = _get_valid_accounts()
    stats = {"sent": 0, "failed": 0}

    for i, lead_row in enumerate(ready_leads):
        lead_id, company_name, category, email, infographic_html, campaign_mode, personalized_pitch = lead_row
        sender_account = valid_accounts[i % len(valid_accounts)]
        sender_email = sender_account["email"]
        sender_password = sender_account["password"]
        # Use lead_id to deterministically pick sender name so follow-ups come from the same "person"
        sender_name = SENDER_NAMES[lead_id % len(SENDER_NAMES)]

        if campaign_mode == "ecom":
            subject = f"quick question about {company_name}"
        else:
            subject = f"had an idea for {company_name}"

        print(f"\n[*] Dispatching to {company_name} ({email}) via {sender_email} as {sender_name}")

        if dry_run:
            print(f"      [DRY RUN] Would send: '{subject}' to {email}")
            stats["sent"] += 1
            continue

        # --- DELIVERABILITY PIVOT: PERSONALIZED PLAIN-TEXT STRATEGY ---
        # The 'personalized_pitch' field contains the AI-generated message.
        # Fallback to a basic template if the pitch is somehow missing.
        pitch_content = lead_row[6]  # personalized_pitch column index

        if pitch_content:
            text_body = pitch_content
        else:
            # Fallback (should not happen if generation cycle ran correctly)
            if campaign_mode == "ecom":
                text_body = f"Hi {company_name},\n\nI was looking at your store and noticed some revenue leakage points. We'll run a first audit for $0.\n\n— {sender_name}"
            else:
                text_body = f"Hi {company_name},\n\nI was looking at your local presence. We'll run a first efficiency audit for $0.\n\n— {sender_name}"

        # Replace generic team sign-off with sender name for reply-thread continuity
        text_body = text_body.replace("— The Dedolytics team", f"— {sender_name}\nDedolytics")
        text_body = text_body.replace("— The Dedolytics Team", f"— {sender_name}\nDedolytics")

        # Add calendar link + unsubscribe footer
        text_body += f"\n\nBook a quick call: {CALENDAR_LINK}"
        text_body += "\n\n---\nTo unsubscribe, reply with 'unsubscribe' or email hello@dedolytics.org"

        final_body = text_body

        # Final safety valve: Detect any bracketed placeholders [Like This]
        import re

        if re.search(r"\[.*?\]", final_body):
            print(f"      [!] CRITICAL SAFETY BLOCK: Placeholder detected in email for {email}. Skipping.")
            db.set_lead_error(lead_id, "Safety Block: Placeholder [ ] detected in pitch")
            stats["failed"] += 1
            continue

        try:
            tracking_id = str(uuid.uuid4())
            result = send_html_email(
                email,
                subject,
                final_body,
                sender_email,
                sender_password,
                sender_name,
                tracking_id=tracking_id,
                force_plain_text=True,
            )
            if result["success"]:
                print(f"      [+] Personalized pitch sent successfully to {email}")
                db.mark_smb_emailed(lead_id)
                db.create_email_event(lead_id, "initial", tracking_id)
                stats["sent"] += 1
            else:
                stats["failed"] += 1
                error_msg = result.get("bounce_message", "SMTP send failed")
                db.set_lead_error(lead_id, error_msg)
        except Exception as e:
            print(f"      [-] Error sending to {email}: {e}")
            stats["failed"] += 1
            db.set_lead_error(lead_id, str(e))

        time.sleep(20)  # Throttled delay

    print(f"\n[*] Initial Outreach Complete: {stats['sent']} sent, {stats['failed']} failed.")
    print(f"--- Finished Outreach at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
    return stats


# ─── Follow-Up Outreach ──────────────────────────────────────────────────────


def run_followup_outreach(dry_run: bool = False) -> dict:
    """
    Sends follow-up emails to leads that were emailed 7+ days ago.
    Max 3 follow-ups per lead, then stops contacting them.
    Returns stats dict.
    """
    print(f"\n--- Starting Follow-Up Outreach at {time.strftime('%Y-%m-%d %H:%M:%S')} ---")

    followup_leads = db.get_followup_leads()

    if not followup_leads:
        print("[*] No follow-ups due today.")
        return {"sent": 0, "failed": 0}

    print(f"[*] Found {len(followup_leads)} leads due for follow-up.")

    valid_accounts = _get_valid_accounts()
    stats = {"sent": 0, "failed": 0}

    for i, (lead_id, company_name, category, email, followup_count, campaign_mode) in enumerate(followup_leads):
        # Pick the right template (0-indexed: followup_count is 0, 1, or 2)
        template_group = ECOM_FOLLOWUP_TEMPLATES if campaign_mode == "ecom" else FOLLOWUP_TEMPLATES
        template_idx = min(followup_count, len(template_group) - 1)
        template = template_group[template_idx]

        sender_account = valid_accounts[i % len(valid_accounts)]
        sender_email = sender_account["email"]
        sender_password = sender_account["password"]
        # Same deterministic name as the initial email so follow-ups feel like the same person
        sender_name = SENDER_NAMES[lead_id % len(SENDER_NAMES)]

        subject = template["subject"].format(company_name=company_name)
        html_body = template["body"].format(
            company_name=company_name,
            category=category.lower() if category else "local",
            calendar_link=CALENDAR_LINK,
            sender_name=sender_name,
        )

        print(f"\n[*] Follow-up #{followup_count + 1} to {company_name} ({email})")

        if dry_run:
            print(f"      [DRY RUN] Would send: '{subject}' to {email}")
            stats["sent"] += 1
            continue

        tracking_id = str(uuid.uuid4())
        event_type = f"followup_{followup_count + 1}"

        try:
            result = send_html_email(
                email,
                subject,
                html_body,
                sender_email,
                sender_password,
                sender_name,
                tracking_id=tracking_id,
                force_plain_text=True,
            )
            if result["success"]:
                print(f"      [+] Follow-up sent to {email}")
                db.mark_followup_sent(lead_id)
                db.create_email_event(lead_id, event_type, tracking_id)
                stats["sent"] += 1
            else:
                stats["failed"] += 1
                error_msg = result.get("bounce_message", f"Follow-up {followup_count + 1} SMTP failed")
                db.set_lead_error(lead_id, error_msg)
                if result.get("bounce_status"):
                    db.create_email_event(lead_id, event_type, tracking_id)
                    db.record_bounce(tracking_id, result["bounce_status"], error_msg)
        except Exception as e:
            print(f"      [-] Error sending follow-up to {email}: {e}")
            stats["failed"] += 1
            db.set_lead_error(lead_id, str(e))

        time.sleep(20)  # Throttled delay

    print(f"\n[*] Follow-Up Complete: {stats['sent']} sent, {stats['failed']} failed.")
    print(f"--- Finished Follow-Ups at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
    return stats


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("[!] DRY RUN MODE — no emails will actually be sent.\n")
    run_smb_outreach(dry_run=dry_run)
    run_followup_outreach(dry_run=dry_run)
