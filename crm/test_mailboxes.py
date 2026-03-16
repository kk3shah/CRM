import os, smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

TO = "kk3shah@uwaterloo.ca"

ACCOUNTS = [
    {"email": os.getenv("EMAIL_1_ADDRESS"), "password": os.getenv("EMAIL_1_PASSWORD"), "name": "Paul"},
    {"email": os.getenv("EMAIL_2_ADDRESS"), "password": os.getenv("EMAIL_2_PASSWORD"), "name": "Ed"},
    {"email": os.getenv("EMAIL_3_ADDRESS"), "password": os.getenv("EMAIL_3_PASSWORD"), "name": "Will"},
]

html_body = """
<html><body style="font-family:Arial,sans-serif;padding:20px;">
  <h2>Test Email from Dedolytics</h2>
  <p>Hey Kushal,</p>
  <p>This is a test email sent from the Dedolytics SMB outreach pipeline to verify SMTP connectivity on this mailbox.</p>
  <p>If you're seeing this, the mailbox is working correctly.</p>
  <br><p>— Dedolytics Engineering</p>
</body></html>
"""

for i, acc in enumerate(ACCOUNTS, 1):
    if not acc["email"] or not acc["password"]:
        print(f"[{i}] SKIP — EMAIL_{i}_ADDRESS or EMAIL_{i}_PASSWORD not set in .env")
        continue

    print(f"[{i}] Sending from {acc['email']} ({acc['name']}) → {TO} ...")
    try:
        msg = EmailMessage()
        msg.set_content("Please enable HTML to view this email.")
        msg.add_alternative(html_body, subtype="html")
        msg["Subject"] = f"[Mailbox {i} Test] Dedolytics SMTP Check"
        msg["From"] = f"{acc['name']} <{acc['email']}>"
        msg["To"] = TO
        msg["Bcc"] = "hello@dedolytics.org"

        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(acc["email"], acc["password"])
        server.send_message(msg)
        server.quit()
        print(f"    [+] SUCCESS")
    except Exception as e:
        print(f"    [-] FAILED: {e}")
