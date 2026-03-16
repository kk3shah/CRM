#!/usr/bin/env python3
"""
Dedolytics Local Deliverability Test
Sends EXACTLY ONE test email from each of the 3 configured sender accounts
to the 3 target test accounts provided by the user.

Using realistic content to avoid Google's "Test email" spam filters.
"""

import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

import db
from bot4_outreach import wrap_infographic_in_email

os.chdir(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

TARGET_INBOXES = [
    "kushal@vinlandacreage.com",
    "kushalkshah02@gmail.com",
    "kushal.shah@retailogists.com",
]

SENDER_NAMES = ["Paul", "Ed", "Will"]


def _html_to_plain_text(html_body):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_body, "html.parser")
    for tag in soup(["style", "script"]):
        tag.decompose()
    return "\n\n".join(line.strip() for line in soup.get_text(separator="\n").splitlines() if line.strip())


def test_deliverability():
    accounts = [
        {"email": os.getenv("EMAIL_1_ADDRESS"), "password": os.getenv("EMAIL_1_PASSWORD")},
        {"email": os.getenv("EMAIL_2_ADDRESS"), "password": os.getenv("EMAIL_2_PASSWORD")},
    ]

    print(f"\n========================================================")
    print(f"  STARTING DELIVERABILITY / SPAM TEST (REALISTIC PAYLOADS)")
    print(f"========================================================")

    import re

    # Let's get a realistic payload from the database to bypass "Test" spam filters
    ready_leads = db.get_ready_smb_emails()
    if ready_leads:
        _, company_name, _, _, infographic_html, campaign_mode = ready_leads[0]
        if campaign_mode == "ecom":
            subject = f"Revenue leakage audit for {company_name}"
        else:
            subject = f"Unlocking hidden profits at {company_name} (Custom Analytics)"

        # EXPERIMENT: Strip absolutely all links and images from the generated HTML
        # to see if a specific domain is dragging the test into spam.
        clean_html = re.sub(r"<img[^>]*>", "", infographic_html)
        clean_html = re.sub(r'href="[^"]*"', 'href="#"', clean_html)

        html_payload = wrap_infographic_in_email(clean_html)
    else:
        subject = "Unlocking hidden profits at Your Company (Custom Analytics)"
        html_payload = wrap_infographic_in_email(
            "<div><h2>Custom Analytics for Your Company</h2><p>Here is your revenue audit...</p></div>"
        )

    for i, account in enumerate(accounts):
        sender_email = account["email"]
        sender_pass = account["password"]
        sender_name = SENDER_NAMES[i]

        if not sender_email or not sender_pass:
            print(f"[-] Skipping Account {i+1} — Missing credentials in .env")
            continue

        print(f"\n>>> Testing Sender {i+1}: {sender_email} ({sender_name})")

        for target in TARGET_INBOXES:
            try:
                msg = EmailMessage()
                msg.set_content(_html_to_plain_text(html_payload))
                msg.add_alternative(html_payload, subtype="html")

                msg["Subject"] = subject
                msg["From"] = f"{sender_name} <{sender_email}>"
                msg["To"] = target
                msg["Reply-To"] = "hello@dedolytics.org"
                msg["List-Unsubscribe"] = "<mailto:unsubscribe@dedolytics.org?subject=Unsubscribe>"

                server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
                server.login(sender_email, sender_pass)
                server.send_message(msg)
                server.quit()

                print(f"  [+] SUCCESS -> {target}")
            except Exception as e:
                print(f"  [-] FAILED  -> {target} | Error: {e}")

    print(f"\n========================================================")
    print(f"  MANUAL TEST COMPLETE.")
    print(f"  Please check all 3 inboxes for spam placement.")
    print(f"========================================================")


if __name__ == "__main__":
    test_deliverability()
