#!/usr/bin/env python3
"""
Download Checkr background check reports (PDFs) for 2021-2024.
Saves to: /workspace/pys/coaches/{year}/{lastname}_{firstname}.pdf
"""

import os
import time
import requests
from datetime import datetime

API_KEY = "b18755b3ea5e2e60b78ab2f65c711a8afd1f2413"
BASE_URL = "https://api.checkr.com/v1"
OUTPUT_DIR = "/workspace/pys/coaches"
TARGET_YEARS = {2021, 2022, 2023, 2024}
LOG_FILE = os.path.join(OUTPUT_DIR, f"download_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

session = requests.Session()
session.auth = (API_KEY, "")

log_lines = []

def log(msg):
    print(msg)
    log_lines.append(msg)

def write_log():
    with open(LOG_FILE, "w") as f:
        f.write("\n".join(log_lines) + "\n")


def get(url, params=None):
    resp = session.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


def download_pdf(url, path):
    resp = requests.get(url)  # plain request — S3 signed URLs break if auth header is sent
    resp.raise_for_status()
    with open(path, "wb") as f:
        f.write(resp.content)


def safe_filename(last, first):
    name = f"{last}_{first}".lower()
    # Replace spaces and anything not alphanumeric/underscore/hyphen
    name = "".join(c if c.isalnum() or c in "_-" else "_" for c in name)
    return f"{name}.pdf"


def main():
    downloaded = 0
    skipped = 0
    errors = []

    # Page through all candidates
    next_url = f"{BASE_URL}/candidates"
    params = {"per_page": 100}
    page = 1

    while next_url:
        log(f"Fetching candidates page {page}...")
        data = get(next_url, params=params)
        candidates = data.get("data", [])
        next_url = data.get("next_href")
        params = None  # next_href already has params baked in
        page += 1

        for candidate in candidates:
            first = candidate.get("first_name", "unknown")
            last = candidate.get("last_name", "unknown")
            report_ids = candidate.get("report_ids", [])

            for report_id in report_ids:
                try:
                    report = get(f"{BASE_URL}/reports/{report_id}")
                    created = report.get("created_at", "")
                    year = int(created[:4]) if created else None

                    if year not in TARGET_YEARS:
                        continue

                    doc_ids = report.get("document_ids", [])
                    if not doc_ids:
                        log(f"  NO DOC ({year}): {last}, {first}")
                        skipped += 1
                        continue

                    # Use the first pdf_report document found
                    pdf_url = None
                    for doc_id in doc_ids:
                        doc = get(f"{BASE_URL}/documents/{doc_id}")
                        if doc.get("type") == "pdf_report":
                            pdf_url = doc.get("download_uri")
                            break

                    if not pdf_url:
                        log(f"  NO PDF ({year}): {last}, {first}")
                        skipped += 1
                        continue

                    filename = safe_filename(last, first)
                    out_path = os.path.join(OUTPUT_DIR, str(year), filename)

                    if os.path.exists(out_path):
                        log(f"  EXISTS: {year}/{filename}")
                        skipped += 1
                        continue

                    log(f"  OK: {year}/{filename}")
                    download_pdf(pdf_url, out_path)
                    downloaded += 1

                    time.sleep(0.25)  # be polite to the API

                except Exception as e:
                    msg = f"  ERROR — {last}, {first} report {report_id}: {e}"
                    log(msg)
                    errors.append(msg)

        write_log()  # save after every page in case of interruption
        time.sleep(0.5)

    log(f"\nDone. Downloaded: {downloaded} | Skipped: {skipped} | Errors: {len(errors)}")
    if errors:
        log("\nErrors:")
        for e in errors:
            log(e)
    write_log()


if __name__ == "__main__":
    main()
