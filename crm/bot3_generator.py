"""
Dedolytics Infographic Bot — Gemini-powered personalized email generation.

Generates a unique HTML infographic for each lead using their business name,
category, website description, and address. Each email feels hand-crafted
while being fully automated.
"""

import os
import re
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
    instagram_handle=None,
    tiktok_handle=None,
    ad_pixel_platforms=None,
    payment_processors=None,
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
        pixels_label = ad_pixel_platforms if ad_pixel_platforms else ("YES" if ad_pixels_detected == "yes" else "NO")
        context_lines.append(f"Running Paid Ads (Platforms): {pixels_label}")
        context_lines.append(f"Email Marketing Flow: {email_capture_detected.upper()}")
        context_lines.append(f"Est. Product SKU Count: {product_count_estimate}")
        if payment_processors:
            context_lines.append(f"BNPL / Payment Options: {payment_processors}")
        if instagram_handle:
            context_lines.append(f"Instagram: @{instagram_handle}")
        if tiktok_handle:
            context_lines.append(f"TikTok: @{tiktok_handle}")

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
    instagram_handle=None,
    tiktok_handle=None,
    ad_pixel_platforms=None,
    payment_processors=None,
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
        pixels_label = ad_pixel_platforms if ad_pixel_platforms else ("YES" if ad_pixels_detected == "yes" else "NO")
        context_lines.append(f"Running Paid Ads (Platforms): {pixels_label}")
        if payment_processors:
            context_lines.append(f"BNPL / Payment Options: {payment_processors}")
        if instagram_handle:
            context_lines.append(f"Instagram: @{instagram_handle}")
        if tiktok_handle:
            context_lines.append(f"TikTok: @{tiktok_handle}")

    business_context = "\n".join(context_lines)

    prompt = f"""You are writing a short, personal cold email on behalf of Dedolytics — a small business growth consultancy — to the owner of {company_name}.

CONTEXT ABOUT THEM:
{business_context}

WHAT DEDOLYTICS DOES:
We work with {niche_category or category} businesses as a growth partner. We come in, figure out exactly where revenue is leaking or where there's untapped margin, and fix it. We handle the analysis, the recommendations, and the implementation support. The owner doesn't need to understand data — they just need to want results.

THE OFFER:
First month is completely free. No contract, no commitment, no invoice. We do the work. If they see value, we talk about continuing. If not, no hard feelings.

NICHE PAIN POINTS — pick exactly ONE that fits their business and build the email around it:
{niche_hints}

HOW TO WRITE THIS EMAIL:
1. Open with "Hi {company_name}," — no other greeting.
2. In 1-2 sentences, name the specific problem you'd work on in month 1. Use plain language — the kind the owner would use, not consultant jargon.
3. State the offer: first month is free, no contract, no catch.
4. Close with a single low-pressure question: "Worth a quick call this week?"
5. Sign off: "— The Dedolytics team"

STRICT RULES:
- Under 100 words total.
- Plain text only. No bullet points, no headers, no HTML.
- NEVER mention: "dashboard", "analytics platform", "data stack", "AI", "machine learning", "Big Data", "KPIs", "metrics".
- NEVER use bracketed placeholders — not [Your Name], not [City], not [Industry]. Nothing in brackets.
- If you don't know a specific detail, leave it out. Never invent facts.
- Do NOT include a subject line.
- ABSOLUTELY NO BRACKETS [ ] ANYWHERE IN THE RESPONSE.
"""
    return prompt


def validate_and_sanitize_pitch(text, company_name):
    """
    Programmatically cleans AI-generated pitches to remove hallucinations/placeholders.
    Detects patterns like [Your Name], [Industry], etc.
    """
    if not text:
        return None

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
    instagram_handle=None,
    tiktok_handle=None,
    ad_pixel_platforms=None,
    payment_processors=None,
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
        instagram_handle=instagram_handle,
        tiktok_handle=tiktok_handle,
        ad_pixel_platforms=ad_pixel_platforms,
        payment_processors=payment_processors,
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
    instagram_handle=None,
    tiktok_handle=None,
    ad_pixel_platforms=None,
    payment_processors=None,
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
        instagram_handle=instagram_handle,
        tiktok_handle=tiktok_handle,
        ad_pixel_platforms=ad_pixel_platforms,
        payment_processors=payment_processors,
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

                # Read new enrichment fields from extended DB query (indices 14–17)
                instagram_handle = lead[14] if len(lead) > 14 else None
                tiktok_handle = lead[15] if len(lead) > 15 else None
                ad_pixel_platforms = lead[16] if len(lead) > 16 else None
                payment_processors = lead[17] if len(lead) > 17 else None

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
                    instagram_handle=instagram_handle,
                    tiktok_handle=tiktok_handle,
                    ad_pixel_platforms=ad_pixel_platforms,
                    payment_processors=payment_processors,
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
    # Each entry: 2-3 concrete business PROBLEMS the owner recognizes, in plain language
    "Dentist": (
        "patients who accept a consultation but never book the actual treatment, "
        "chairs sitting empty on predictable days of the week because of no-show patterns nobody tracks, "
        "which hygienists have the best patient rebooking rate and why"
    ),
    "Physiotherapy": (
        "patients who drop off after session 2 or 3 before they've seen real results — and the clinic never finds out why, "
        "which referral sources send patients who complete their full plan vs those who ghost, "
        "scheduling gaps that quietly cost the clinic thousands a month"
    ),
    "Restaurants": (
        "menu items that look popular but actually subsidize everything else because the margin is terrible, "
        "which nights and shifts are making money vs quietly losing it once labour is accounted for, "
        "which promotions drove genuinely new revenue vs just moved existing customers to a discounted price"
    ),
    "Landscaping": (
        "job types that look profitable on paper but actually cost more once drive time and crew hours are counted, "
        "seasonal scheduling gaps that leave crews underutilized and margins thin, "
        "maintenance contract renewals that quietly lapse because nobody flags them in time"
    ),
    "Cleaning": (
        "clients that are technically active but cost more to service than they pay — and nobody has done the math, "
        "which services have the best margin and which are basically breakeven, "
        "lapsed clients who left without explanation that could be won back with the right outreach"
    ),
    "Accounting": (
        "clients who take the most hours but generate the least revenue per hour — the classic 80/20 inversion most firms never measure, "
        "which services have the strongest margin and which ones the firm does out of habit, "
        "off-season revenue gaps that could be filled with advisory work the firm is already qualified to do"
    ),
    "Plumbing": (
        "job types where the ticket size looks fine but the actual margin after parts and drive time is thin, "
        "emergency call patterns that could be shifted into more profitable scheduled work, "
        "repeat customers who haven't called back in 12+ months and why"
    ),
    "Gyms": (
        "exactly when members decide to cancel — most gyms lose members at predictable points that nobody is watching, "
        "which class time slots are consistently underbooked and losing money on instructor cost, "
        "members who are one bad experience away from leaving vs those who are deeply sticky"
    ),
    "Fitness": (
        "the drop-off point where new members stop showing up before they've built a habit — and it's usually within the first 3 weeks, "
        "which membership tiers are actually profitable vs which ones the studio offers out of habit, "
        "intro offer conversions — what percentage actually convert to full members and what changes that number"
    ),
    "Online": (
        "products that get added to cart but abandoned at a predictable point in checkout, "
        "which acquisition channels are bringing customers who actually come back vs one-time buyers, "
        "repeat purchase timing — most stores have a natural reorder window they've never identified"
    ),
    "Apparel": (
        "which SKUs have high return rates quietly eating into margin, "
        "dead inventory that's tying up cash and could be moved with targeted promotions, "
        "customers who bought once and never came back — and what they had in common"
    ),
    "Supplements": (
        "subscription customers who are about to cancel before they actually do — there are always early signals, "
        "which product combinations have the best long-term retention and how to bundle around them, "
        "the reorder window — most supplement brands have a predictable repurchase cycle they're not using"
    ),
    "Auto": (
        "job types that look profitable but aren't once technician time and parts markup are properly allocated, "
        "customers who came in once and never returned — identifying them and why they left, "
        "service reminder timing — most shops send reminders too early or too late to convert"
    ),
    "Pet": (
        "clients whose visit frequency is quietly dropping before they fully churn, "
        "which services have the strongest margin vs which ones the practice does mainly out of goodwill, "
        "seasonal appointment gaps that could be filled with proactive outreach"
    ),
    "Beauty": (
        "stylists with high client no-show rates that the owner hasn't noticed yet, "
        "clients who haven't rebooked in 90 days who are almost certainly going to a competitor, "
        "which retail products move because stylists recommend them vs which just sit on the shelf"
    ),
    "Marketing": (
        "clients who are technically paying but are quietly unhappy and about to leave, "
        "which service lines have the strongest margin and which ones the agency takes because they need the revenue, "
        "retainer clients vs project clients — the revenue mix that actually determines agency stability"
    ),
    "Law": (
        "matters that are taking significantly longer than they should — billing efficiency that nobody tracks at the matter level, "
        "client intake that stalls between first contact and retained — where and why prospects drop off, "
        "which practice areas have the best realization rate vs which ones attorneys avoid billing accurately"
    ),
    "Mortgage": (
        "leads that go quiet between pre-approval and application — the drop-off nobody measures, "
        "which referral partners are actually sending closeable deals vs just sending volume, "
        "pipeline timing patterns — deals that stall at specific stages for predictable reasons"
    ),
    "Recruitment": (
        "roles that get filled but then leave within 90 days — the most expensive failure in recruiting, "
        "clients who send consistent volume but have a low offer-acceptance rate that nobody flags, "
        "time-to-fill by role type — where the bottlenecks are and what they cost the agency per day"
    ),
    "Financial": (
        "clients who are technically active but haven't had a meaningful conversation in 6+ months, "
        "which service tiers are growing and which are quietly declining — and what that means for revenue 12 months out, "
        "referral patterns — which clients send more clients and how to systematically activate more of them"
    ),
    "Real Estate": (
        "leads who viewed listings but never progressed — what they had in common and whether they can be re-engaged, "
        "listings that sat too long before a price reduction that was probably predictable from day one, "
        "which lead sources close at the highest rate vs which ones just inflate pipeline numbers"
    ),
    "HVAC": (
        "service agreement renewals that quietly lapse because nobody flags them before the expiry date, "
        "seasonal demand spikes where capacity is the bottleneck and how to get ahead of them, "
        "job margin by type — emergency calls vs installs vs maintenance, and where the real profit is"
    ),
    "Bookkeeping": (
        "clients who take 3x as many hours as they pay for — the profitability problem most bookkeeping firms never measure, "
        "which service types have the strongest realization rate and which ones are priced wrong, "
        "capacity planning — most firms hit a ceiling they don't see coming until they're already overloaded"
    ),
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
        instagram_handle = lead[14] if len(lead) > 14 else None
        tiktok_handle = lead[15] if len(lead) > 15 else None
        ad_pixel_platforms = lead[16] if len(lead) > 16 else None
        payment_processors = lead[17] if len(lead) > 17 else None

        detail = f"{name}"
        if addr:
            detail += f" ({addr})"
        if desc:
            detail += f" — {desc[:200]}"
        if campaign_mode == "ecom":
            if platform:
                detail += f" [Platform: {platform}]"
            if ad_pixel_platforms:
                detail += f" [Ads: {ad_pixel_platforms}]"
            if payment_processors:
                detail += f" [BNPL: {payment_processors}]"
            if instagram_handle:
                detail += f" [IG: @{instagram_handle}]"
            if tiktok_handle:
                detail += f" [TT: @{tiktok_handle}]"
        business_list += f"{idx+1}. {detail}\n"

    niche_hints = NICHE_SCENARIOS.get(
        category, "margin analysis, customer retention mapping, operational efficiency audit"
    )

    prompt = f"""You are writing short, personal cold emails for Dedolytics — a small business growth consultancy — to {category} business owners.

WHAT DEDOLYTICS DOES:
We work with {category} businesses as a growth partner. We figure out exactly where revenue is leaking or where there's untapped margin, and we fix it. The owner doesn't need to understand data — they just need to want results.

THE OFFER:
First month is completely free. No contract, no commitment, no invoice. We do the work. If they see value, we talk about continuing.

{category.upper()} PAIN POINTS — use exactly ONE per email, the one that best fits that specific business:
{niche_hints}

BUSINESSES TO EMAIL:
{business_list}

STRICT RULES:
1. Return EXACTLY {len(leads)} emails separated by '---END_PITCH---'.
2. Start each with "Hi [business name]," — their actual name, never a placeholder.
3. End each with "— The Dedolytics team".
4. Body: 2-3 sentences max. Name the ONE specific problem. State the free month offer. Ask "Worth a quick call this week?"
5. Use plain language — what the owner would say, not consultant jargon.
6. NEVER mention: "dashboard", "analytics", "data stack", "AI", "machine learning", "KPIs".
7. ZERO brackets anywhere — not [Your Name], not [City], nothing in square brackets.
8. No subject line. Plain text. No bullet points. No numbering or labels on the emails themselves.

OUTPUT FORMAT: <email body>---END_PITCH---<email body>---END_PITCH---
"""
    try:
        response = MODEL.generate_content(prompt, request_options={"timeout": 60})
        raw_text = response.text.strip()
        pitches = []
        for p in raw_text.split("---END_PITCH---"):
            p = p.strip()
            if not p:
                continue
            # Strip "Email 1:", "Email 2:", "1.", "1:" etc. that Gemini adds despite instructions
            p = re.sub(r"^(?:email\s*\d+\s*[:\-]?\s*|\d+[\.\):\-]\s*)", "", p, flags=re.IGNORECASE).strip()
            pitches.append(p)
        return pitches
    except Exception as e:
        print(f"      [-] Batch generation failed for {category}: {e}")
        return []


if __name__ == "__main__":
    run_outreach_generation_cycle()
