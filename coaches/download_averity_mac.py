#!/usr/bin/env python3
"""
Run this directly on your Mac (not in OrbStack/workspace):
  python3 ~/Git/pys/coaches/download_averity_mac.py
"""

import csv
import time
import requests
from pathlib import Path

OUTPUT_DIR = Path("~/Git/pys/coaches/2021").expanduser()
CSV_FILE = Path("~/Git/pys/coaches/complete.csv").expanduser()
LOG_FILE = Path("~/Git/pys/coaches/averity_download_log.txt").expanduser()

OUTPUT_DIR.mkdir(exist_ok=True)

COOKIES = {
    "ASP.NET_SessionId": "jtn1ipzhdqwti5fktxplzxl4",
    "__RequestVerificationToken_L2xvZ2lu0": "67l-OxEAmiZGc3J4HQExT7efYnWp39AalzIRNG2TSAws49y48Q7iGqXnciJ5TvqS0DK3TmJLxtfKRAgizEOZf-gb9hg1",
    "ClientUsersAdministration": "F1606E4CC8012F86AEA9DC4080A4860730DA52E2C29ED7CF40C55B331878545AE13BA608381EFE8687236870EB2067A2B1C53EBE73F091E0D1F22DF6EF5F0A65BDC695E3AE108835C0CDC43BB0EE08F624B21FA3"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://averity.com/BackgroundChecks.aspx?Tab=complete"
}

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
    log(f"Found {len(rows)} records")

    # Quick test first
    log("Testing session cookies...")
    test = requests.get(
        "https://averity.com/login/DisplayReport.aspx?RequestID=6889474",
        cookies=COOKIES, headers=HEADERS,
        allow_redirects=False
    )
    log(f"  Test response: {test.status_code}, Location: {test.headers.get('Location', 'none')[:80]}")
    if test.status_code != 302 or "priorityresearch.com" not in test.headers.get("Location", ""):
        log("  ERROR: Session appears invalid or expired. Re-copy cookies from browser and update this script.")
        return
    log("  Session OK")

    downloaded = 0
    skipped = 0
    errors = []

    for row in rows:
        first = row.get("First Name", "unknown").strip()
        last = row.get("Last Name", "unknown").strip()
        request_id = row.get("Report", "").strip().split("RequestID=")[-1]

        if not request_id:
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
            resp = requests.get(
                f"https://averity.com/login/DisplayReport.aspx?RequestID={request_id}",
                cookies=COOKIES, headers=HEADERS,
                allow_redirects=False
            )

            pdf_url = resp.headers.get("Location")
            if not pdf_url or "priorityresearch.com" not in pdf_url:
                log(f"  NO REDIRECT: {last}, {first} (RequestID={request_id}, status={resp.status_code})")
                skipped += 1
                continue

            pdf_resp = requests.get(pdf_url)
            pdf_resp.raise_for_status()
            out_path.write_bytes(pdf_resp.content)
            log(f"  OK: 2021/{filename} ({len(pdf_resp.content):,} bytes)")
            downloaded += 1

        except Exception as e:
            msg = f"  ERROR — {last}, {first}: {e}"
            log(msg)
            errors.append(msg)

        write_log()
        time.sleep(0.5)

    log(f"\nDone. Downloaded: {downloaded} | Skipped: {skipped} | Errors: {len(errors)}")
    if errors:
        log("\nErrors:")
        for e in errors:
            log(e)
    write_log()

if __name__ == "__main__":
    main()
