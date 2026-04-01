#!/usr/bin/env python3
"""
Dedolytics Daily Analytical Report & Guardrails

Generates a deep revenue-audit performance report and emails it to the team.
Enforces safety guardrails (bounce rates, reply rates) to pause the pipeline
if metrics fall out of acceptable bands.
"""

import os
import sys
import smtplib
from email.message import EmailMessage
from datetime import datetime
from dotenv import load_dotenv

import db

os.chdir(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

RECIPIENT_EMAIL = "kushalkshah02@gmail.com"
SENDER_EMAIL = os.getenv("EMAIL_1_ADDRESS")
SENDER_PASS = os.getenv("EMAIL_1_PASSWORD")


def _get_start_of_today():
    return datetime.now().strftime("%Y-%m-%d 00:00:00")


def gather_metrics():
    """Gathers all necessary metrics for the report and guardrails."""
    conn = db.get_connection()
    cursor = conn.cursor()
    today_start = _get_start_of_today()

    metrics = {"today": {}, "lifetime": {}}

    # --- TODAY METRICS ---
    cursor.execute("SELECT COUNT(*) FROM email_events WHERE sent_at >= ?", (today_start,))
    metrics["today"]["sent"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM email_events WHERE bounce_status IS NOT NULL AND sent_at >= ?", (today_start,))
    metrics["today"]["bounces"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM email_events WHERE replied = 'yes' AND reply_date >= ?", (today_start,))
    metrics["today"]["replies"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM email_events WHERE positive_reply = 'yes' AND reply_date >= ?", (today_start,))
    metrics["today"]["positive_replies"] = cursor.fetchone()[0]

    # Unique Leads Opened Today (filtering out LTE IPs starting with 78.)
    cursor.execute(
        """
        SELECT COUNT(DISTINCT lead_id)
        FROM email_events 
        WHERE opened = 'yes' AND opened_at >= ? AND (ip_address NOT LIKE '78.%' OR ip_address IS NULL)
    """,
        (today_start,),
    )
    metrics["today"]["opened"] = cursor.fetchone()[0]

    # Unique IPs Today (filtering out LTE IPs)
    cursor.execute(
        """
        SELECT COUNT(DISTINCT ip_address) 
        FROM email_events 
        WHERE opened = 'yes' AND opened_at >= ? AND ip_address IS NOT NULL AND ip_address != '' AND ip_address NOT LIKE '78.%'
    """,
        (today_start,),
    )
    metrics["today"]["unique_ips"] = cursor.fetchone()[0]

    # Bounced Emails List Today
    cursor.execute(
        """
        SELECT l.email, e.bounce_message
        FROM email_events e
        JOIN smb_leads l ON e.lead_id = l.id
        WHERE e.bounce_status IS NOT NULL AND e.sent_at >= ?
    """,
        (today_start,),
    )
    metrics["today"]["bounce_list"] = cursor.fetchall()

    # Best Niche Today (Based on replies, or sends if no replies)
    cursor.execute(
        """
        SELECT l.niche_category, COUNT(*) as cnt 
        FROM email_events e
        JOIN smb_leads l ON e.lead_id = l.id
        WHERE e.replied = 'yes' AND e.reply_date >= ?
        GROUP BY l.niche_category
        ORDER BY cnt DESC LIMIT 1
    """,
        (today_start,),
    )
    best_niche_row = cursor.fetchone()
    metrics["today"]["best_niche"] = best_niche_row[0] if best_niche_row else "N/A"

    # --- LIFETIME METRICS ---
    cursor.execute("SELECT COUNT(*) FROM email_events")
    metrics["lifetime"]["sent"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM email_events WHERE bounce_status IS NOT NULL")
    metrics["lifetime"]["bounces"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM email_events WHERE replied = 'yes'")
    metrics["lifetime"]["replies"] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM email_events WHERE positive_reply = 'yes'")
    metrics["lifetime"]["positive_replies"] = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT l.niche_category, COUNT(*) as cnt 
        FROM email_events e
        JOIN smb_leads l ON e.lead_id = l.id
        WHERE e.replied = 'yes'
        GROUP BY l.niche_category
        ORDER BY cnt DESC LIMIT 1
    """
    )
    best_seg_row = cursor.fetchone()
    metrics["lifetime"]["best_segment"] = best_seg_row[0] if best_seg_row else "N/A"

    cursor.execute(
        """
        SELECT l.variant_id, COUNT(*) as cnt 
        FROM email_events e
        JOIN smb_leads l ON e.lead_id = l.id
        WHERE e.replied = 'yes'
        GROUP BY l.variant_id
        ORDER BY cnt DESC LIMIT 1
    """
    )
    best_variant_row = cursor.fetchone()
    metrics["lifetime"]["best_variant"] = best_variant_row[0] if best_variant_row else "N/A"

    # Lifetime Unique Opens (filtering LTE)
    cursor.execute(
        """
        SELECT COUNT(DISTINCT lead_id)
        FROM email_events 
        WHERE opened = 'yes' AND (ip_address NOT LIKE '78.%' OR ip_address IS NULL)
    """
    )
    metrics["lifetime"]["opened"] = cursor.fetchone()[0]

    # 7-Day Trend
    cursor.execute(
        """
        SELECT DATE(sent_at) as day, COUNT(*) as sent, 
               SUM(CASE WHEN opened = 'yes' THEN 1 ELSE 0 END) as opened
        FROM email_events
        WHERE sent_at >= datetime('now', '-7 days')
        GROUP BY DATE(sent_at)
        ORDER BY day ASC
    """
    )
    metrics["trend"] = [{"day": row[0], "sent": row[1], "opened": row[2]} for row in cursor.fetchall()]

    conn.close()

    # Calculate rates
    t_sent = metrics["today"]["sent"]
    metrics["today"]["reply_rate"] = (metrics["today"]["replies"] / t_sent * 100) if t_sent > 0 else 0
    metrics["today"]["bounce_rate"] = (metrics["today"]["bounces"] / t_sent * 100) if t_sent > 0 else 0
    metrics["today"]["open_rate"] = (metrics["today"].get("opened", 0) / t_sent * 100) if t_sent > 0 else 0

    l_sent = metrics["lifetime"]["sent"]
    metrics["lifetime"]["reply_rate"] = (metrics["lifetime"]["replies"] / l_sent * 100) if l_sent > 0 else 0
    metrics["lifetime"]["bounce_rate"] = (metrics["lifetime"]["bounces"] / l_sent * 100) if l_sent > 0 else 0
    metrics["lifetime"]["open_rate"] = (metrics["lifetime"].get("opened", 0) / l_sent * 100) if l_sent > 0 else 0

    return metrics


def check_guardrails(metrics):
    """
    Evaluates guardrails and pauses pipeline if thresholds are breached.
    Guardrails:
    - Pause if lifetime bounce_rate > 5%
    - Pause if lifetime reply_rate < 0.1% after 1,000 sends
    Returns a list of warnings (empty if all good).
    """
    warnings = []

    # Lifetime Bounce Rate Guardrail
    if metrics["lifetime"]["sent"] > 100 and metrics["lifetime"]["bounce_rate"] > 5.0:
        warnings.append(f"CRITICAL: Bounce rate is {metrics['lifetime']['bounce_rate']:.1f}% (> 5%).")

    # Minimum Viable Reply Rate Guardrail
    if metrics["lifetime"]["sent"] >= 1000 and metrics["lifetime"]["reply_rate"] < 0.1:
        warnings.append(f"CRITICAL: Reply rate is {metrics['lifetime']['reply_rate']:.2f}% (< 0.1% after 1K sends).")

    if warnings:
        db.set_state("pipeline_paused", "yes")

    return warnings


def generate_report_html(metrics, warnings):
    """Generates the HTML email body for the daily report, styled as a BI Dashboard."""
    import urllib.parse

    warning_html = ""
    if warnings:
        warning_items = "".join([f"<li>{w}</li>" for w in warnings])
        warning_html = f"""
        <div style="background-color: #fee2e2; border-left: 4px solid #ef4444; padding: 15px; margin: 20px 30px; border-radius: 4px;">
            <h3 style="color: #b91c1c; margin-top: 0; font-size: 16px;">⚠️ PIPELINE PAUSED: Guardrails Triggered</h3>
            <ul style="color: #b91c1c; font-weight: bold; margin-bottom: 0;">
                {warning_items}
            </ul>
        </div>
        """

    today = metrics["today"]
    lifetime = metrics["lifetime"]
    trend = metrics.get("trend", [])

    # Generate Chart Image URL (QuickChart)
    labels = [d["day"][5:] for d in trend]  # MM-DD
    sents = [d["sent"] for d in trend]
    opens = [d["opened"] for d in trend]

    chart_config = f"""{{
      type: 'bar',
      data: {{
        labels: {labels},
        datasets: [
          {{ label: 'Sent', data: {sents}, backgroundColor: '#cbd5e1', borderRadius: 4 }},
          {{ label: 'Opened', data: {opens}, backgroundColor: '#2563eb', borderRadius: 4 }}
        ]
      }},
      options: {{
        plugins: {{ legend: {{ position: 'bottom' }} }},
        scales: {{ x: {{ grid: {{ display: false }} }}, y: {{ beginAtZero: true }} }}
      }}
    }}"""
    chart_url = f"https://quickchart.io/chart?w=600&h=300&c={urllib.parse.quote(chart_config)}"

    # Format Bounces
    bounce_str = "None!"
    if today.get("bounce_list"):
        bounce_str = "<br>".join(
            [
                f"{e[0]} <span style='color:#ef4444; font-size:11px;'>({e[1][:20]}..)</span>"
                for e in today["bounce_list"]
            ]
        )

    # --- RECENT ENGAGEMENT SECTION ---
    recent_leads_html = ""
    try:
        from db import get_recent_opens
        import requests

        def get_location(ip):
            if (
                not ip
                or ip in ("127.0.0.1", "::1")
                or ip.startswith("192.168.")
                or ip.startswith("10.")
                or ip.startswith("78.")
            ):
                return "Unknown"
            if not hasattr(get_location, "cache"):
                get_location.cache = {}
            if ip in get_location.cache:
                return get_location.cache[ip]
            try:
                resp = requests.get(f"http://ip-api.com/json/{ip}?fields=status,countryCode,city", timeout=3)
                data = resp.json()
                if data.get("status") == "success":
                    loc = f"{data.get('city', '')}, {data.get('countryCode', '')}".strip(", ")
                    get_location.cache[ip] = loc
                    return loc
            except Exception:
                pass
            get_location.cache[ip] = "Unknown"
            return "Unknown"

        recent = get_recent_opens(limit=50)
        # Filter proxies and user LTE IP
        lead_opens = [
            o
            for o in recent
            if "ggpht.com" not in (o.get("user_agent") or "") and not (o.get("ip_address") or "").startswith("78.")
        ][:8]

        if lead_opens:
            rows = ""
            for o in lead_opens:
                ip_addr = o.get("ip_address") or "Unknown"
                loc = get_location(ip_addr)
                # Parse hour from timestamp for cleaner display
                time_only = o["opened_at"].split()[1][:5] if " " in o["opened_at"] else o["opened_at"]

                rows += f"""
                <tr style="border-bottom: 1px solid #f1f5f9;">
                    <td style="padding: 12px 10px; font-size: 13px; font-weight: 500; color:#1e293b;">{o['company_name'][:25]}</td>
                    <td style="padding: 12px 10px; font-size: 12px; color:#64748b;">{time_only}</td>
                    <td style="padding: 12px 10px; font-size: 12px; color:#64748b;">{loc}<br><span style="font-size:10px;color:#cbd5e1;">{ip_addr}</span></td>
                </tr>
                """
            recent_leads_html = f"""
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; margin-top: 20px;">
                <div style="background: #f8fafc; padding: 12px 20px; border-bottom: 1px solid #e2e8f0; font-weight: 600; font-size: 13px; color: #475569;">
                    RECENT LIVE ENGAGEMENT
                </div>
                <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse: collapse;">
                    {rows}
                </table>
            </div>
            """
    except Exception as e:
        print(f"[-] Could not fetch recent lead opens for report: {e}")

    kpi_box_style = "background: #ffffff; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px; flex: 1; min-width: 140px; margin-bottom: 15px;"
    kpi_title_style = "font-size: 11px; color: #64748b; text-transform: uppercase; font-weight: 700; margin: 0 0 8px 0; letter-spacing: 0.5px;"
    kpi_value_style = "font-size: 28px; color: #0f172a; font-weight: 700; margin: 0; line-height: 1;"
    kpi_sub_style = "font-size: 12px; color: #10b981; font-weight: 600; margin: 8px 0 0 0;"

    html = f"""
    <html>
    <head><style>@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');</style></head>
    <body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: 'Inter', -apple-system, sans-serif; color: #333;">
        <div style="max-width: 650px; margin: 20px auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); overflow: hidden;">
            
            <!-- HEADER -->
            <div style="background-color: #0f172a; padding: 30px; text-align: left;">
                <h2 style="margin: 0; color: #ffffff; font-size: 22px; font-weight: 600;">Dedolytics BI Hub</h2>
                <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 14px;">Daily Campaign Analytics ({datetime.now().strftime('%B %d, %Y')})</p>
            </div>
            
            {warning_html}
            
            <div style="padding: 30px;">
                <!-- KPI WIDGETS (TODAY) -->
                <h3 style="font-size: 14px; color: #475569; margin: 0 0 15px 0;">TODAY'S PERFORMANCE</h3>
                
                <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 20px;">
                    <tr>
                        <td width="32%" valign="top" style="{kpi_box_style}">
                            <p style="{kpi_title_style}">Sent</p>
                            <p style="{kpi_value_style}">{today['sent']}</p>
                            <p style="{kpi_sub_style}; color: #64748b;">Delivered Rate: {100 - today['bounce_rate']:.1f}%</p>
                        </td>
                        <td width="2%"></td>
                        <td width="32%" valign="top" style="{kpi_box_style}">
                            <p style="{kpi_title_style}">Unique Opens</p>
                            <p style="{kpi_value_style}">{today.get('opened', 0)}</p>
                            <p style="{kpi_sub_style}; color: #2563eb;">Rate: {today.get('open_rate', 0):.1f}%</p>
                        </td>
                        <td width="2%"></td>
                        <td width="32%" valign="top" style="{kpi_box_style}">
                            <p style="{kpi_title_style}">Replies</p>
                            <p style="{kpi_value_style}">{today['replies']}</p>
                            <p style="{kpi_sub_style}">Rate: {today['reply_rate']:.1f}%</p>
                        </td>
                    </tr>
                </table>

                <!-- CHART SECTION -->
                <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin-bottom: 30px; text-align: center;">
                    <p style="{kpi_title_style}; text-align: left;">7-DAY VOLUME TREND</p>
                    <img src="{chart_url}" width="100%" style="max-width: 550px; height: auto; border: none; display: block; margin: 0 auto;" alt="7 Day Trend Chart" />
                </div>

                <!-- LIFETIME METRICS -->
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin-bottom: 30px;">
                    <h3 style="font-size: 13px; color: #475569; margin: 0 0 15px 0;">LIFETIME PIPELINE STATS</h3>
                    <table width="100%" style="font-size: 13px; color: #334155;">
                        <tr>
                            <td style="padding: 8px 0; border-bottom: 1px dotted #cbd5e1;"><strong>Total Dispatched</strong></td>
                            <td align="right" style="padding: 8px 0; border-bottom: 1px dotted #cbd5e1;">{lifetime['sent']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; border-bottom: 1px dotted #cbd5e1;"><strong>Total Unique Opens</strong></td>
                            <td align="right" style="padding: 8px 0; border-bottom: 1px dotted #cbd5e1;">{lifetime.get('opened', 0)} <span style="color: #2563eb;">({lifetime.get('open_rate', 0):.1f}%)</span></td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; border-bottom: 1px dotted #cbd5e1;"><strong>Total Replies</strong></td>
                            <td align="right" style="padding: 8px 0; border-bottom: 1px dotted #cbd5e1;">{lifetime['replies']} <span style="color: #10b981;">({lifetime.get('reply_rate', 0):.1f}%)</span></td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; border-bottom: 1px dotted #cbd5e1;"><strong>Global Bounce Rate</strong></td>
                            <td align="right" style="padding: 8px 0; border-bottom: 1px dotted #cbd5e1;">{lifetime['bounce_rate']:.1f}%</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Active Variant</strong></td>
                            <td align="right" style="padding: 8px 0;">V-1</td>
                        </tr>
                    </table>
                </div>

                <!-- RECENT ACTIVITY LOG -->
                {recent_leads_html}
                
                <!-- DIAGNOSTICS -->
                <div style="margin-top: 25px; font-size: 11px; color: #64748b; border-top: 1px solid #e2e8f0; padding-top: 15px;">
                    <strong>Bounced Addresses (Today):</strong><br>
                    {bounce_str}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html


def send_report():
    # --- SYNC FIRST ---
    try:
        from metrics import sync_opens

        sync_opens()
    except Exception as e:
        print(f"[-] Automated tracking sync failed: {e}")

    metrics = gather_metrics()
    warnings = check_guardrails(metrics)
    html_body = generate_report_html(metrics, warnings)

    subject = f"Daily Outbound Report - {datetime.now().strftime('%b %d')}"
    if warnings:
        subject = "🚨 ACTION REQUIRED: " + subject

    print(f"[*] Dispatching Daily Report to {RECIPIENT_EMAIL}...")

    if "--dry-run" in sys.argv:
        print("[DRY RUN] Report content:")
        # Just show the start of the HTML to verify structure
        print(html_body[:1000] + "...")
        print("[DRY RUN] Would send to:", RECIPIENT_EMAIL)
        return

    resend_api_key = os.getenv("RESEND_API_KEY")

    if resend_api_key:
        # ── Resend HTTPS API (primary — Railway blocks outbound SMTP) ──────────
        try:
            import resend as resend_lib
            resend_lib.api_key = resend_api_key
            params: resend_lib.Emails.SendParams = {
                "from": f"Dedolytics System <{SENDER_EMAIL}>",
                "to": [RECIPIENT_EMAIL],
                "subject": subject,
                "html": html_body,
            }
            resend_lib.Emails.send(params)
            print("[+] Report sent successfully via Resend.")
        except Exception as e:
            print(f"[-] Resend failed for daily report: {e}")
        return

    # ── SMTP fallback (local dev only) ───────────────────────────────────────
    if not SENDER_EMAIL or not SENDER_PASS:
        print("[-] No RESEND_API_KEY and no SMTP credentials. Cannot send report.")
        return

    try:
        msg = EmailMessage()
        msg.set_content("Please view this email in an HTML-compatible client.")
        msg.add_alternative(html_body, subtype="html")
        msg["Subject"] = subject
        msg["From"] = f"Dedolytics System <{SENDER_EMAIL}>"
        msg["To"] = RECIPIENT_EMAIL

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASS)
        server.send_message(msg)
        server.quit()
        print("[+] Report sent successfully.")
    except Exception as e:
        print(f"[-] Failed to send daily report: {e}")


if __name__ == "__main__":
    send_report()
