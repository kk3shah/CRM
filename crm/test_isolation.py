import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import db
from bot4_outreach import wrap_infographic_in_email, _html_to_plain_text

os.chdir(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

TARGET_INBOXES = ["kushal@vinlandacreage.com", "kushalkshah02@gmail.com", "kushal.shah@retailogists.com"]


def test_configurations():
    sender_email = os.getenv("EMAIL_1_ADDRESS")
    sender_pass = os.getenv("EMAIL_1_PASSWORD")

    # Get realistic payload
    ready_leads = db.get_ready_smb_emails()
    if ready_leads:
        _, company_name, _, _, infographic_html, campaign_mode = ready_leads[0]
        subject = f"Revenue audit for {company_name}"
        html_payload = wrap_infographic_in_email(infographic_html)
    else:
        subject = "Revenue audit for Your Company"
        html_payload = wrap_infographic_in_email(
            "<div><h2>Custom Analytics for Your Company</h2><p>Here is your revenue audit. We found several areas of leakage we believe can be optimized to increase conversions.</p></div>"
        )

    plain_payload = _html_to_plain_text(html_payload)

    tests = [
        {
            "name": "1. Realistic HTML - NO Custom Headers (No Unsubscribe, No Reply-To)",
            "subject": f"Test 1: {subject}",
            "html": html_payload,
            "plain": plain_payload,
            "headers": False,
        },
        {
            "name": "2. Minimal HTML (Just tags)",
            "subject": "Test 2: Minimal HTML Send",
            "html": "<html><body><p>Hello Kushal,</p><br/><p>This is a minimal <strong>HTML</strong> test without any complex tables.</p></body></html>",
            "plain": "Hello Kushal,\n\nThis is a minimal HTML test without any complex tables.",
            "headers": True,
        },
        {
            "name": "3. Realistic Plain Text ONLY (No HTML Part)",
            "subject": f"Test 3: Plain text of {subject}",
            "html": None,
            "plain": plain_payload,
            "headers": True,
        },
    ]

    print("\n>>> STARTING BINARY ISOLATION TESTS <<<\n")

    for i, test in enumerate(tests):
        print(f"--- Running {test['name']} ---")
        for target in TARGET_INBOXES:
            try:
                msg = EmailMessage()
                msg.set_content(test["plain"])
                if test["html"]:
                    msg.add_alternative(test["html"], subtype="html")

                msg["Subject"] = test["subject"]
                msg["From"] = f"Paul <{sender_email}>"
                msg["To"] = target

                if test["headers"]:
                    msg["Reply-To"] = "hello@dedolytics.org"
                    msg["List-Unsubscribe"] = "<mailto:unsubscribe@dedolytics.org?subject=Unsubscribe>"

                server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
                server.login(sender_email, sender_pass)
                server.send_message(msg)
                server.quit()
                print(f"  [+] SUCCESS -> {target}")
            except Exception as e:
                print(f"  [-] FAILED  -> {target} | Error: {e}")
        print("")


if __name__ == "__main__":
    test_configurations()
