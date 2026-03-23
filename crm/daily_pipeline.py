#!/usr/bin/env python3
"""
Dedolytics Daily Pipeline Orchestrator.

Runs the full lead acquisition → email generation → outreach pipeline
sequentially with comprehensive error handling. Designed to be triggered
once daily at 8:30 AM EST via launchd.

Stages:
  1. SCRAPE  — Google Places API → Playwright email extraction (max 1 hr)
  2. GENERATE — Gemini AI infographic generation for new leads (max 1 hr)
  3. SEND    — Initial emails + follow-up emails
  4. METRICS — Sync open tracking data + daily metrics summary

Usage:
  python daily_pipeline.py              # Full run (sends real emails)
  python daily_pipeline.py --dry-run    # Full run but emails are simulated
"""

import os
import sys
import time
import fcntl
import logging
from datetime import datetime
from dotenv import load_dotenv

# Ensure we're running from the crm/ directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

# ─── Logging Setup ────────────────────────────────────────────────────────────

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

log_filename = os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y-%m-%d')}.log")

# Log to both file and stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filename, mode="a"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("pipeline")

# ─── Pipeline Lock ────────────────────────────────────────────────────────────

LOCK_FILE = "/tmp/dedolytics_pipeline.lock"


def acquire_pipeline_lock():
    """Prevents two pipeline instances from running simultaneously.
    Clears stale lock files left by crashed/killed previous runs."""
    import psutil

    def _lock_is_stale():
        """Returns True if the lock file exists but no live process holds it."""
        if not os.path.exists(LOCK_FILE):
            return False
        for proc in psutil.process_iter(["pid", "cmdline"]):
            try:
                cmdline = " ".join(proc.info["cmdline"] or [])
                if "daily_pipeline" in cmdline:
                    return False  # a live pipeline process exists
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return True  # file exists but no pipeline process running → stale

    if _lock_is_stale():
        logger.warning("Stale lock file detected (no live pipeline process). Clearing it.")
        os.remove(LOCK_FILE)

    try:
        lock_fd = os.open(LOCK_FILE, os.O_CREAT | os.O_WRONLY)
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_fd
    except BlockingIOError:
        logger.error("PIPELINE ALREADY RUNNING. Another instance holds the lock. Exiting.")
        sys.exit(1)


# ─── Stage Runners ────────────────────────────────────────────────────────────


def run_stage_scrape() -> dict:
    """Stage 1: Scrape new leads via Google Places API + Playwright."""
    logger.info("=" * 60)
    logger.info("STAGE 1: SCRAPE — Google Places API Lead Acquisition")
    logger.info("=" * 60)

    try:
        from bot1_smb import scrape_gta_smbs as scrape_local
        from bot2_ecom import scrape_gta_smbs as scrape_ecom

        logger.info("Starting Bot 1 (Local SMB Scraper)...")
        stats_local = scrape_local(target_leads=50)

        logger.info("Starting Bot 2 (Ecom Scraper)...")
        stats_ecom = scrape_ecom(target_leads=50)

        combined_stats = {
            "new_leads": stats_local.get("new_leads", 0) + stats_ecom.get("new_leads", 0),
            "errors": stats_local.get("errors", 0) + stats_ecom.get("errors", 0),
        }
        logger.info(f"Scrapers finished: {combined_stats}")
        return combined_stats
    except Exception as e:
        logger.error(f"STAGE 1 FAILED: {e}", exc_info=True)
        return {"new_leads": 0, "errors": 1, "fatal_error": str(e)}


def run_stage_generate() -> dict:
    """Stage 2: Generate Gemini AI pitches for new leads."""
    logger.info("=" * 60)
    logger.info("STAGE 2: GENERATE — Gemini AI Pitch Generation")
    logger.info("=" * 60)

    try:
        import db
        from bot3_generator import run_outreach_generation_cycle

        # Retry leads stuck in error state (reset up to 20 per run for re-generation)
        retried = db.reset_error_leads(limit=20)
        if retried:
            logger.info(f"[+] Reset {retried} error-state leads for retry.")

        before_count = len(db.get_pending_smb_infographics())
        run_outreach_generation_cycle()
        after_count = len(db.get_pending_smb_infographics())
        generated = before_count - after_count
        logger.info(f"Generated {generated} pitches ({after_count} still pending).")
        return {"generated": generated, "still_pending": after_count}

    except Exception as e:
        logger.error(f"STAGE 2 FAILED: {e}", exc_info=True)
        return {"generated": 0, "fatal_error": str(e)}


def run_stage_send(dry_run: bool = False) -> dict:
    """Stage 3: Send initial emails."""
    logger.info("=" * 60)
    logger.info("STAGE 3: SEND — Email Dispatch")
    logger.info("=" * 60)

    results = {"initial": {}}

    try:
        from bot4_outreach import run_smb_outreach

        results["initial"] = run_smb_outreach(dry_run=dry_run)
        logger.info(f"Initial outreach: {results['initial']}")
    except Exception as e:
        logger.error(f"Initial outreach FAILED: {e}", exc_info=True)
        results["initial"] = {"sent": 0, "failed": 0, "fatal_error": str(e)}

    return results


def run_stage_metrics() -> dict:
    """Stage 4: Sync open tracking data + compute daily metrics."""
    logger.info("=" * 60)
    logger.info("STAGE 4: METRICS — Sync Opens + Daily Report")
    logger.info("=" * 60)

    results = {"synced_opens": 0, "open_rate": 0, "bounce_rate": 0}

    # Sync opens from tracking server
    try:
        from metrics import sync_opens

        synced = sync_opens()
        results["synced_opens"] = synced
        logger.info(f"Synced {synced} new opens from tracking server.")
    except Exception as e:
        logger.warning(f"Open tracking sync skipped: {e}")

    # Compute and log metrics
    try:
        import db

        metrics = db.get_email_metrics(days=7)
        results["open_rate"] = metrics.get("open_rate", 0)
        results["bounce_rate"] = metrics.get("bounce_rate", 0)

        logger.info("── 7-Day Email Performance ──")
        logger.info(f"  Sent:         {metrics['total_sent']}")
        logger.info(f"  Delivered:    {metrics['delivered']} ({metrics['delivery_rate']}%)")
        logger.info(f"  Opened:       {metrics['total_opened']} ({metrics['open_rate']}% open rate)")
        logger.info(f"  Bounced:      {metrics['total_bounced']} ({metrics['bounce_rate']}% bounce rate)")
        if metrics["avg_hours_to_open"] is not None:
            logger.info(f"  Avg Open Time: {metrics['avg_hours_to_open']} hrs")

        # Log per-type breakdown
        if metrics["by_type"]:
            for etype, data in sorted(metrics["by_type"].items()):
                rate = round(data["opened"] / data["sent"] * 100, 1) if data["sent"] > 0 else 0
                logger.info(f"    {etype}: {data['sent']} sent, {data['opened']} opened ({rate}%)")

    except Exception as e:
        logger.warning(f"Metrics computation failed: {e}")

    return results


# ─── Main Pipeline ────────────────────────────────────────────────────────────


def run_pipeline(dry_run: bool = False, args: dict = None):
    """Runs the complete daily pipeline sequentially."""
    if args is None:
        args = {}
    pipeline_start = time.time()

    logger.info("")
    logger.info("*" * 60)
    logger.info("  DEDOLYTICS DAILY PIPELINE")
    logger.info(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info(f"  Log:  {log_filename}")
    logger.info("*" * 60)
    logger.info("")

    # Acquire pipeline-level lock
    acquire_pipeline_lock()

    import db

    if db.get_state("pipeline_paused") == "yes":
        logger.warning("************************************************************")
        logger.warning("  PIPELINE IS PAUSED DUE TO GUARDRAILS.")
        logger.warning("  Please check the daily report and manually resume by")
        logger.warning("  updating the 'pipeline_state' table.")
        logger.warning("************************************************************")
        return {"fatal_error": "Pipeline paused by guardrails."}

    # Pre-populate with empty dicts so summary never KeyErrors on skipped stages
    all_results = {
        "scrape": {"new_leads": 0},
        "generate": {"generated": 0},
        "send": {"initial": {"sent": 0, "failed": 0}},
        "metrics": {},
    }
    stage1_elapsed = stage2_elapsed = stage3_elapsed = 0.0

    # ── Auto-Top-Up Fallback ──
    # If we are in outreach-only mode but have very few leads, trigger a small scrape
    ready_leads = len(db.get_ready_smb_emails())
    auto_topup = False
    if args.get("outreach_only") and ready_leads < 50:
        logger.warning(f"[!] Outreach queue critically low ({ready_leads} leads). Forcing top-up scrape.")
        auto_topup = True

    # ── Stage 1: Scrape ──
    if not args.get("outreach_only") and not args.get("gen_only") or auto_topup:
        stage1_start = time.time()
        # If it's an auto-topup, we only need a small batch (100)
        target = 100 if auto_topup else 700

        logger.info("=" * 60)
        logger.info(f"STAGE 1: SCRAPE — {'AUTO TOP-UP' if auto_topup else 'REGULAR'}")
        logger.info("=" * 60)

        try:
            from bot1_smb import scrape_gta_smbs as scrape_local
            from bot2_ecom import scrape_gta_smbs as scrape_ecom

            stats_local = scrape_local(target_leads=target)
            stats_ecom = scrape_ecom(target_leads=10)  # Small ecom topup
            all_results["scrape"] = {"new_leads": stats_local.get("new_leads", 0) + stats_ecom.get("new_leads", 0)}
        except Exception as e:
            logger.error(f"Stage 1 top-up failed: {e}")

        stage1_elapsed = time.time() - stage1_start
        logger.info(f"Stage 1 completed in {stage1_elapsed / 60:.1f} min\n")
    else:
        logger.info("Stage 1 (Scrape) skipped by flag.")

    # ── Stage 2: Generate ──
    if not args.get("outreach_only") and not args.get("scrape_only") or auto_topup:
        stage2_start = time.time()
        all_results["generate"] = run_stage_generate()
        stage2_elapsed = time.time() - stage2_start
        logger.info(f"Stage 2 completed in {stage2_elapsed / 60:.1f} min\n")
    else:
        logger.info("Stage 2 (Generate) skipped by flag.")

    # ── Stage 3: Send ──
    if not args.get("scrape_only") and not args.get("gen_only"):
        stage3_start = time.time()
        all_results["send"] = run_stage_send(dry_run=dry_run)
        stage3_elapsed = time.time() - stage3_start
        logger.info(f"Stage 3 completed in {stage3_elapsed / 60:.1f} min\n")
    else:
        logger.info("Stage 3 (Send) skipped by flag.")

    # ── Stage 4: Metrics ──
    stage4_start = time.time()
    all_results["metrics"] = run_stage_metrics()
    stage4_elapsed = time.time() - stage4_start
    logger.info(f"Stage 4 completed in {stage4_elapsed:.1f} sec\n")

    # ── Summary ──
    total_elapsed = time.time() - pipeline_start

    logger.info("")
    logger.info("*" * 60)
    logger.info("  PIPELINE SUMMARY")
    logger.info("*" * 60)
    logger.info(f"  Total time:       {total_elapsed / 60:.1f} min")
    logger.info(
        f"  Stage 1 (Scrape): {stage1_elapsed / 60:.1f} min — {all_results['scrape'].get('new_leads', 0)} new leads"
    )
    logger.info(
        f"  Stage 2 (Gen):    {stage2_elapsed / 60:.1f} min — {all_results['generate'].get('generated', 0)} infographics"
    )

    send_results = all_results.get("send", {})
    initial = send_results.get("initial", {})
    logger.info(
        f"  Stage 3 (Send):   {stage3_elapsed / 60:.1f} min — {initial.get('sent', 0)} sent, {initial.get('failed', 0)} failed"
    )

    metrics_data = all_results.get("metrics", {})
    logger.info(
        f"  Stage 4 (Metrics): synced {metrics_data.get('synced_opens', 0)} opens — "
        f"{metrics_data.get('open_rate', 0)}% open rate, {metrics_data.get('bounce_rate', 0)}% bounce rate"
    )

    # Check for any fatal errors
    has_errors = any("fatal_error" in v if isinstance(v, dict) else False for v in all_results.values())
    if has_errors:
        logger.warning("  STATUS: COMPLETED WITH ERRORS (check log for details)")
    else:
        logger.info("  STATUS: ALL STAGES COMPLETED SUCCESSFULLY")

    logger.info("*" * 60)
    logger.info("")

    return all_results


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Dedolytics Daily Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Simulate email sending")
    parser.add_argument("--scrape-only", action="store_true", help="Run only Stage 1 (Scraping)")
    parser.add_argument("--gen-only", action="store_true", help="Run only Stage 2 (AI Generation)")
    parser.add_argument("--outreach-only", action="store_true", help="Run only Stage 3 (Email Outreach)")

    cmd_args = parser.parse_args()

    pipeline_args = {
        "scrape_only": cmd_args.scrape_only,
        "gen_only": cmd_args.gen_only,
        "outreach_only": cmd_args.outreach_only,
    }

    run_pipeline(dry_run=cmd_args.dry_run, args=pipeline_args)
