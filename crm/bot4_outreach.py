"""
Dedolytics SMB Outreach Bot — Initial emails only.

Sends AI-generated personalized plain-text emails to new leads.
Safety: OS-level file lock prevents concurrent execution. DB-level
email_sent='yes' prevents duplicate sends to the same address.
"""

import os
import re
import sys
import time
import uuid
import smtplib
import fcntl
import logging
from email.message import EmailMessage
from dotenv import load_dotenv

import db
from email_validator import validate_email

logger = logging.getLogger(__name__)

load_dotenv()

# ─── SMTP Accounts ────────────────────────────────────────────────────────────
EMAIL_ACCOUNTS = [
    {"email": os.getenv("EMAIL_1_ADDRESS"), "password": os.getenv("EMAIL_1_PASSWORD")},
    {"email": os.getenv("EMAIL_2_ADDRESS"), "password": os.getenv("EMAIL_2_PASSWORD")},
    {"email": os.getenv("EMAIL_3_ADDRESS"), "password": os.getenv("EMAIL_3_PASSWORD")},
]

SENDER_NAMES = ["Paul", "Ed", "Will"]

CALENDAR_LINK = "https://calendar.google.com/calendar/u/0/appointments/schedules/AcZssZ2HePxAUUQzDdORvH9M7ZxCnczzZHTq6w_Ubpjy2STAQTLqYfAgCC9bqNidQSiguEqe1_1kJ_lx"


# ─── Email Sending ─────────────────────────────────────────────────────────────


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
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_body, "html.parser")
            for tag in soup(["style", "script"]):
                tag.decompose()
            plain_text = "\n\n".join(line.strip() for line in soup.get_text(separator="\n").splitlines() if line.strip())
            msg.set_content(plain_text)
            msg.add_alternative(html_body, subtype="html")

        msg["Subject"] = subject
        msg["From"] = f"{sender_name} <{sender_email}>"
        msg["To"] = to_address
        msg["Bcc"] = "hello@dedolytics.org"
        msg["List-Unsubscribe"] = "<mailto:hello@dedolytics.org?subject=Unsubscribe>"
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
        msg["Reply-To"] = "hello@dedolytics.org"
        return msg

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
            if attempt < max_retries - 1:
                wait = 2 ** attempt * 5  # 5s, 10s, 20s
                print(f"      [!] Transient SMTP error (attempt {attempt + 1}/{max_retries}), retrying in {wait}s: {e}")
                time.sleep(wait)
            else:
                print(f"      [-] SMTP failed after {max_retries} attempts for {to_address}: {e}")
                return {"success": False, "bounce_status": None, "bounce_message": str(e)}

        except Exception as e:
            print(f"      [-] Failed to send to {to_address}: {e}")
            return {"success": False, "bounce_status": None, "bounce_message": str(e)}

    return {"success": False, "bounce_status": None, "bounce_message": "Max retries exceeded"}


def _insert_tracking_pixel(html_body, tracking_id, base_url):
    """Inserts a 1x1 invisible tracking pixel into the HTML email body."""
    pixel_url = f"{base_url}/pixel.php?id={tracking_id}"
    pixel_tag = (
        f'<img src="{pixel_url}" width="1" height="1" alt="" '
        f'style="display:block;width:1px;height:1px;border:0;opacity:0;" />'
    )
    lower = html_body.lower()
    idx = lower.rfind("</body>")
    if idx != -1:
        return html_body[:idx] + pixel_tag + html_body[idx:]
    idx = lower.rfind("</html>")
    if idx != -1:
        return html_body[:idx] + pixel_tag + html_body[idx:]
    return html_body + pixel_tag


def _get_valid_accounts():
    """Returns email accounts that have credentials configured."""
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


# ─── Initial Outreach ─────────────────────────────────────────────────────────


def run_smb_outreach(dry_run: bool = False) -> dict:
    """
    Sends initial personalized plain-text emails to leads with status='generated'.
    Returns stats dict.
    """
    print(f"\n--- Starting SMB Outreach Bot at {time.strftime('%Y-%m-%d %H:%M:%S')} ---")

    if not dry_run:
        _acquire_lock()

    ready_leads = db.get_ready_smb_emails()

    if not ready_leads:
        print("[*] No un-emailed leads ready for dispatch today.")
        return {"sent": 0, "failed": 0}

    print(f"[*] Found {len(ready_leads)} leads ready to email.")

    valid_accounts = _get_valid_accounts()
    stats = {"sent": 0, "failed": 0}

    for i, lead_row in enumerate(ready_leads):
        lead_id, company_name, category, email, infographic_html, campaign_mode, personalized_pitch = lead_row
        sender_account = valid_accounts[i % len(valid_accounts)]
        sender_email = sender_account["email"]
        sender_password = sender_account["password"]
        # Deterministic sender name per lead so any future reply thread feels consistent
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

        # Build email body from AI-generated pitch
        pitch_content = personalized_pitch

        if pitch_content:
            text_body = pitch_content
        else:
            # Fallback — should not happen if generation cycle ran correctly
            if campaign_mode == "ecom":
                text_body = f"Hi {company_name},\n\nI was looking at your store and noticed some revenue leakage points. We'll run a first audit for $0.\n\n— {sender_name}"
            else:
                text_body = f"Hi {company_name},\n\nI was looking at your local presence. We'll run a first efficiency audit for $0.\n\n— {sender_name}"

        # Replace generic team sign-off with the sender name
        text_body = re.sub(r"—\s*The Dedolytics [Tt]eam", f"— {sender_name}\nDedolytics", text_body)

        # Append calendar link + unsubscribe footer
        text_body += f"\n\nBook a quick call: {CALENDAR_LINK}"
        text_body += "\n\n---\nTo unsubscribe, reply with 'unsubscribe' or email hello@dedolytics.org"

        # Safety valve: block any email that still contains bracketed placeholders
        if re.search(r"\[.*?\]", text_body):
            print(f"      [!] SAFETY BLOCK: Placeholder detected for {email}. Skipping.")
            db.set_lead_error(lead_id, "Safety Block: Placeholder [ ] detected in pitch")
            stats["failed"] += 1
            continue

        # Pre-send validation (mailcheck.ai — fails open if API unavailable)
        validation = validate_email(email)
        if not validation["valid"]:
            print(f"      [!] VALIDATION BLOCK: {email} — {validation['reason']}. Skipping.")
            db.set_lead_error(lead_id, f"Validation block: {validation['reason']}")
            stats["failed"] += 1
            continue

        tracking_id = str(uuid.uuid4())

        try:
            result = send_html_email(
                email,
                subject,
                text_body,
                sender_email,
                sender_password,
                sender_name,
                tracking_id=tracking_id,
                force_plain_text=True,
            )
            if result["success"]:
                print(f"      [+] Sent successfully to {email}")
                db.mark_smb_emailed(lead_id)
                db.create_email_event(lead_id, "initial", tracking_id)
                stats["sent"] += 1
            else:
                stats["failed"] += 1
                error_msg = result.get("bounce_message", "SMTP send failed")
                db.set_lead_error(lead_id, error_msg)
                # Record bounces in email_events so metrics reflect them
                if result.get("bounce_status"):
                    db.create_email_event(lead_id, "initial", tracking_id)
                    db.record_bounce(tracking_id, result["bounce_status"], error_msg)
        except Exception as e:
            print(f"      [-] Error sending to {email}: {e}")
            stats["failed"] += 1
            db.set_lead_error(lead_id, str(e))

        time.sleep(20)  # Throttled delay between sends

    print(f"\n[*] Outreach Complete: {stats['sent']} sent, {stats['failed']} failed.")
    print(f"--- Finished Outreach at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
    return stats


# ─── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("[!] DRY RUN MODE — no emails will actually be sent.\n")
    run_smb_outreach(dry_run=dry_run)
