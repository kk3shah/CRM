import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

# Senders
ACCOUNTS = [
    ("hello@dedolytics.org", os.getenv("EMAIL_1_PASSWORD"), "Kushal Shah"),
    ("ops@dedolytics.org", os.getenv("EMAIL_2_PASSWORD"), "Dedolytics Operations"),
]

# Recipients
RECIPIENTS = [
    "vinlandacreageinc@gmail.com",
    "kushalkshah01@gmail.com",
]


def send_test_email(sender_email, sender_pass, sender_name, subject, text_body, html_body=None, attachment_path=None):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{sender_name} <{sender_email}>"
    # To avoid triggering bulk filters on tests, we send individually

    for recipient in RECIPIENTS:
        test_msg = EmailMessage()
        test_msg["Subject"] = subject
        test_msg["From"] = f"{sender_name} <{sender_email}>"
        test_msg["To"] = recipient

        test_msg.set_content(text_body)

        if html_body:
            test_msg.add_alternative(html_body, subtype="html")

        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as f:
                file_data = f.read()
                file_name = os.path.basename(attachment_path)
            # Use maintype and subtype for a generic binary attachment if needed, or guess based on extension
            if file_name.endswith(".pdf"):
                test_msg.add_attachment(file_data, maintype="application", subtype="pdf", filename=file_name)
            elif file_name.endswith(".png"):
                test_msg.add_attachment(file_data, maintype="image", subtype="png", filename=file_name)
            else:
                test_msg.add_attachment(file_data, maintype="application", subtype="octet-stream", filename=file_name)

        try:
            server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
            server.login(sender_email, sender_pass)
            server.send_message(test_msg)
            server.quit()
            print(f"  [+] Sent '{subject}' to {recipient}")
        except Exception as e:
            print(f"  [-] Failed to send '{subject}' to {recipient}: {e}")


def run_tests():
    # We will just use the 'hello' account for this boundary testing to keep it simple
    sender_email, sender_pass, sender_name = ACCOUNTS[0]
    print(f"Testing sending from {sender_email}...\n")

    # Create dummy image attachment for test 2
    dummy_img = "test_image.png"
    with open(dummy_img, "wb") as f:
        # 1x1 transparent PNG bytes
        f.write(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff\xff\x00\x05\xfe\x02\xfe\xa74\x00\x00\x00\x00\x00\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    tests = [
        {
            "num": 1,
            "subject": "[Test 5] Heavy Formatting Plain Text",
            "text": "Hi Kushal,\n\nWe noticed 3 massive revenue leaks:\n- NO RETARGETING PIXEL\n- HIGH BOUNCE RATE\n- WEAK AOV\n\nFixing these alone is worth $10k/mo.\n\nBook the audit here: https://calendar.google.com/link\nCheck our site: https://dedolytics.org\n\nAre you open for a quick 15 min chat?\n\n— Kushal\nDedolytics Revenue Audit",
            "html": None,
            "attachment": None,
        },
        {
            "num": 2,
            "subject": "[Test 6] Plain Text + Image Attachment + Links",
            "text": "Hi Kushal,\n\nI have attached an image of the dashboard concept we built for you.\n\nLet me know if you want to see the live version: https://dedolytics.org\n\nThanks,\nKushal",
            "html": None,
            "attachment": dummy_img,
        },
        {
            "num": 3,
            "subject": "[Test 7] Dangerously Complex HTML",
            "text": "Requires HTML viewer.",
            "html": "<html><body style='background-color:#0a0a0a; color:#ffffff; font-family:sans-serif;'><div style='padding:20px; border:1px solid #333;'><h2>We Found Revenue Leakage</h2><p>Here are the 3 major issues:</p><ul><li style='color:#ff0000;'>Weak Cart Abandonment</li><li>No AOV Upsell</li><li>Missing Pixel</li></ul><a href='https://dedolytics.org' style='display:inline-block; padding:10px 20px; background:#fff; color:#000;'>Book Call</a></div></body></html>",
            "attachment": None,
        },
        {
            "num": 4,
            "subject": "[Test 8] Minimal HTML + Tracking Pixel",
            "text": "Requires HTML viewer.",
            "html": "<html><body><p>Just checking if you received my previous message regarding the data mapping.</p><img src='https://dedolytics.org/pixel/test_pixel.png' width='1' height='1' style='display:none;'/></body></html>",
            "attachment": None,
        },
    ]

    for t in tests:
        print(f"\nExecuting {t['subject']}")
        send_test_email(sender_email, sender_pass, sender_name, t["subject"], t["text"], t["html"], t["attachment"])

    # Cleanup
    if os.path.exists(dummy_img):
        os.remove(dummy_img)

    print("\nAll boundary tests dispatched.")


if __name__ == "__main__":
    run_tests()
