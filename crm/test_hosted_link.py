import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

SENDER_EMAIL = "hello@dedolytics.org"
SENDER_PASS = os.getenv("EMAIL_1_PASSWORD")
SENDER_NAME = "Kushal Shah"
RECIPIENTS = ["vinlandacreageinc@gmail.com", "kushalkshah01@gmail.com"]


def send_sample():
    subject = "Revenue Audit: Dedolytics"

    # This is exactly what Bot 4 will generate and send. No HTML, no tracking pixels, just pure conversation and a link.
    text_body = """Hi Kushal,

I was looking at the storefront for Dedolytics and noticed a few missing pieces in your ad tech stack specifically typical for your niche. These blind spots usually account for significant hidden efficiency losses (specifically around weak AOV optimization and missing bundle logic).

We ran a quick revenue audit on your brand and mapped out the exact leakage points. 

I've hosted the interactive visual breakdown for you here:
https://busy-spies-rescue.loca.lt/audit_12345.html
(Note: Since this is a temporary testing tunnel, you may need to click 'Continue' to view it)

Are you open for a quick 15-min chat next week to go over this?

— Kushal
Dedolytics Revenue Audit"""

    for recipient in RECIPIENTS:
        msg = EmailMessage()
        msg.set_content(text_body)
        msg["Subject"] = subject
        msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        msg["To"] = recipient

        try:
            server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
            server.login(SENDER_EMAIL, SENDER_PASS)
            server.send_message(msg)
            server.quit()
            print(f"  [+] Sent Sample to {recipient}")
        except Exception as e:
            print(f"  [-] Failed to send to {recipient}: {e}")


if __name__ == "__main__":
    send_sample()
