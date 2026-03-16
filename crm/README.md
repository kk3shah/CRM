# Dedolytics B2B Outreach Pipeline (Revenue Recovery Engine)

A hyper-personalized, fully automated AI sales outreach engine designed for Dedolytics. This Python pipeline targets digitally-native revenue businesses (e-commerce, D2C brands, online retailers), leverages website intelligence to extract buying signals, and uses the Google Gemini LLM to construct bespoke, premium HTML revenue-audit pitches.

## Architecture

The system is composed of an orchestrator (`daily_pipeline.py`) running sequential bots, augmented by a daily reporting and guardrail system:

1.  **Bot 1: Discovery & Enrichment (`smb_scraper.py`)**
    *   Finds and extracts highly targeted online/e-commerce businesses using Google Places API (e.g., "online boutique Toronto", "supplements brand Canada").
    *   Scrapes websites using Playwright to extract contact emails and deep enrichment signals (e-commerce platform, pixel detection, email marketing tools, est. catalog depth).
    *   Applies a strict qualification filter (requires e-commerce, ads, >10 SKUs, non-restaurant/agency).

2.  **Bot 2: Email Generator (`infographic_bot.py`)**
    *   Iterates over all "new" enriched leads.
    *   Prompts Gemini to generate visually premium, revenue-auditing HTML emails featuring A/B Themes (Dark Premium vs. Clean White Consulting).
    *   Injects 3 custom, actionable "Revenue Signals" tailored to their niche and infrastructure.

3.  **Bot 3: SMTP Dispatcher (`smb_outreach.py`)**
    *   Filters the database for un-sent HTML payloads.
    *   Rotates through multiple Google Workspace sender accounts to distribute sending volume.
    *   Executes absolute database blocklisting and strict OS-level (`fcntl`) process locking.

4.  **Bot 4: Analytics & Feedback Loop (`check_replies.py`, `daily_report.py`)**
    *   **Reply Tracker**: Periodically parses IMAP inboxes for positive intent replies and syncs into the `crm_database.db`.
    *   **Daily Analytics**: Emails a comprehensive end-of-day niche performance and cohort summary to logic/ops teams.
    *   **Safety Guardrails**: Automatically pauses the entire orchestration pipeline if lifetime bounce rates exceed 5% or reply rates drop below 0.1%.

## Setup & Dependencies

1.  Clone the repository and initialize the Python virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install google-generativeai python-dotenv duckduckgo-search beautifulsoup4 playwright
    playwright install
    ```

2.  Create a `.env` file in the root directory and populate your credentials:
    ```env
    GEMINI_API_KEY="your_google_ai_studio_key"
    DB_PATH="crm_database.db"

    EMAIL_1_ADDRESS="hello@dedolytics.org"
    EMAIL_1_PASSWORD="your_app_password"

    EMAIL_2_ADDRESS="ops@dedolytics.org"
    EMAIL_2_PASSWORD="your_app_password"

    EMAIL_3_ADDRESS="contact@dedolytics.org"
    EMAIL_3_PASSWORD="your_app_password"
    ```

## Execution

### Master Orchestrator

To run the entire system start-to-finish (Scrape -> Generate -> Dispatch):

```bash
source venv/bin/activate
python crm/run_smb_pipeline.py
```

### Daily Automated Report (Schedule via Cron)
Run the analytical email payload at 9:00 PM:
```bash
0 21 * * * /path/to/venv/bin/python /path/to/Dedolytics/crm/daily_report.py
```

### Reply Tracker (Schedule via Cron)
Polls the mailboxes for new positive signals:
```bash
*/15 * * * * /path/to/venv/bin/python /path/to/Dedolytics/crm/check_replies.py
```

### Emergency Stop
If you need to instantly abort an active run (e.g. rate-limit errors or infinite loops), execute the bash failsafe script to forcefully kill all lingering python processes:
```bash
./kill_all.sh
```

## Testing / Development

To generate a sample infographic and send a test mock-up to your personal inbox without touching the production database:

```bash
source venv/bin/activate
python test_smb_infographics.py your.email@example.com
```

## Author
Developed by the Dedolytics Engineering Team (2026).
