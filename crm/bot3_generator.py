"""
Dedolytics Infographic Bot — Gemini-powered personalized email generation.

Generates a unique HTML infographic for each lead using their business name,
category, website description, and address. Each email feels hand-crafted
while being fully automated.
"""

import os
import time
import db
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not _GEMINI_API_KEY or _GEMINI_API_KEY == "your-gemini-api-key-here":
    raise EnvironmentError("GEMINI_API_KEY is missing or unset in .env — generation cannot proceed.")
genai.configure(api_key=_GEMINI_API_KEY)
MODEL = genai.GenerativeModel("gemini-2.0-flash")

CALENDAR_LINK = (
    "https://calendar.google.com/calendar/u/0/appointments/schedules/"
    "AcZssZ2HePxAUUQzDdORvH9M7ZxCnczzZHTq6w_Ubpjy2STAQTLqYfAgCC9bqNidQSiguEqe1_1kJ_lx"
)


def _upload_to_ftp(file_name, html_payload):
    """Silently uploads the generated dashboard direct to Hostinger using FTP."""
    import ftplib
    import io

    ftp_host = "82.25.83.169"
    ftp_user = "u864548059"
    ftp_pass = os.getenv("FTP_PASSWORD")

    if not ftp_pass:
        print("      [!] FTP_PASSWORD missing from .env, skipping upload...")
        return False

    try:
        ftp = ftplib.FTP(ftp_host)
        ftp.login(ftp_user, ftp_pass)

        # Navigate to Hostinger's actual web root for dedolytics.org
        ftp.cwd("domains/dedolytics.org/public_html")

        try:
            ftp.cwd("dashboards")
        except Exception:
            ftp.mkd("dashboards")
            ftp.cwd("dashboards")

        bio = io.BytesIO(html_payload.encode("utf-8"))
        ftp.storbinary(f"STOR {file_name}", bio)
        ftp.quit()
        return True

    except Exception as e:
        print(f"      [-] FTP Upload Error: {e}")
        return False


def _build_personalized_prompt(
    company_name,
    category,
    business_description="",
    address="",
    variant_id="A",
    ecommerce_platform=None,
    ad_pixels_detected="no",
    email_capture_detected="no",
    product_count_estimate=0,
    niche_category=None,
    campaign_mode="local",
):
    """
    Builds a highly personalized Gemini prompt using all available context
    about the business, switching strategies based on campaign_mode.
    """

    context_lines = [f"Business Name: {company_name}", f"Industry/Niche: {niche_category or category}"]
    if address:
        context_lines.append(f"Location: {address}")
    if business_description:
        context_lines.append(f"About Them: {business_description}")

    if campaign_mode == "ecom":
        context_lines.append(f"Ecommerce Platform: {ecommerce_platform or 'Unknown'}")
        context_lines.append(f"Running Paid Ads (Pixels Detected): {ad_pixels_detected.upper()}")
        context_lines.append(f"Email Marketing Flow Detected: {email_capture_detected.upper()}")
        context_lines.append(f"Est. Product SKU Count: {product_count_estimate}")

    business_context = "\n".join(context_lines)

    theme_instructions = (
        "Dark premium theme (Deep dark greys/blacks for background (#111111 or #0a0a0a), white/light text, clean modern system fonts, extremely premium aesthetic)."
        if variant_id == "A"
        else "Clean white consulting theme (White background, extremely crisp dark text, minimalist, sharp, professional, light grey subtle borders)."
    )

    if campaign_mode == "ecom":
        # ECOM: High-converting revenue audit layout
        prompt = f"""You are a senior growth engineer writing a highly targeted, visually premium cold email for Dedolytics.

TARGET BUSINESS (E-Commerce):
{business_context}

We are offering a "Revenue Recovery Sprint" — this is NOT a generic analytics pitch. It's a precision-targeted revenue audit.

GENERATE a single self-contained HTML email (no JavaScript, inline CSS only).
Do NOT include any generic AI buzzwords or mention "data stacks". Be confident, direct, and focused on revenue.

DESIGN RULES:
- Width: 600px responsive width, centered.
- Theme: {theme_instructions}
- Fonts: Clean modern system fonts (Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial).
- No heavy graphics. No infographic fluff. 
- Use semantic HTML with inline styles.

EMAIL STRUCTURE:

1. HEADER
   - Dedolytics logo (left-aligned): <img src="https://www.dedolytics.org/assets/images/logo.jpeg" alt="Dedolytics" width="120" style="margin-bottom:20px;" />

2. SECTION 1 — HOOK
   - Headline: "We Found Revenue Leakage in {company_name}"
   - Short 2-sentence intro referencing their specific brand type and niche. Mention signs of leakage based on their platform ({ecommerce_platform}) or ads ({ad_pixels_detected}). 

3. SECTION 2 — 3 REVENUE SIGNALS (Styled Cards)
   - Layout: 3 distinct cards lined up vertically. Each card needs a light border + subtle background (adapted to the theme).
   - Content: Identify 3 specific revenue leakages or opportunities tailored to their '{niche_category or category}' niche. 
   - Examples of specific signals: "Conversion friction", "No post-purchase flow", "Weak AOV optimization", "Missing bundle logic", "Low repeat purchase triggers".
   - Make it sound like an expert analyzed them.

4. SECTION 3 — CLEAR OFFER
   - A distinct highlighted box.
   - Text exactly as follows:
     "Revenue Recovery Sprint"
     • 2-week deep revenue audit
     • Prioritized roadmap
     • Implementation playbook
     Flat: $1,500
     If we don't find at least one actionable opportunity, you don't pay.

5. SECTION 4 — CTA
   - Text: "Open to a 15-min call next week?"
   - Link: <a href="{CALENDAR_LINK}" style="[insert theme-appropriate premium button styling]">Schedule a Call</a>

OUTPUT INSTRUCTIONS:
Raw HTML only. No markdown. No ```html blocks. No explanation text. Just the literal HTML starting with <div and ending with </div>.
"""
    else:
        # LOCAL: Legacy generic local SMB infographic layout
        prompt = f"""You are a senior data analyst and designer at Dedolytics.

TARGET BUSINESS (Local SMB):
{business_context}

We are offering local businesses a custom data analytics dashboard.
GENERATE a single self-contained HTML infographic/dashboard concept (no JavaScript, inline CSS only).

DESIGN RULES:
- Width: 600px responsive width, centered.
- Theme: Clean, modern, high-contrast dashboard aesthetic (White/Grey or Dark Mode).
- Fonts: Clean modern system fonts.
- Must look like a snapshot of a premium analytics tool.

EMAIL STRUCTURE:
1. HEADER: "Custom Analytics Dashboard Concept for {company_name}"
2. METRICS ROW: 3 visual blocks showing simulated hyper-relevant KPI metrics for a '{category}' business (e.g., "Monthly Appointment Volume", "Customer Retention", "LTV").
3. VISUAL: A simulated CSS bar chart or progress bars showing hypothetical growth.
4. FOOTER/CTA: "Want to see your real numbers like this? Book a free data consultation."
   <a href="{CALENDAR_LINK}">Book Consultation</a>

OUTPUT INSTRUCTIONS:
Raw HTML only. No markdown. No ```html blocks. No explanation text. Just the literal HTML starting with <div and ending with </div>.
"""
    return prompt


def _build_pitch_prompt(
    company_name,
    category,
    business_description="",
    address="",
    ecommerce_platform=None,
    ad_pixels_detected="no",
    email_capture_detected="no",
    product_count_estimate=0,
    niche_category=None,
    campaign_mode="local",
):
    """
    Builds a prompt for a highly personalized, plain-text outreach email.
    Focuses on $0 trial and specific high-value business cases.
    """
    context_lines = [f"Business Name: {company_name}", f"Industry/Niche: {niche_category or category}"]
    if address:
        context_lines.append(f"Location: {address}")
    if business_description:
        context_lines.append(f"About Them: {business_description}")

    if campaign_mode == "ecom":
        context_lines.append(f"Ecommerce Platform: {ecommerce_platform or 'Unknown'}")
        context_lines.append(f"Running Paid Ads (Pixels Detected): {ad_pixels_detected.upper()}")

    business_context = "\n".join(context_lines)

    prompt = f"""You are a senior data consultant at Dedolytics. You are writing a PERSONAL, one-to-one cold email to the owner of {company_name}.

GOAL: Get them to reply.
OFFER: First month (or first project) is completely $0. If they like the results, you can talk about a future partnership.

TARGET BUSINESS CONTEXT:
{business_context}

INSTRUCTIONS:
1. Write in plain text. NO HTML. NO generic greeting like "Dear Team". Use "Hi {company_name}" or similar.
2. Mention 2-3 specific, high-value business scenarios tailored to their niche ({niche_category or category}).
   - Examples for Convenience Stores: inventory audits to stop shrinkage, aisle/shelf optimization for higher margin snacks, POS pricing optimization, or delivery route efficiency.
   - Examples for E-commerce: abandoned cart recovery audits, CAC/LTV breakdown by channel, or inventory forecasting.
   - Examples for Local Services: booking leak analysis, local search intent mapping, or customer lifetime value segmentation.
3. Be specific. Use "real world" terms, not "Big Data" or "AI Models".
4. Pitch: "We'll build you a custom dashboard or run a specific audit (like [scenario]) for $0. No risk. I just want to show you how much margin you're leaving on the table."
5. Tone: Low-pressure, helpful, and expert. Like a neighbor who happens to be a data genius.
6. Keep it concise (under 150 words).

7. CRITICAL: Strictly forbid ALL bracketed placeholders. Do NOT include phrases like "[Your Name]", "[Industry]", or "[City]".
8. DO NOT invent contact names or personal details. 
9. Use the business name "{company_name}" directly if needed, never a placeholder.
10. If you do not know a piece of information, omit the sentence entirely rather than using a placeholder.

OUTPUT REQUIREMENTS:
- Start DIRECTLY with the greeting (e.g., "Hi {company_name},").
- Just the email body text. 
- NO subject line. 
- NO placeholders like [Your Name] or [My Name]. 
- Use "— The Dedolytics team" as the sign-off.
- DO NOT invent a name for yourself.
- ABSOLUTELY NO BRACKETS [ ] IN THE ENTIRE RESPONSE.
"""
    return prompt


def validate_and_sanitize_pitch(text, company_name):
    """
    Programmatically cleans AI-generated pitches to remove hallucinations/placeholders.
    Detects patterns like [Your Name], [Industry], etc.
    """
    if not text:
        return None

    import re

    # 1. Check for any bracketed placeholders [Like This]
    placeholders = re.findall(r"\[.*?\]", text)
    if placeholders:
        print(f"      [!] Sanitizing placeholders found in pitch: {placeholders}")
        # Case-insensitive replacements for name/company placeholders
        text = re.sub(r"\[(?:my|your|consultant|sender|rep)\s*name\]", "The Dedolytics team", text, flags=re.IGNORECASE)
        text = re.sub(r"\[company\s*name\]", company_name, text, flags=re.IGNORECASE)
        text = re.sub(r"\[company\]", company_name, text, flags=re.IGNORECASE)

        # Final safety: If any brackets remain, this pitch is unsafe
        if "[" in text or "]" in text:
            print("      [!] CRITICAL: Pitch still contains brackets after sanitization. Blocking.")
            return None

    return text


def generate_personalized_pitch(
    company_name,
    category,
    business_description="",
    address="",
    ecommerce_platform=None,
    ad_pixels_detected="no",
    email_capture_detected="no",
    product_count_estimate=0,
    niche_category=None,
    campaign_mode="local",
):
    """Generates a personalized plain-text pitch using Gemini."""
    prompt = _build_pitch_prompt(
        company_name,
        category,
        business_description,
        address,
        ecommerce_platform,
        ad_pixels_detected,
        email_capture_detected,
        product_count_estimate,
        niche_category,
        campaign_mode,
    )

    try:
        response = MODEL.generate_content(prompt, request_options={"timeout": 60})
        text = response.text.strip()
        return validate_and_sanitize_pitch(text, company_name)
    except Exception as e:
        print(f"      [-] Gemini failed for {company_name}: {e}")
        return None


def generate_smb_infographic_html(
    company_name,
    category,
    business_description="",
    address="",
    variant_id="A",
    ecommerce_platform=None,
    ad_pixels_detected="no",
    email_capture_detected="no",
    product_count_estimate=0,
    niche_category=None,
    campaign_mode="local",
):
    """
    Generates a personalized HTML infographic for a specific business using Gemini.
    """
    prompt = _build_personalized_prompt(
        company_name,
        category,
        business_description,
        address,
        variant_id,
        ecommerce_platform,
        ad_pixels_detected,
        email_capture_detected,
        product_count_estimate,
        niche_category,
        campaign_mode,
    )

    try:
        response = MODEL.generate_content(prompt, request_options={"timeout": 90})
        text = response.text.strip()

        # Clean up markdown blocks if Gemini wraps them
        if text.startswith("```html"):
            text = text.replace("```html", "", 1)
        if text.startswith("```"):
            text = text.replace("```", "", 1)
        if text.endswith("```"):
            text = text[: text.rfind("```")]
        text = text.strip()

        # Basic validation — must contain HTML
        if "<div" not in text.lower():
            print(f"      [-] Gemini returned non-HTML for {company_name}")
            return None

        return text
    except Exception as e:
        print(f"      [-] Gemini failed for {company_name}: {e}")
        return None


def run_outreach_generation_cycle():
    """Reads pending SMB leads and generates content in optimized batches by category."""
    print(f"\n--- Starting Outreach Generation Bot at {time.strftime('%Y-%m-%d %H:%M:%S')} ---")

    pending_leads = db.get_pending_smb_infographics()
    if not pending_leads:
        print("[*] No new SMB leads require generation. Exiting.")
        return

    print(f"[*] Found {len(pending_leads)} businesses awaiting personalized content.\n")

    # Group leads by category/niche for batch processing
    from collections import defaultdict

    category_groups = defaultdict(list)
    for lead in pending_leads:
        cat = lead[12] or lead[2]  # niche_category or category
        category_groups[cat].append(lead)

    success_count = 0
    fail_count = 0

    for cat, leads in category_groups.items():
        print(f"[*] Processing category: {cat} ({len(leads)} leads)")

        # Process in sub-batches of 5 to stay within token/output limits and ensure quality
        sub_batch_size = 5
        for i in range(0, len(leads), sub_batch_size):
            batch = leads[i : i + sub_batch_size]

            # 1. Generate Batch Pitches
            pitches = _generate_batched_pitches(batch, cat)

            # 2. Process results
            for idx, lead in enumerate(batch):
                lead_id = lead[0]
                company_name = lead[1]

                # Check if we have a pitch for this index
                pitch_text = pitches[idx] if idx < len(pitches) else None

                # Still generate legacy infographic (one by one for now as it's HTML heavy)
                html_payload = generate_smb_infographic_html(
                    company_name=company_name,
                    category=lead[2],
                    business_description=lead[5] or "",
                    address=lead[6] or "",
                    variant_id=lead[7] or "A",
                    ecommerce_platform=lead[8],
                    ad_pixels_detected=lead[9],
                    email_capture_detected=lead[10],
                    product_count_estimate=lead[11],
                    niche_category=lead[12],
                    campaign_mode=lead[13],
                )

                if pitch_text:
                    # Pitch is the primary deliverable (plain-text strategy).
                    # Save it immediately so the lead moves to 'generated' status
                    # and is ready to email even if the infographic FTP upload fails.
                    db.save_personalized_pitch(lead_id, pitch_text)

                    # Best-effort: also generate + upload infographic for future use
                    if html_payload:
                        import uuid as _uuid

                        file_name = f"audit_{lead_id}_{_uuid.uuid4().hex[:8]}.html"
                        full_html = (
                            html_payload
                            + """
<div style="width:100%;max-width:600px;margin:30px auto 0;padding:20px 0;border-top:1px solid #e0e0e0;text-align:center;font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <a href="https://www.dedolytics.org" style="display:inline-block;padding:12px 28px;background-color:#111111;color:#ffffff;text-decoration:none;font-weight:600;border-radius:6px;font-size:14px;letter-spacing:0.5px;">Visit Dedolytics &rarr;</a>
  <p style="color:#999999;font-size:12px;margin-top:14px;">&copy; 2026 Dedolytics &mdash; Data &amp; AI for Growing Businesses</p>
</div>
"""
                        )
                        if _upload_to_ftp(file_name, full_html):
                            public_url = f"https://dedolytics.org/dashboards/{file_name}"
                            db.save_smb_infographic(lead_id, public_url)

                    success_count += 1
                else:
                    fail_count += 1
                    db.set_lead_error(lead_id, "Pitch generation failed")

            time.sleep(2)  # Anti-throttle pause between sub-batches

    print(f"\n[*] Generation Cycle Complete.")
    print(f"    Success: {success_count} | Failed: {fail_count}")


NICHE_SCENARIOS = {
    "Dentist": "appointment no-show rate analysis, treatment acceptance funnel, patient reactivation segmentation, chair utilization optimization",
    "Physiotherapy": "appointment fill-rate tracking, patient drop-off analysis after initial visit, referral source ROI, rebooking rate optimization",
    "Restaurants": "menu profitability by item, labor cost vs revenue by shift, table turn optimization, promo ROI (e.g. happy hour lift)",
    "Landscaping": "job margin by service type, crew utilization, seasonal demand forecasting, upsell conversion on maintenance contracts",
    "Cleaning": "booking funnel drop-off, client lifetime value segmentation, re-engagement of lapsed clients, service profitability breakdown",
    "Accounting": "client churn prediction, service mix profitability, referral source tracking, off-season revenue analysis",
    "Plumbing": "job ticket average analysis, dispatch efficiency, emergency call conversion rate, repeat customer identification",
    "Gyms": "member churn prediction, class fill-rate by time slot, personal training upsell conversion, LTV by acquisition channel",
    "Fitness": "class attendance trends, membership tier profitability, intro offer to paid conversion, drop-off timing analysis",
    "Online": "abandoned cart recovery, CAC by channel, LTV segmentation, email flow performance",
    "Apparel": "return rate by SKU, size/colour dead inventory, ad spend ROI by channel, repeat purchase triggers",
    "Supplements": "subscription churn analysis, bundle attach rate, reorder timing optimization, ad attribution by SKU",
    "Auto": "technician utilization, parts margin by job type, repeat customer identification, service reminder conversion",
    "Pet": "appointment rebooking rate, product attachment per visit, seasonal demand, client lifetime spend segmentation",
    "Beauty": "stylist utilization, appointment no-show rate, rebooking trigger analysis, retail product attach rate",
    # New high-converting B2B niches
    "Marketing": "campaign ROI by channel, client retention analytics, lead attribution, monthly reporting automation",
    "Law": "billing efficiency by matter type, client intake conversion, referral source tracking, utilization rate by attorney",
    "Mortgage": "lead-to-close conversion funnel, referral partner ROI, pipeline velocity, lost deal analysis",
    "Recruitment": "time-to-fill by role type, placement rate by client, candidate source quality, revenue per recruiter",
    "Financial": "client retention analysis, AUM growth attribution, service tier profitability, referral network mapping",
    "Real Estate": "lead-to-showing conversion, listing time vs price reduction correlation, agent productivity, referral source ROI",
    "HVAC": "seasonal demand forecasting, technician utilization, service agreement renewal rate, parts margin by job",
    "Bookkeeping": "client profitability by service mix, capacity utilization, referral source tracking, seasonal workload patterns",
}


def _generate_batched_pitches(leads, category):
    """Generates multiple pitches in a single Gemini call with full business context."""
    business_list = ""
    for idx, lead in enumerate(leads):
        name = lead[1]
        desc = lead[5] or ""
        addr = lead[6] or ""
        platform = lead[8] or ""
        campaign_mode = lead[13] or "local"
        detail = f"{name}"
        if addr:
            detail += f" ({addr})"
        if desc:
            detail += f" — {desc[:200]}"
        if campaign_mode == "ecom" and platform:
            detail += f" [Platform: {platform}]"
        business_list += f"{idx+1}. {detail}\n"

    niche_hints = NICHE_SCENARIOS.get(
        category, "margin analysis, customer retention mapping, operational efficiency audit"
    )

    prompt = f"""You are a senior data consultant at Dedolytics writing cold outreach emails to {category} business owners.

GOAL: Get a reply. Offer: First project is $0. No commitment.
TONE: Conversational, expert, like a smart friend — NOT a sales pitch.
LENGTH: Under 120 words per email.

NICHE-SPECIFIC ANGLES FOR {category}:
{niche_hints}

BUSINESSES:
{business_list}

STRICT RULES:
1. Return EXACTLY {len(leads)} emails separated by '---END_PITCH---'.
2. Start each with "Hi [business name]," — use their actual name, never a placeholder.
3. End each with "— The Dedolytics team" (no other sign-off).
4. Pick 1-2 of the niche angles above that fit their specific description. Be concrete, not generic.
5. ZERO bracketed placeholders — not [Your Name], not [City], not [Industry]. Nothing in brackets.
6. No subject line. Plain text only. No markdown.
7. If you don't know a specific detail, leave it out — never invent facts.

OUTPUT:
Email 1
---END_PITCH---
Email 2
---END_PITCH---
"""
    try:
        response = MODEL.generate_content(prompt, request_options={"timeout": 60})
        raw_text = response.text.strip()
        pitches = [p.strip() for p in raw_text.split("---END_PITCH---") if p.strip()]
        return pitches
    except Exception as e:
        print(f"      [-] Batch generation failed for {category}: {e}")
        return []


if __name__ == "__main__":
    run_outreach_generation_cycle()
