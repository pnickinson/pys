"""
Load Meta API credentials from 1Password via the `op` CLI.

Item name:  Meta_PYS   (in the "API keys" vault)
Fields:     app_id, app_secret, access_token (used by setup_token.py only)

Requires the 1Password CLI: https://developer.1password.com/docs/cli/get-started/
Verify it works: op item get "Meta_PYS" --vault "API keys" --field app_id
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


def _op(field):
    op_bin = _find_op()
    if not op_bin:
        print("ERROR: 1Password CLI (`op`) not found.")
        print("Install it: https://developer.1password.com/docs/cli/get-started/")
        sys.exit(1)
    try:
        result = subprocess.run(
            [op_bin, "item", "get", OP_ITEM, "--vault", "API keys", "--field", field, "--reveal"],
            capture_output=True, text=True, check=True,
        )
        value = result.stdout.strip()
        if not value:
            raise ValueError(f"Empty value for field '{field}'")
        return value
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Could not read '{field}' from 1Password item '{OP_ITEM}'.")
        print(f"  {e.stderr.strip()}")
        print(f"  Check: op item get \"{OP_ITEM}\" --vault \"API keys\" --field {field}")
        sys.exit(1)


def get_app_secret():
    return _op("app_secret")

def get_access_token():
    """Short-lived token field — used by setup_token.py only."""
    return _op("access_token")
