#!/usr/bin/env python3
"""
Dedolytics Pipeline Orchestrator (Bots 1 -> 4)

Executes the four daily outbound bots in strict sequential order.
Cron is scheduled to run this file at 8:30 AM daily.

1. Bot 1: Scrapes Local SMBs
2. Bot 2: Scrapes E-commerce Leads
3. Bot 3: Generates AI Infographics & Audits
4. Bot 4: Dispatches initial outreach + follow-ups
"""

import os
import sys
import subprocess
import time

# Ensure we're running from the `crm` directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

bots = [
    ("Bot 1 (Local SMB Scraper)", "bot1_smb.py"),
    ("Bot 2 (E-Com Scraper)", "bot2_ecom.py"),
    ("Bot 3 (Gemini Generator)", "bot3_generator.py"),
    ("Bot 4 (Outreach & Follow-Up)", "bot4_outreach.py"),
]


def run_orchestrator():
    print(f"\n========================================================")
    print(f"  DEDOLYTICS PIPELINE ORCHESTRATOR STARTED")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"========================================================\n")

    for bot_name, script_name in bots:
        print(f"\n>>>> Executing {bot_name} ({script_name})...")
        try:
            # We use the python executable from the virtual environment if it exists, else system python
            python_exec = "venv/bin/python" if os.path.exists("venv/bin/python") else sys.executable

            result = subprocess.run(
                [python_exec, script_name],
                check=True,
                capture_output=False,  # Print straight to the console/cron log
            )
            print(f"<<<< {bot_name} completed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"\n[CRITICAL ERROR] {bot_name} failed with exit code {e.returncode}.")
            print("Aborting the pipeline sequence to prevent bad downstream data.")
            sys.exit(1)

        # Slight pause between distinct bot executions
        time.sleep(2)

    print(f"\n========================================================")
    print(f"  ORCHESTRATOR COMPLETED SUCCESSFULLY")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"========================================================\n")


if __name__ == "__main__":
    run_orchestrator()
