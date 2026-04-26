"""
Google Cloud Storage auth for the PYS social dashboard.

Uses a service account key file (service_account.json) — no browser auth needed.

service_account.json: download from GCP → IAM & Admin → Service Accounts →
pys-dashboard-uploader → Keys (project: dashboard-494217)
"""

import os

SCRIPT_DIR      = os.path.dirname(os.path.abspath(__file__))
SCOPES          = ["https://www.googleapis.com/auth/devstorage.full_control"]
SERVICE_ACCOUNT = os.path.join(SCRIPT_DIR, "service_account.json")


def get_credentials():
    from google.oauth2 import service_account

    if not os.path.exists(SERVICE_ACCOUNT):
        raise FileNotFoundError(
            "Missing service_account.json.\n"
            "Download a service account key from:\n"
            "https://console.cloud.google.com/iam-admin/serviceaccounts\n"
            "(project: dashboard-494217)"
        )
    return service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT, scopes=SCOPES
    )


def get_storage_service():
    from googleapiclient.discovery import build
    return build("storage", "v1", credentials=get_credentials())
