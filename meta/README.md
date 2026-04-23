# PYS Social Media Dashboard

Pulls Facebook + Instagram analytics for Pensacola Youth Soccer and generates a
self-contained HTML dashboard hosted on Google Cloud Storage.

**Dashboard URL:** https://storage.googleapis.com/pys-social-dashboard/dashboard.html

---

## Setup (one time)

### 1. Python environment

```bash
cd pys/meta
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Meta developer app

1. Go to https://developers.facebook.com/ and create a new app
   - App type: **Business** (or Consumer)
   - Name it something like `pys_social`
2. Note the **App ID** and **App Secret** (App Settings → Basic)
3. Add the **Instagram** product to the app
4. In 1Password ("API keys" vault), create an item called **Meta_PYS** with fields:
   - `app_id` — your App ID
   - `app_secret` — your App Secret
   - `access_token` — leave blank for now

### 3. Get your Page ID and Instagram Account ID

After creating the app, go to https://developers.facebook.com/tools/explorer/,
select your app, generate a token with `pages_show_list` checked, then run:

```
https://graph.facebook.com/pensacolayouthsoccer?fields=id,instagram_business_account&access_token=YOUR_TOKEN
```

Copy the numeric `id` (page) and `instagram_business_account.id` into `config.py`.
Also put the App ID in `config.py`.

### 4. Generate the page token

```bash
# First generate a short-lived token in Graph API Explorer with these permissions:
#   pages_show_list, pages_read_engagement, pages_read_user_content,
#   instagram_basic, instagram_manage_insights
python3 setup_token.py --token PASTE_SHORT_LIVED_TOKEN_HERE
```

This saves a never-expiring page token to `page_token.txt`.

### 5. Google Cloud Storage

1. Go to https://console.cloud.google.com/ (project: `dashboard-494217`)
2. Enable the **Cloud Storage API** if not already enabled
3. Go to APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: **Desktop app**
   - Download the JSON and save it as `client_secret.json` in this directory
4. On first `--upload` run, a browser window will open to authorize GCS access

---

## Running

```bash
source venv/bin/activate

# Fetch latest data from Meta API
python3 fetch.py

# Generate dashboard HTML
python3 dashboard.py

# Generate and upload to GCS
python3 dashboard.py --upload

# Generate, upload, and open in browser
python3 dashboard.py --upload --open
```

---

## Raspberry Pi / Cronicle

On the Pi, clone the repo and set up the venv the same way. Copy
`page_token.txt` and `token.pickle` via scp. Add a monthly Cronicle job
pointing to a shell script like:

```bash
#!/bin/bash
cd /home/philnickinson/pys/meta
./venv/bin/python fetch.py
./venv/bin/python dashboard.py --upload
```

---

## Files

| File | Purpose |
|------|---------|
| `config.py` | Page IDs, API version, file paths |
| `creds.py` | Loads app secret from 1Password |
| `fetch.py` | Pulls data from Meta Graph API → `data/` |
| `dashboard.py` | Reads `data/`, generates HTML, uploads to GCS |
| `setup_token.py` | One-time token exchange |
| `gcs_auth.py` | Google Cloud OAuth handler |

Secrets (`page_token.txt`, `token.pickle`, `client_secret.json`) are gitignored.
Data files (`data/*.json`) are gitignored — they accumulate on the machine running
the refreshes.
