#!/usr/bin/env python3
"""
Download Averity/Protect Youth Sports background check reports.
Reads complete.csv, logs in to averity.com, and downloads each PDF.
Saves to: ~/Git/pys/coaches/2021/{lastname}_{firstname}.pdf

Run on your Mac:
  pip install playwright
  playwright install chromium
  python3 download_averity_reports.py
"""

import csv
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

USERNAME = "pensacolayouthsoccer"
PASSWORD = "9nQpX7VBJCLGqhi@"
CSV_FILE = Path(__file__).parent / "complete.csv"
OUTPUT_DIR = Path(__file__).parent / "2021"
LOG_FILE = Path(__file__).parent / "averity_download_log.txt"

OUTPUT_DIR.mkdir(exist_ok=True)
log_lines = []

def log(msg):
    print(msg)
    log_lines.append(msg)

def write_log():
    LOG_FILE.write_text("\n".join(log_lines) + "\n")

def safe_filename(last, first):
    name = f"{last}_{first}".lower()
    name = "".join(c if c.isalnum() or c in "_-" else "_" for c in name)
    return f"{name}.pdf"

def main():
    with open(CSV_FILE, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    log(f"Found {len(rows)} records in CSV")

    downloaded = 0
    skipped = 0
    errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Log in
        log("Logging in to averity.com...")
        page.goto("https://averity.com/Login.aspx", wait_until="networkidle")
        page.screenshot(path=str(Path(__file__).parent / "debug_login.png"))
        log(f"  Current URL: {page.url}")
        log(f"  Page content snippet: {page.content()[:500]}")
        log("  Waiting 15 seconds so you can see the browser window...")
        page.wait_for_timeout(15000)
        browser.close()
        return

        for row in rows:
            first = row.get("First Name", "unknown").strip()
            last = row.get("Last Name", "unknown").strip()
            report_url = row.get("Report", "").strip()

            if not report_url:
                log(f"  NO URL: {last}, {first}")
                skipped += 1
                continue

            filename = safe_filename(last, first)
            out_path = OUTPUT_DIR / filename

            if out_path.exists():
                log(f"  EXISTS: 2021/{filename}")
                skipped += 1
                continue

            try:
                # Navigate to the report page and capture any PDF download
                pdf_url = None

                def handle_response(response):
                    nonlocal pdf_url
                    if "priorityresearch.com" in response.url and response.status == 200:
                        ct = response.headers.get("content-type", "")
                        if "pdf" in ct:
                            pdf_url = response.url

                page.on("response", handle_response)
                page.goto(report_url, wait_until="networkidle")
                time.sleep(2)  # give it a moment to fully load
                page.remove_listener("response", handle_response)

                if pdf_url:
                    # Download the PDF directly
                    import requests
                    resp = requests.get(pdf_url)
                    resp.raise_for_status()
                    out_path.write_bytes(resp.content)
                    log(f"  OK: 2021/{filename} ({len(resp.content):,} bytes)")
                    downloaded += 1
                else:
                    # Try triggering a download directly
                    with context.expect_page() as new_page_info:
                        pass
                    log(f"  NO PDF FOUND: {last}, {first} — {report_url}")
                    skipped += 1

            except Exception as e:
                msg = f"  ERROR — {last}, {first}: {e}"
                log(msg)
                errors.append(msg)

            write_log()
            time.sleep(1)

        browser.close()

    log(f"\nDone. Downloaded: {downloaded} | Skipped: {skipped} | Errors: {len(errors)}")
    if errors:
        log("\nErrors:")
        for e in errors:
            log(e)
    write_log()

if __name__ == "__main__":
    main()
