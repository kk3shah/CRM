import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

# Senders
ACCOUNTS = [
    ("hello@dedolytics.org", os.getenv("EMAIL_1_PASSWORD"), "Kushal Shah"),
]

# Recipients
RECIPIENTS = [
    "vinlandacreageinc@gmail.com",
    "kshah.cg.rtl@aldogroup.com",  # Also adding the outlook address to see if any tests survive there
]

SAMPLE_HTML = """
<div style="width: 600px; margin: 0 auto; background-color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; padding: 40px; border: 1px solid #eaeaea;">
  <img src="https://www.dedolytics.org/assets/images/logo.jpeg" alt="Dedolytics" width="120" style="margin-bottom:30px;" />
  <h1 style="font-size: 24px; font-weight: 600; color: #111111; margin-bottom: 10px;">We Found Revenue Leakage in Your Brand</h1>
  <p style="font-size: 16px; color: #444444; line-height: 1.5; margin-bottom: 30px;">Based on a quick review of your storefront and ad tech stack, we noticed a few missing pieces specifically typical for the beauty niche. These blind spots usually account for significant hidden efficiency losses.</p>
  
  <div style="border: 1px solid #eaeaea; background-color: #fafafa; padding: 20px; margin-bottom: 15px; border-radius: 4px;">
    <h3 style="font-size: 16px; font-weight: 600; color: #111111; margin: 0 0 5px 0;">Weak AOV Optimization</h3>
    <p style="font-size: 14px; color: #555555; margin: 0;">We didn't detect strong post-purchase upsell paths or dynamic cart minimums.</p>
  </div>
  
  <div style="border: 1px solid #eaeaea; background-color: #fafafa; padding: 20px; margin-bottom: 15px; border-radius: 4px;">
    <h3 style="font-size: 16px; font-weight: 600; color: #111111; margin: 0 0 5px 0;">Missing Bundle Logic</h3>
    <p style="font-size: 14px; color: #555555; margin: 0;">Lack of tiered discounting means you are likely leaving 15-20% of margin on the table for multi-product buyers.</p>
  </div>
  
  <div style="border: 1px solid #eaeaea; background-color: #fafafa; padding: 20px; margin-bottom: 30px; border-radius: 4px;">
    <h3 style="font-size: 16px; font-weight: 600; color: #111111; margin: 0 0 5px 0;">Low Repeat Purchase Triggers</h3>
    <p style="font-size: 14px; color: #555555; margin: 0;">Without robust replenishment flow tracking, lifecycle LTV drops dramatically after month 3.</p>
  </div>

  <div style="background-color: #111111; padding: 25px; border-radius: 4px; margin-bottom: 30px;">
    <h2 style="font-size: 18px; font-weight: 600; color: #ffffff; margin: 0 0 15px 0;">Revenue Recovery Sprint</h2>
    <ul style="list-style-type: none; padding: 0; margin: 0 0 20px 0; color: #cccccc; font-size: 14px; line-height: 1.6;">
      <li>• 2-week deep revenue audit</li>
      <li>• Prioritized roadmap</li>
      <li>• Implementation playbook</li>
    </ul>
    <p style="color: #ffffff; font-size: 16px; font-weight: 600; margin: 0 0 10px 0;">Flat: $1,500</p>
    <p style="color: #999999; font-size: 12px; margin: 0;">If we don't find at least one actionable opportunity, you don't pay.</p>
  </div>
  
  <p style="font-size: 16px; color: #444444; margin-bottom: 20px;">Open to a 15-min call next week?</p>
  <a href="https://calendar.google.com/calendar/u/0/appointments/schedules/AcZssZ2HePxAUUQzDdORvH9M7ZxCnczzZHTq6w_Ubpjy2STAQTLqYfAgCC9bqNidQSiguEqe1_1kJ_lx" style="display: inline-block; background-color: #111111; color: #ffffff; font-size: 14px; font-weight: 600; text-decoration: none; padding: 12px 24px; border-radius: 4px;">Schedule a Call</a>
</div>
"""


def wrap_infographic_in_email(infographic_html):
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


def _html_to_plain_text(html_body):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_body, "html.parser")
    for tag in soup(["style", "script"]):
        tag.decompose()
    text = soup.get_text(separator="\\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\\n\\n".join(lines)


def send_test_case(
    test_num,
    subject,
    sender_email,
    sender_pass,
    sender_name,
    use_bcc=True,
    use_reply_to=True,
    use_list_unsubscribe=True,
    use_pixel=True,
    use_bs4_plain_text=True,
    use_wrapper=True,
):
    html_body = SAMPLE_HTML
    if use_wrapper:
        html_body = wrap_infographic_in_email(html_body)

    if use_pixel:
        pixel_tag = '<img src="https://dedolytics.org/pixel/test_pixel.png" width="1" height="1" alt="" style="display:block;width:1px;height:1px;border:0;opacity:0;" />'
        html_body = html_body + pixel_tag

    plain_text = "Requires HTML viewer."
    if use_bs4_plain_text:
        plain_text = _html_to_plain_text(html_body)

    for recipient in RECIPIENTS:
        msg = EmailMessage()
        msg.set_content(plain_text)
        msg.add_alternative(html_body, subtype="html")

        msg["Subject"] = subject
        msg["From"] = f"{sender_name} <{sender_email}>"
        msg["To"] = recipient

        if use_reply_to:
            msg["Reply-To"] = "hello@dedolytics.org"

        if use_list_unsubscribe:
            msg["List-Unsubscribe"] = "<mailto:unsubscribe@dedolytics.org?subject=Unsubscribe>"

        if use_bcc:
            msg["Bcc"] = "hello@dedolytics.org"

        try:
            server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
            server.login(sender_email, sender_pass)
            server.send_message(msg)
            server.quit()
            print(f"  [+] Sent Test {test_num} to {recipient}")
        except Exception as e:
            print(f"  [-] Failed Test {test_num} to {recipient}: {e}")


def run_tests():
    sender_email, sender_pass, sender_name = ACCOUNTS[0]
    print(f"Executing Spam Trigger Isolation Tests from {sender_email}...\n")

    # Test 1: EXACT match of bot4_outreach
    print("Test 1: Exact Bot 4 Match")
    send_test_case(1, "[Spam Test 1] Exact Bot 4 Logic", sender_email, sender_pass, sender_name)

    # Test 2: No BCC
    print("\\nTest 2: No BCC")
    send_test_case(2, "[Spam Test 2] No BCC Header", sender_email, sender_pass, sender_name, use_bcc=False)

    # Test 3: No Custom Headers
    print("\\nTest 3: No Reply-To or List-Unsubscribe")
    send_test_case(
        3,
        "[Spam Test 3] No Custom Meta Headers",
        sender_email,
        sender_pass,
        sender_name,
        use_reply_to=False,
        use_list_unsubscribe=False,
    )

    # Test 4: No Pixel
    print("\\nTest 4: No Tracking Pixel")
    send_test_case(
        4, "[Spam Test 4] No Tracking Pixel Attached", sender_email, sender_pass, sender_name, use_pixel=False
    )

    # Test 5: No BS4 Plain Text parsing (Use 'Requires HTML viewer' string)
    print("\\nTest 5: No BS4 Plain Text Parsing")
    send_test_case(
        5, "[Spam Test 5] No Plain Text Parser", sender_email, sender_pass, sender_name, use_bs4_plain_text=False
    )

    # Test 6: No Wrapper
    print("\\nTest 6: No HTML Wrapper Table")
    send_test_case(6, "[Spam Test 6] No Wrapper Table", sender_email, sender_pass, sender_name, use_wrapper=False)

    # Test 7: Vanilla (No Headers, No Pixel, No Parsing, No Wrapper)
    print("\\nTest 7: Absolute Vanilla HTML Only")
    send_test_case(
        7,
        "[Spam Test 7] Vanilla HTML Payload",
        sender_email,
        sender_pass,
        sender_name,
        use_bcc=False,
        use_reply_to=False,
        use_list_unsubscribe=False,
        use_pixel=False,
        use_bs4_plain_text=False,
        use_wrapper=False,
    )


if __name__ == "__main__":
    run_tests()
