import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Fill these in after creating the Meta developer app and running setup_token.py.
# Get PAGE_ID from: https://graph.facebook.com/pensacolayouthsoccer?fields=id&access_token=YOUR_TOKEN
# Get IG_ACCOUNT_ID from: https://graph.facebook.com/PAGE_ID?fields=instagram_business_account&access_token=YOUR_TOKEN
PAGE_ID       = "577747999226096"
IG_ACCOUNT_ID = "17841410721551227"
APP_ID        = "2200232384053922"

API_VERSION = "v22.0"

TOKEN_FILE  = os.path.join(SCRIPT_DIR, "page_token.txt")
DATA_DIR    = os.path.join(SCRIPT_DIR, "data")
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "dashboard.html")
LOGO_PATH   = os.path.join(SCRIPT_DIR, "assets", "logo.png")
