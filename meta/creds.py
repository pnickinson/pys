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
        print("ERROR: 1Password CLI (`op`) not found.")
        print("Install it: https://developer.1password.com/docs/cli/get-started/")
        sys.exit(1)
    try:
        result = subprocess.run(
            [op_bin, "item", "get", item, "--vault", "API keys", "--field", field, "--reveal"],
            capture_output=True, text=True, check=True,
        )
        value = result.stdout.strip()
        if not value:
            raise ValueError(f"Empty value for field '{field}'")
        return value
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Could not read '{field}' from 1Password item '{item}'.")
        print(f"  {e.stderr.strip()}")
        print(f"  Check: op item get \"{item}\" --vault \"API keys\" --field {field}")
        sys.exit(1)


def get_app_secret():
    return _op("app_secret")

def get_access_token():
    """Short-lived token field — used by setup_token.py only."""
    return _op("access_token")

def get_mailchimp_api_key():
    """Read Mailchimp API key from 1Password, or fall back to mailchimp_api_key.txt."""
    key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mailchimp_api_key.txt")
    op_bin = _find_op()
    if op_bin:
        return _op("mailchimp_api", item="Mailchimp")
    if os.path.exists(key_file):
        with open(key_file) as f:
            return f.read().strip()
    print("ERROR: 1Password CLI not found and mailchimp_api_key.txt is missing.")
    print(f"  Create it: echo 'YOUR_KEY' > {key_file}")
    import sys; sys.exit(1)
