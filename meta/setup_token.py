"""
Token setup — run this once to exchange a short-lived token for a
never-expiring Page Access Token.

Usage:
    python setup_token.py --token YOUR_SHORT_LIVED_TOKEN

How to get the short-lived token:
  1. Go to https://developers.facebook.com/tools/explorer/
  2. Select your PYS app
  3. Click "Generate Access Token" and check these permissions:
       pages_show_list
       pages_read_engagement
       pages_read_user_content
       instagram_basic
       instagram_manage_insights
  4. Copy the token and paste it after --token
"""

import argparse
import os
import sys

import requests

import creds
from config import APP_ID, PAGE_ID, TOKEN_FILE


def exchange_for_long_lived(short_token, app_id, app_secret):
    r = requests.get(
        "https://graph.facebook.com/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": short_token,
        },
    )
    data = r.json()
    if "error" in data:
        print(f"ERROR exchanging token: {data['error']['message']}")
        sys.exit(1)
    return data["access_token"]


def get_page_token(long_user_token):
    # Try /me/accounts first (works when personal account is direct page admin)
    r = requests.get(
        "https://graph.facebook.com/me/accounts",
        params={"access_token": long_user_token},
    )
    data = r.json()
    if "error" not in data:
        for page in data.get("data", []):
            if page["id"] == PAGE_ID:
                return page["access_token"]

    # Fallback: fetch the page token directly by page ID (works for Business Manager pages)
    print(f"  Not found in /me/accounts — trying direct page token fetch...")
    r2 = requests.get(
        f"https://graph.facebook.com/{PAGE_ID}",
        params={"fields": "access_token", "access_token": long_user_token},
    )
    data2 = r2.json()
    if "error" in data2:
        print(f"ERROR getting page token: {data2['error']['message']}")
        print("The token may not have sufficient page permissions.")
        sys.exit(1)
    token = data2.get("access_token")
    if not token:
        print(f"ERROR: No access_token returned for page {PAGE_ID}.")
        print(f"Response: {data2}")
        sys.exit(1)
    return token


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", help="Short-lived user token from Graph API Explorer")
    args = parser.parse_args()

    print("Loading credentials from 1Password...")
    app_secret  = creds.get_app_secret()
    short_token = args.token or creds.get_access_token()

    print("Exchanging for long-lived user token...")
    long_token = exchange_for_long_lived(short_token, APP_ID, app_secret)
    print("  OK — long-lived user token obtained")

    print("Getting Page Access Token...")
    page_token = get_page_token(long_token)

    with open(TOKEN_FILE, "w") as f:
        f.write(page_token)

    print(f"  Saved to {TOKEN_FILE}")
    print("  Page tokens derived from long-lived user tokens never expire.")
    print("\nAll done. Run: python3 fetch.py")


if __name__ == "__main__":
    main()
