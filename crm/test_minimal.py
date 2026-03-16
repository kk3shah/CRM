import os
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid, formatdate
from dotenv import load_dotenv

os.chdir(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

TARGET_INBOXES = [
    "kushal@vinlandacreage.com",
    "kushalkshah02@gmail.com",
    "kushal.shah@retailogists.com",
]


def test_minimal():
    accounts = [
        {"email": os.getenv("EMAIL_1_ADDRESS"), "password": os.getenv("EMAIL_1_PASSWORD"), "name": "Paul"},
        {"email": os.getenv("EMAIL_2_ADDRESS"), "password": os.getenv("EMAIL_2_PASSWORD"), "name": "Ed"},
    ]

    print("\n>>> Testing Minimal Plain Text Send")
    for account in accounts:
        sender_email = account["email"]
        sender_pass = account["password"]
        sender_name = account["name"]

        print(f"\n--- Testing from {sender_email} ---")
        for target in TARGET_INBOXES:
            try:
                msg = EmailMessage()
                msg.set_content(
                    "Hi Kushal,\n\nI hope you are having a great week. I wanted to touch base regarding the onboarding agenda we discussed yesterday.\n\nBest,\n"
                    + sender_name
                )

                msg["Subject"] = "Follow up on yesterday's meeting"
                msg["From"] = f"{sender_name} <{sender_email}>"
                msg["To"] = target
                msg["Date"] = formatdate(localtime=True)
                msg["Message-ID"] = make_msgid(domain="dedolytics.org")

                server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
                server.login(sender_email, sender_pass)
                server.send_message(msg)
                server.quit()
                print(f"  [+] SUCCESS -> {target}")
            except Exception as e:
                print(f"  [-] FAILED  -> {target} | Error: {e}")


if __name__ == "__main__":
    test_minimal()
