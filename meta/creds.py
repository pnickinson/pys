"""
Load API credentials from 1Password via the `op` CLI.

Meta:      item "Meta_PYS",  fields: app_id, app_secret, access_token
Mailchimp: item "Mailchimp", field:  mailchimp_api

Requires the 1Password CLI: https://developer.1password.com/docs/cli/get-started/
"""

import os
import subprocess
import sys

OP_ITEM = "Meta_PYS"


def _find_op():
    import shutil
    candidates = [
        shutil.which("op"),
        os.path.expanduser("~/bin/op"),
        "/usr/local/bin/op",
        "/opt/homebrew/bin/op",
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def _op(field, item=None):
    if item is None:
        item = OP_ITEM
    op_bin = _find_op()
    if not op_bin:
        return None
    try:
        result = subprocess.run(
            [op_bin, "item", "get", item, "--vault", "API keys", "--field", field, "--reveal"],
            capture_output=True, text=True, check=True, timeout=10,
        )
        value = result.stdout.strip()
        return value if value else None
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def get_app_secret():
    value = _op("app_secret")
    if value:
        return value
    print(f"ERROR: Could not read app_secret from 1Password item '{OP_ITEM}'.")
    print("  Ensure `op` is signed in or the field exists.")
    sys.exit(1)

def get_access_token():
    """Short-lived token field — used by setup_token.py only."""
    value = _op("access_token")
    if value:
        return value
    print(f"ERROR: Could not read access_token from 1Password item '{OP_ITEM}'.")
    sys.exit(1)

def get_mailchimp_api_key():
    """Read Mailchimp API key from /etc/teamsnap-weather/credentials, or fall back to 1Password."""
    CREDS_FILE = "/etc/teamsnap-weather/credentials"
    if os.path.exists(CREDS_FILE):
        with open(CREDS_FILE) as f:
            for line in f:
                line = line.strip()
                if line.startswith("MAILCHIMP_API_KEY="):
                    return line.split("=", 1)[1]
    value = _op("mailchimp_api", item="Mailchimp")
    if value:
        return value
    print("ERROR: Could not read Mailchimp API key from /etc/teamsnap-weather/credentials or 1Password.")
    sys.exit(1)
