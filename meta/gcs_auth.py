"""
Google Cloud Storage auth for the PYS social dashboard.

On first run this opens a browser to authorize. Subsequent runs use
the cached token.pickle in this directory.

client_secret.json: download a Desktop OAuth credential from
https://console.cloud.google.com/ (project: pys-merch-tracking)
"""

import os
import pickle

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE  = os.path.join(SCRIPT_DIR, "token.pickle")
SCOPES      = ["https://www.googleapis.com/auth/devstorage.full_control"]
CLIENT_SECRET = os.path.join(SCRIPT_DIR, "client_secret.json")


def get_credentials():
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRET):
                raise FileNotFoundError(
                    "Missing client_secret.json.\n"
                    "Download a Desktop OAuth credential from:\n"
                    "https://console.cloud.google.com/apis/credentials\n"
                    "(project: pys-merch-tracking)"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    return creds


def get_storage_service():
    from googleapiclient.discovery import build
    return build("storage", "v1", credentials=get_credentials())
