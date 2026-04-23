"""
Fetch Facebook Page + Instagram analytics from the Meta Graph API.

Saves JSON files to data/ for dashboard.py to read.

Usage:
    python3 fetch.py
"""

import json
import os
import sys
import time
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings("ignore", message=".*LibreSSL.*")
warnings.filterwarnings("ignore", message=".*NotOpenSSLWarning.*")

import requests

from config import API_VERSION, DATA_DIR, IG_ACCOUNT_ID, PAGE_ID, TOKEN_FILE

BASE = f"https://graph.facebook.com/{API_VERSION}"


# ── Helpers ──────────────────────────────────────────────────────────────────

def load_token():
    if not os.path.exists(TOKEN_FILE):
        print(f"ERROR: {TOKEN_FILE} not found. Run setup_token.py first.")
        sys.exit(1)
    with open(TOKEN_FILE) as f:
        return f.read().strip()


def get(path, params, token):
    params = dict(params)
    params["access_token"] = token
    r = requests.get(f"{BASE}/{path}", params=params)
    data = r.json()
    if "error" in data:
        msg = data["error"].get("message", "unknown error")
        print(f"  API error [{path}]: {msg}")
        return None
    return data


def get_paged(path, params, token, limit=50):
    results = []
    data = get(path, params, token)
    if not data:
        return None
    results.extend(data.get("data", []))
    while "paging" in data and "next" in data.get("paging", {}) and len(results) < limit:
        r = requests.get(data["paging"]["next"])
        data = r.json()
        if "error" in data:
            break
        results.extend(data.get("data", []))
        time.sleep(0.1)
    return results[:limit]


def save(filename, data):
    if data is None:
        print(f"  Skipped {filename} (keeping previous data)")
        return
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    count = len(data) if isinstance(data, list) else "dict"
    print(f"  Saved {filename} ({count})")


def append_history(filename, record):
    """Append a snapshot record to an accumulating history file."""
    path = os.path.join(DATA_DIR, filename)
    os.makedirs(DATA_DIR, exist_ok=True)
    history = []
    if os.path.exists(path):
        with open(path) as f:
            history = json.load(f)
    today = record.get("date", datetime.utcnow().strftime("%Y-%m-%d"))
    history = [h for h in history if h.get("date") != today]
    history.append(record)
    history.sort(key=lambda x: x.get("date", ""))
    with open(path, "w") as f:
        json.dump(history, f, indent=2)
    print(f"  Updated {filename} ({len(history)} snapshots)")


# ── Facebook ─────────────────────────────────────────────────────────────────

def fetch_fb_page(token):
    print("Facebook: page info")
    page = get(PAGE_ID, {
        "fields": "id,name,fan_count,followers_count,link,about",
    }, token)
    if page:
        append_history("fb_fan_history.json", {
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "fan_count": page.get("fan_count", 0),
        })
    return page


def fetch_fb_posts(token):
    print("Facebook: posts")
    fields = (
        "id,message,story,created_time,full_picture,permalink_url,"
        "reactions.limit(0).summary(true),"
        "comments.limit(0).summary(true),"
        "shares,"
        "attachments{type,media_type,title}"
    )
    posts = get_paged(f"{PAGE_ID}/posts", {
        "fields": fields,
        "limit": 10,
    }, token, limit=60)

    if posts is None:
        return None

    for post in posts:
        post["reaction_count"] = (
            post.get("reactions", {}).get("summary", {}).get("total_count", 0)
        )
        post["comment_count"] = (
            post.get("comments", {}).get("summary", {}).get("total_count", 0)
        )
        post["share_count"] = post.get("shares", {}).get("count", 0)

    print(f"  Fetched {len(posts)} posts")
    return posts


# ── Instagram ─────────────────────────────────────────────────────────────────

def fetch_ig_account(token):
    print("Instagram: account info")
    account = get(IG_ACCOUNT_ID, {
        "fields": "id,name,username,biography,followers_count,media_count,website",
    }, token)
    if account:
        append_history("ig_follower_history.json", {
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "followers_count": account.get("followers_count", 0),
        })
    return account


def fetch_ig_insights(token):
    print("Instagram: account insights")
    until = datetime.utcnow()
    since_30 = until - timedelta(days=30)

    result = {"monthly": None}
    followers = get(f"{IG_ACCOUNT_ID}/insights", {
        "metric": "follower_count",
        "period": "day",
        "since": int(since_30.timestamp()),
        "until": int(until.timestamp()),
    }, token)
    result["follower_history"] = followers
    return result


def fetch_ig_media(token):
    print("Instagram: media")
    media = get_paged(f"{IG_ACCOUNT_ID}/media", {
        "fields": (
            "id,caption,media_type,media_product_type,"
            "media_url,thumbnail_url,timestamp,"
            "like_count,comments_count,permalink"
        ),
        "limit": 25,
    }, token, limit=60)

    print(f"  Fetching insights for {len(media)} posts...")
    for item in media:
        mtype  = item.get("media_type", "")
        mptype = item.get("media_product_type", "")

        if mptype == "REELS":
            metric = "reach,total_interactions,likes,comments,saved,shares,reposts,views"
        elif mtype == "CAROUSEL_ALBUM":
            metric = "reach,total_interactions,likes,comments,saved,shares,reposts"
        elif mtype == "VIDEO":
            metric = "reach,video_views,total_interactions,likes,comments,saved,shares,reposts"
        elif mtype == "IMAGE":
            metric = "reach,total_interactions,likes,comments,saved,shares,reposts"
        else:
            continue

        ins = get(f"{item['id']}/insights", {"metric": metric}, token)
        if ins and "data" in ins:
            for row in ins["data"]:
                if "value" in row:
                    item[row["name"]] = row["value"]
                else:
                    vals = row.get("values", [])
                    item[row["name"]] = vals[0].get("value", 0) if vals else 0
        time.sleep(0.05)

    return media


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    token = load_token()
    failed = []

    fb_page  = fetch_fb_page(token);  save("fb_page.json",  fb_page)
    fb_posts = fetch_fb_posts(token); save("fb_posts.json", fb_posts)
    if fb_page  is None: failed.append("Facebook page info")
    if fb_posts is None: failed.append("Facebook posts")

    ig_account  = fetch_ig_account(token);  save("ig_account.json",  ig_account)
    ig_insights = fetch_ig_insights(token); save("ig_insights.json", ig_insights)
    ig_media    = fetch_ig_media(token);    save("ig_media.json",    ig_media)
    if ig_account  is None: failed.append("Instagram account info")
    if ig_insights is None: failed.append("Instagram insights")
    if ig_media    is None: failed.append("Instagram media")

    print("\nDone. Run: python3 dashboard.py")

    import json as _json
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _status = {
        "last_run": datetime.utcnow().isoformat(),
        "success": len(failed) == 0,
        "failed": failed,
        "error": None,
        "details": {},
    }
    with open(os.path.join(_script_dir, "run_status.json"), "w") as _f:
        _json.dump(_status, _f)


if __name__ == "__main__":
    try:
        main()
    except Exception as _e:
        import json as _json, traceback as _tb
        _script_dir = os.path.dirname(os.path.abspath(__file__))
        _status = {
            "last_run": datetime.utcnow().isoformat(),
            "success": False,
            "error": str(_e),
            "details": {},
        }
        with open(os.path.join(_script_dir, "run_status.json"), "w") as _f:
            _json.dump(_status, _f)
        _tb.print_exc()
        sys.exit(1)
