#!/usr/bin/env python3
"""
Dedolytics Scheduler

Single entrypoint — run locally: python crm/scheduler.py
- Daily pipeline: 8:30 AM Eastern every day (DST-aware via APScheduler + pytz)
- Daily report:   9:00 PM Eastern every day
- Reply checker:  every 15 minutes
- On startup: seeds DB with previously-emailed addresses, runs an immediate reply check

Set RUN_NOW=true in env to trigger the pipeline immediately on startup.
"""

import os
import sys
import logging

# Must be first — ensures all relative imports/file paths resolve correctly
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import db
from seed_db import seed_emailed_emails

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("scheduler")

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

EASTERN = pytz.timezone("America/Toronto")


# ─── Jobs ─────────────────────────────────────────────────────────────────────


def run_daily_pipeline():
    logger.info("=" * 55)
    logger.info("  SCHEDULED TRIGGER: Daily Pipeline")
    logger.info("=" * 55)
    try:
        from daily_pipeline import run_pipeline
        run_pipeline()
    except Exception as e:
        logger.error(f"Pipeline crashed: {e}", exc_info=True)


def run_reply_check():
    try:
        from check_replies import run_reply_checker
        run_reply_checker()
    except Exception as e:
        logger.error(f"Reply check failed: {e}", exc_info=True)


def run_daily_report():
    logger.info("=" * 55)
    logger.info("  SCHEDULED TRIGGER: Daily Report (9 PM)")
    logger.info("=" * 55)
    try:
        from daily_report import send_report
        send_report()
    except Exception as e:
        logger.error(f"Daily report failed: {e}", exc_info=True)


# ─── Startup ──────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    logger.info("Dedolytics scheduler starting...")

    # 1. Ensure DB schema is up to date
    db.init_db()

    # 2. Seed previously-emailed addresses so they can never be re-contacted
    seed_emailed_emails()

    # 3. Immediate reply check — catch anything that arrived overnight
    logger.info("Running startup reply check...")
    run_reply_check()

    # 4. If RUN_NOW is set, fire the full pipeline immediately (manual run)
    if os.getenv("RUN_NOW", "").lower() == "true":
        logger.info("RUN_NOW=true — triggering pipeline immediately.")
        run_daily_pipeline()

    # 5. Schedule ongoing jobs
    scheduler = BlockingScheduler(timezone=EASTERN)

    # Daily pipeline at 8:30 AM Eastern (handles EDT/EST automatically)
    scheduler.add_job(
        run_daily_pipeline,
        CronTrigger(hour=8, minute=30, timezone=EASTERN),
        id="daily_pipeline",
        name="Daily Pipeline",
        misfire_grace_time=600,   # Allow up to 10 min late start (e.g. container restart)
        coalesce=True,            # If multiple misfired, only run once
    )

    # Reply checker every 15 minutes
    scheduler.add_job(
        run_reply_check,
        "interval",
        minutes=15,
        id="reply_checker",
        name="Reply Checker",
        misfire_grace_time=120,
        coalesce=True,
    )

    # Daily report at 9 PM Eastern
    scheduler.add_job(
        run_daily_report,
        CronTrigger(hour=21, minute=0, timezone=EASTERN),
        id="daily_report",
        name="Daily Report",
        misfire_grace_time=600,
        coalesce=True,
    )

    logger.info("Pipeline:     daily at 8:30 AM Eastern")
    logger.info("Daily report: daily at 9:00 PM Eastern")
    logger.info("Reply check:  every 15 minutes")
    logger.info("Scheduler running. Waiting for next trigger...")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped cleanly.")
