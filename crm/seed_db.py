#!/usr/bin/env python3
"""
Dedolytics DB Seeder

On a fresh Railway deployment, seeds the smb_leads table with all previously-contacted
email addresses so they can never be re-emailed. Idempotent — safe to run multiple times.
"""

import os
from dotenv import load_dotenv

os.chdir(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

import db


def seed_emailed_emails() -> int:
    """
    Reads seeded_emails.txt and inserts each address as a minimal 'already emailed'
    record in smb_leads. The UNIQUE constraint on email ensures duplicates are silently
    ignored, making this safe to run on every startup.

    Returns the number of new addresses blocked.
    """
    seed_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seeded_emails.txt")
    if not os.path.exists(seed_file):
        print("[seed] No seeded_emails.txt found — skipping (clean slate).")
        return 0

    conn = db.get_connection()
    cursor = conn.cursor()
    seeded = 0

    with open(seed_file) as f:
        for line in f:
            email = line.strip().lower()
            if not email or "@" not in email:
                continue
            try:
                cursor.execute(
                    """INSERT OR IGNORE INTO smb_leads
                       (company_name, category, email, email_sent, status, source, date_scraped)
                       VALUES (?, 'seeded', ?, 'yes', 'emailed', 'seed', date('now'))""",
                    (email, email),
                )
                if cursor.rowcount > 0:
                    seeded += 1
            except Exception:
                pass

    conn.commit()
    conn.close()
    print(f"[seed] Blocked {seeded} previously-contacted addresses from re-send.")
    return seeded


if __name__ == "__main__":
    db.init_db()
    seed_emailed_emails()
