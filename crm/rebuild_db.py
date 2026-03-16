import db
import sqlite3
import uuid

# Force recreate the db schema completely
if __name__ == "__main__":
    db.init_db()
    conn = db._get_connection() if hasattr(db, "_get_connection") else sqlite3.connect("crm_database.db")
    cursor = conn.cursor()

    test_emails = ["vinlandacreageinc@gmail.com", "kushalkshah01@gmail.com"]
    for email in test_emails:
        try:
            cursor.execute(
                """INSERT INTO smb_leads 
                              (company_name, email, website_url, status, campaign_mode) 
                              VALUES (?, ?, ?, 'new', 'ecom')""",
                (f"Deliverability Test {uuid.uuid4().hex[:4]}", email, "https://dedolytics.org"),
            )
        except sqlite3.IntegrityError:
            cursor.execute("""UPDATE smb_leads SET status='new', infographic_html=NULL WHERE email=?""", (email,))

    conn.commit()
    print("Database ready with 2 pending testing leads in 'new' status.")
