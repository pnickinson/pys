"""
One-time backfill of Facebook fan count history.

Fetches historical page_fans data from the Insights API and merges it
into fb_fan_history.json without overwriting existing snapshots.

Usage:
    python3 backfill_fans.py             # backfill last 2 years
    python3 backfill_fans.py --days 365  # backfill last year
"""

import argparse
import json
import os
from datetime import datetime, timedelta

import requests

from config import API_VERSION, DATA_DIR, PAGE_ID, TOKEN_FILE

BASE = f"https://graph.facebook.com/{API_VERSION}"


def load_token():
    with open(TOKEN_FILE) as f:
        return f.read().strip()


def fetch_fan_history(token, since_dt, until_dt):
    """Fetch daily page_fans snapshots between two dates."""
    results = []
    since = int(since_dt.timestamp())
    until = int(until_dt.timestamp())

    # API returns max ~93 days per request; chunk if needed
    chunk = timedelta(days=90)
    current = since_dt
    while current < until_dt:
        end = min(current + chunk, until_dt)
        print(f"  Fetching {current.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}...")
        r = requests.get(
            f"{BASE}/{PAGE_ID}/insights",
            params={
                "metric": "page_fans",
                "period": "day",
                "since": int(current.timestamp()),
                "until": int(end.timestamp()),
                "access_token": token,
            },
        )
        data = r.json()
        if "error" in data:
            print(f"  API error: {data['error']['message']}")
            break
        for item in data.get("data", []):
            if item.get("name") == "page_fans":
                for v in item.get("values", []):
                    date = v.get("end_time", "")[:10]
                    count = v.get("value", 0)
                    if date:
                        results.append({"date": date, "fan_count": count})
        current = end

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=730, help="Days of history to backfill (default: 730)")
    args = parser.parse_args()

    token = load_token()
    until_dt = datetime.utcnow()
    since_dt = until_dt - timedelta(days=args.days)

    print(f"Fetching fan history from {since_dt.strftime('%Y-%m-%d')} to {until_dt.strftime('%Y-%m-%d')}...")
    new_records = fetch_fan_history(token, since_dt, until_dt)
    print(f"  Got {len(new_records)} snapshots from API")

    # Merge with existing history
    history_path = os.path.join(DATA_DIR, "fb_fan_history.json")
    existing = []
    if os.path.exists(history_path):
        with open(history_path) as f:
            existing = json.load(f)

    by_date = {r["date"]: r for r in existing}
    for r in new_records:
        by_date.setdefault(r["date"], r)  # don't overwrite existing snapshots

    merged = sorted(by_date.values(), key=lambda x: x["date"])
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(history_path, "w") as f:
        json.dump(merged, f, indent=2)

    print(f"  Saved {len(merged)} total snapshots to fb_fan_history.json")
    print("\nDone. Run: python3 dashboard.py --upload")


if __name__ == "__main__":
    main()
