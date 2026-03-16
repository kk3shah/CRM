#!/usr/bin/env python3
"""
Dedolytics Reply Tracker

Connects to the configured email accounts via IMAP, searches for unseen replies,
matches the sender's email against our database, classifies the reply for positive
intent, and updates our tracking metrics.
"""

import os
import imaplib
import email
import re
from email.header import decode_header
from dotenv import load_dotenv

import db

# Ensure we're running from the crm/ directory limits
os.chdir(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

EMAIL_ACCOUNTS = [
    {"email": os.getenv("EMAIL_1_ADDRESS"), "password": os.getenv("EMAIL_1_PASSWORD")},
    {"email": os.getenv("EMAIL_2_ADDRESS"), "password": os.getenv("EMAIL_2_PASSWORD")},
    {"email": os.getenv("EMAIL_3_ADDRESS"), "password": os.getenv("EMAIL_3_PASSWORD")},
    # Reply-To inbox — all cold email replies land here first
    {"email": os.getenv("EMAIL_REPLY_ADDRESS"), "password": os.getenv("EMAIL_REPLY_PASSWORD")},
]

POSITIVE_KEYWORDS = [
    # Direct agreement
    "yes",
    "sure",
    "absolutely",
    "definitely",
    "sounds good",
    "sounds great",
    # Interest signals
    "interested",
    "tell me more",
    "learn more",
    "more info",
    "more information",
    "curious",
    "intrigued",
    "sounds interesting",
    "could work",
    "this could work",
    # Meeting / availability
    "let's talk",
    "let's chat",
    "let's connect",
    "book",
    "schedule",
    "set up a call",
    "when are you",
    "available",
    "good time",
    "next week",
    "this week",
    # Action intent
    "call",
    "meeting",
    "demo",
    "chat",
    "discuss",
    "follow up",
    "follow-up",
    # Pricing / scope signals (warm leads)
    "pricing",
    "price",
    "cost",
    "how much",
    "what do you charge",
    "rates",
    "free trial",
    "pilot",
    "audit",
    "proposal",
]


def _clean_email(email_str):
    """Extracts the raw email address from a string like 'Name <email@domain.com>'"""
    match = re.search(r"<([^>]+)>", email_str)
    return match.group(1).lower().strip() if match else email_str.lower().strip()


def _get_plain_text(msg):
    """Extracts plain text body from the email message."""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_dispos = str(part.get("Content-Disposition"))
            if content_type == "text/plain" and "attachment" not in content_dispos:
                charset = part.get_content_charset()
                if charset:
                    return part.get_payload(decode=True).decode(charset, errors="ignore")
                return part.get_payload(decode=True).decode(errors="ignore")
    else:
        content_type = msg.get_content_type()
        if content_type == "text/plain":
            charset = msg.get_content_charset()
            if charset:
                return msg.get_payload(decode=True).decode(charset, errors="ignore")
            return msg.get_payload(decode=True).decode(errors="ignore")
    return ""


_AUTO_REPLY_SIGNALS = [
    "out of office",
    "out of the office",
    "on vacation",
    "on leave",
    "away from",
    "automatic reply",
    "auto-reply",
    "auto reply",
    "will be back",
    "i am away",
    "i'm away",
    "currently unavailable",
    "do not reply",
    "do-not-reply",
    "noreply",
]


def _is_auto_reply(body_text):
    """Returns True if the email looks like an auto-reply / OOO message."""
    body_lower = body_text.lower()
    return any(signal in body_lower for signal in _AUTO_REPLY_SIGNALS)


def _is_positive(body_text):
    """Returns True if the reply shows genuine buying interest."""
    if _is_auto_reply(body_text):
        return False
    body_lower = body_text.lower()
    for kw in POSITIVE_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", body_lower):
            return True
    return False


def check_account_replies(account):
    """Checks a specific IMAP account for replies."""
    addr = account["email"]
    password = account["password"]

    if not addr or not password:
        return 0, 0

    print(f"[*] Checking INBOX for {addr}...")

    replies_found = 0
    positive_found = 0

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(addr, password)
        mail.select("inbox")

        # Search for all unread messages
        status, messages = mail.search(None, "UNSEEN")
        if status != "OK" or not messages[0]:
            print(f"    No new unread messages.")
            mail.logout()
            return 0, 0

        for msg_num in messages[0].split():
            status, data = mail.fetch(msg_num, "(RFC822)")
            if status != "OK":
                continue

            msg = email.message_from_bytes(data[0][1])
            sender = msg.get("From")
            sender_email = _clean_email(sender) if sender else ""

            # Skip automated bounces and mailer daemons
            if "mailer-daemon" in sender_email or "bounce" in sender_email:
                continue

            body_text = _get_plain_text(msg)

            # Skip auto-replies and OOO messages — they are not genuine replies
            if _is_auto_reply(body_text):
                continue

            # Record a reply only if sender is one of our scraped SMBs
            is_pos = _is_positive(body_text)
            tracked = db.record_reply(sender_email, is_positive=is_pos)

            if tracked:
                print(f"    [+] Logged reply from {sender_email} (Positive: {is_pos})")
                replies_found += 1
                if is_pos:
                    positive_found += 1

        mail.logout()
    except Exception as e:
        print(f"    [-] Error checking IMAP for {addr}: {e}")

    return replies_found, positive_found


def run_reply_checker():
    print("--- Starting Reply Tracker ---")
    total_replies = 0
    total_positive = 0

    for acc in EMAIL_ACCOUNTS:
        r, p = check_account_replies(acc)
        total_replies += r
        total_positive += p

    print(f"--- Finished Reply Tracker ---")
    print(f"Total New Replies Tracked: {total_replies}")
    print(f"Total Positive Replies: {total_positive}")


if __name__ == "__main__":
    run_reply_checker()
