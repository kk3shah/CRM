import sqlite3
from datetime import datetime
import json

def check_analytics():
    conn = sqlite3.connect('crm_database.db', timeout=10)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print(f"=== PIPELINE METRICS AS OF {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    
    try:
        # Get live data from email_events for today
        cursor.execute("""
            SELECT 
                COUNT(*) as total_sent,
                SUM(CASE WHEN opened = 'yes' THEN 1 ELSE 0 END) as total_opened,
                SUM(open_count) as total_opens_recorded
            FROM email_events
            WHERE date(sent_at) = date('now', 'localtime')
        """)
        today = cursor.fetchone()
        
        print("\n[ TODAY'S PERFORMANCE ]")
        if today and today['total_sent'] > 0:
            print(f"Emails Sent Today:  {today['total_sent']}")
            print(f"Total Unique Opens: {today['total_opened']} ({(today['total_opened']/today['total_sent'])*100:.1f}%)")
            print(f"Total Open Events:  {today['total_opens_recorded'] if today['total_opens_recorded'] else 0}")
        else:
            print("No email events recorded for today yet.")
            
        print("\n[ LIFETIME OUTREACH ACTIVITY ]")
        cursor.execute("""
            SELECT 
                COUNT(*) as total_sent,
                SUM(CASE WHEN opened = 'yes' THEN 1 ELSE 0 END) as total_opened,
                SUM(CASE WHEN bounce_status = 'bounced' THEN 1 ELSE 0 END) as total_bounced
            FROM email_events
        """)
        lifetime = cursor.fetchone()
        if lifetime and lifetime['total_sent'] > 0:
            print(f"Total Sent:     {lifetime['total_sent']}")
            print(f"Total Opened:   {lifetime['total_opened']} ({(lifetime['total_opened']/lifetime['total_sent'])*100:.1f}%)")
            print(f"Total Bounced:  {lifetime['total_bounced']} ({(lifetime['total_bounced']/lifetime['total_sent'])*100:.1f}%)")
        else:
            print("No email events recorded historically.")

    except sqlite3.OperationalError as e:
        print(f"Error reading database: {e}")
        
    conn.close()

if __name__ == '__main__':
    check_analytics()
