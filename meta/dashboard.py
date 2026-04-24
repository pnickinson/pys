"""
Generate a self-contained HTML social media dashboard for Pensacola Youth Soccer.

Reads JSON files from data/ and produces dashboard.html.

Usage:
    python dashboard.py
    python dashboard.py --open
    python dashboard.py --upload
"""

import argparse
import base64
import json
import os
import sys
import time
import warnings
from collections import defaultdict
from datetime import datetime

warnings.filterwarnings("ignore", message=".*LibreSSL.*")
warnings.filterwarnings("ignore", message=".*NotOpenSSLWarning.*")
import requests

from config import DATA_DIR, LOGO_PATH, OUTPUT_HTML


# ── Data loading ─────────────────────────────────────────────────────────────

def read_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        print(f"  Warning: {filename} not found — skipping")
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def encode_logo():
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    return ""



def fetch_image_b64(url):
    """Download an image and return a base64 data URI, or empty string on failure."""
    if not url:
        return ""
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            ct = r.headers.get("Content-Type", "image/jpeg").split(";")[0]
            b64 = base64.b64encode(r.content).decode("ascii")
            return f"data:{ct};base64,{b64}"
    except Exception:
        pass
    return ""


# ── Processing ────────────────────────────────────────────────────────────────

def month_label(date_str):
    s = date_str[:7]
    try:
        return datetime.strptime(s, "%Y-%m").strftime("%b %Y")
    except Exception:
        return s


def detect_post_type(post):
    attachments = post.get("attachments", {}).get("data", [])
    if attachments:
        t = attachments[0].get("type", "")
        mt = attachments[0].get("media_type", "")
        if t in ("photo", "album", "sticker", "animated_image_video", "cover_photo", "profile_media") or mt == "photo":
            return "Photo"
        if t in ("video_inline", "video") or mt == "video":
            return "Video"
        if t == "share":
            return "Link"
    if post.get("full_picture"):
        return "Photo"
    return "Text"


def process_fb(fb_page, fb_fan_history, fb_posts):
    page = fb_page or {}
    fan_hist = sorted(fb_fan_history or [], key=lambda x: x.get("date", ""))
    posts = fb_posts or []

    fan_labels, fan_data = [], []
    for row in fan_hist:
        d = row.get("date", "")
        try:
            fan_labels.append(datetime.strptime(d, "%Y-%m-%d").strftime("%b %d, %Y"))
        except Exception:
            fan_labels.append(d)
        fan_data.append(row.get("fan_count", 0) or 0)

    eng_by_month = defaultdict(lambda: {"reactions": 0, "comments": 0, "shares": 0})
    for p in posts:
        date = p.get("created_time", "")[:7]
        if date:
            lbl = month_label(date)
            eng_by_month[lbl]["reactions"] += p.get("reaction_count", 0) or 0
            eng_by_month[lbl]["comments"]  += p.get("comment_count", 0) or 0
            eng_by_month[lbl]["shares"]    += p.get("share_count", 0) or 0
    eng_labels = sorted(eng_by_month.keys(),
                        key=lambda x: datetime.strptime(x, "%b %Y"))
    reactions_series = [eng_by_month[m]["reactions"] for m in eng_labels]
    comments_series  = [eng_by_month[m]["comments"]  for m in eng_labels]
    shares_series    = [eng_by_month[m]["shares"]    for m in eng_labels]
    engagements      = [
        eng_by_month[m]["reactions"] + eng_by_month[m]["comments"] + eng_by_month[m]["shares"]
        for m in eng_labels
    ]

    type_counts = defaultdict(lambda: defaultdict(int))
    for p in posts:
        date = p.get("created_time", "")[:7]
        if date:
            lbl = month_label(date)
            type_counts[lbl][detect_post_type(p)] += 1

    type_months = sorted(type_counts.keys(),
                         key=lambda x: datetime.strptime(x, "%b %Y"))
    post_types = ["Photo", "Video", "Link", "Text"]
    type_series = {t: [type_counts[m].get(t, 0) for m in type_months]
                   for t in post_types}

    def impressions(p):
        return (p.get("reaction_count", 0) or 0) + (p.get("comment_count", 0) or 0)

    top = []
    for p in sorted(posts, key=impressions, reverse=True)[:10]:
        top.append({
            "message":      (p.get("message") or p.get("story") or "")[:220],
            "created_time": p.get("created_time", ""),
            "full_picture": p.get("full_picture", ""),
            "permalink_url":p.get("permalink_url", ""),
            "type":         detect_post_type(p),
            "impressions":  impressions(p),
            "reactions":    p.get("reaction_count", 0) or 0,
            "comments":     p.get("comment_count", 0) or 0,
            "shares":       p.get("share_count", 0) or 0,
        })

    latest_fans = fan_data[-1] if fan_data else page.get("fan_count", 0) or 0
    latest_eng  = engagements[-1] if engagements else None

    return {
        "page":             page,
        "followers":        latest_fans,
        "latest_eng":       latest_eng,
        "fan_labels":       fan_labels,
        "fan_data":         fan_data,
        "eng_labels":       eng_labels,
        "engagements":      engagements,
        "reactions_series": reactions_series,
        "comments_series":  comments_series,
        "shares_series":    shares_series,
        "type_months":      type_months,
        "type_series":      type_series,
        "top_posts":        top,
    }


def process_ig(ig_account, ig_follower_history, ig_insights, ig_media):
    account  = ig_account  or {}
    fol_hist = sorted(ig_follower_history or [], key=lambda x: x.get("date", ""))
    insights = ig_insights or {}
    media    = ig_media     or []

    fol_labels, fol_counts = [], []
    for row in fol_hist:
        d = row.get("date", "")
        try:
            fol_labels.append(datetime.strptime(d, "%Y-%m-%d").strftime("%b %d, %Y"))
        except Exception:
            fol_labels.append(d)
        fol_counts.append(row.get("followers_count", 0) or 0)

    new_fol_labels, new_fol_counts = [], []
    fhist = insights.get("follower_history") or {}
    for item in fhist.get("data", []):
        if item.get("name") == "follower_count":
            for val in item.get("values", []):
                date = val.get("end_time", "")[:10]
                if date:
                    try:
                        new_fol_labels.append(datetime.strptime(date, "%Y-%m-%d").strftime("%b %d"))
                    except Exception:
                        new_fol_labels.append(date)
                    new_fol_counts.append(val.get("value", 0))

    reach_by_month = defaultdict(int)
    for m in media:
        date = m.get("timestamp", "")[:7]
        if date:
            lbl = month_label(date)
            reach_by_month[lbl] += m.get("reach", 0) or 0

    ig_reach_labels = sorted(reach_by_month.keys(),
                             key=lambda x: datetime.strptime(x, "%b %Y"))
    ig_reach_vals   = [reach_by_month[m] for m in ig_reach_labels]

    monthly_media = defaultdict(lambda: {"count": 0, "likes": 0, "comments": 0})
    for m in media:
        date = m.get("timestamp", "")[:7]
        if date:
            lbl = month_label(date)
            monthly_media[lbl]["count"]    += 1
            monthly_media[lbl]["likes"]    += m.get("like_count", 0) or 0
            monthly_media[lbl]["comments"] += m.get("comments_count", 0) or 0

    ig_months = sorted(monthly_media.keys(),
                       key=lambda x: datetime.strptime(x, "%b %Y"))
    ig_post_counts     = [monthly_media[m]["count"]    for m in ig_months]
    ig_likes_series    = [monthly_media[m]["likes"]    for m in ig_months]
    ig_comments_series = [monthly_media[m]["comments"] for m in ig_months]

    def score(m):
        return (m.get("reach", 0) or 0) + (m.get("like_count", 0) or 0)

    top = []
    for m in sorted(media, key=score, reverse=True)[:10]:
        mtype = m.get("media_product_type") or m.get("media_type", "")
        is_video = mtype in ("REELS", "VIDEO") or m.get("media_type") == "VIDEO"
        if is_video:
            thumb = m.get("thumbnail_url") or m.get("media_url") or ""
        else:
            thumb = m.get("media_url") or m.get("thumbnail_url") or ""
        top.append({
            "caption":    (m.get("caption") or "")[:220],
            "media_type": mtype,
            "media_url":  thumb,
            "timestamp":  m.get("timestamp", ""),
            "permalink":  m.get("permalink", ""),
            "likes":      m.get("like_count", 0) or 0,
            "comments":   m.get("comments_count", 0) or 0,
            "reach":      m.get("reach", 0) or 0,
            "saved":      m.get("saved", 0) or 0,
            "shares":     m.get("shares", 0) or 0,
            "reposts":    m.get("reposts", 0) or 0,
            "views":      m.get("views", 0) or 0,
        })

    current_followers = account.get("followers_count", 0) or 0
    recent_reach = next((v for v in reversed(ig_reach_vals) if v), 0)

    return {
        "account":         account,
        "followers":       current_followers,
        "latest_reach":    recent_reach,
        "fol_labels":      fol_labels,
        "fol_counts":      fol_counts,
        "new_fol_labels":  new_fol_labels,
        "new_fol_counts":  new_fol_counts,
        "reach_labels":    ig_reach_labels,
        "reach_vals":      ig_reach_vals,
        "ig_months":       ig_months,
        "post_counts":     ig_post_counts,
        "likes_series":    ig_likes_series,
        "comments_series": ig_comments_series,
        "top_posts":       top,
    }


# ── Mailchimp processing ──────────────────────────────────────────────────────

def process_mailchimp(campaigns):
    campaigns = campaigns or []
    # Reverse so charts show oldest → newest left to right
    ordered = list(reversed(campaigns))
    labels      = [(c["subject"] or c["title"] or "")[:35] for c in ordered]
    open_rates  = [round(c.get("open_rate", 0) * 100, 1) for c in ordered]
    click_rates = [round(c.get("click_rate", 0) * 100, 1) for c in ordered]
    avg_open  = round(sum(open_rates)  / len(open_rates),  1) if open_rates  else 0
    avg_click = round(sum(click_rates) / len(click_rates), 1) if click_rates else 0
    return {
        "campaigns":   ordered,
        "labels":      labels,
        "open_rates":  open_rates,
        "click_rates": click_rates,
        "avg_open":    avg_open,
        "avg_click":   avg_click,
    }


# ── HTML generation ───────────────────────────────────────────────────────────

def generate_html(fb, ig, mc, logo_uri, generated, failed=None):
    data_json = json.dumps({"fb": fb, "ig": ig, "mc": mc}, ensure_ascii=False)
    logo_tag = (f'<img src="{logo_uri}" class="header-logo" alt="PYS">'
                if logo_uri else
                '<span class="header-logo-text">PYS</span>')

    if failed:
        items = "".join(f"<li>{f}</li>" for f in failed)
        error_banner = (
            f'<div style="background:#fff3cd;border-left:4px solid #f0a500;'
            f'padding:12px 16px;margin:16px auto;max-width:1200px;border-radius:6px;'
            f'font-family:sans-serif;font-size:14px;">'
            f'<strong>⚠️ Data warning:</strong> The following could not be refreshed and '
            f'are showing the last available data: <ul style="margin:6px 0 0 0;padding-left:20px">{items}</ul></div>'
        )
    else:
        error_banner = ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>Pensacola Youth Soccer — Social Media Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Muli:wght@400;600;700;800&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
:root {{
  --primary:   #1B3A6B;
  --accent:    #2D8A4E;
  --dark:      #1f2937;
  --green:     #2D8A4E;
  --orange:    #F59E0B;
  --cyan:      #0EA5E9;
  --gray:      #8C8C8C;
  --bg:        #f3f4f6;
  --card-bg:   #ffffff;
  --shadow:    0 1px 3px rgba(0,0,0,.08), 0 2px 8px rgba(0,0,0,.04);
  --radius:    10px;
  --fb:        #1877F2;
  --ig:        #E1306C;
}}
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Muli', sans-serif; background: var(--bg); color: var(--dark); line-height: 1.5; }}

/* Header */
.header {{
  background: var(--primary); color: #fff;
  padding: 18px 32px; display: flex; align-items: center; gap: 20px; flex-wrap: wrap;
}}
.header-logo {{ height: 44px; }}
.header-logo-text {{ font-size: 22px; font-weight: 800; }}
.header-title {{ font-size: 20px; font-weight: 700; flex: 1; }}
.header-subtitle {{ font-size: 13px; color: #a8c4e8; font-weight: 600; }}
.header-date {{ font-size: 12px; color: #a8c4e8; white-space: nowrap; }}

/* Layout */
.container {{ max-width: 1360px; margin: 0 auto; padding: 24px 20px 56px; }}

/* Scorecards */
.scorecards {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 16px; margin-bottom: 32px;
}}
.scorecard {{
  background: var(--card-bg); border-radius: var(--radius);
  box-shadow: var(--shadow); padding: 20px 22px; text-align: center;
}}
.scorecard .value {{
  font-size: 34px; font-weight: 800; color: var(--primary); line-height: 1.1;
}}
.scorecard .label {{
  font-size: 12px; color: var(--gray); font-weight: 700;
  text-transform: uppercase; letter-spacing: .5px; margin-top: 6px;
}}
.scorecard .platform-tag {{
  display: inline-block; padding: 2px 9px; border-radius: 10px;
  font-size: 11px; font-weight: 700; margin-bottom: 8px;
}}
.tag-fb {{ background: #e8f0fd; color: var(--fb); }}
.tag-ig {{ background: #fde8ef; color: var(--ig); }}
.tag-mc {{ background: #e0f5f3; color: #00A99D; }}

/* Section headers */
.section-header {{
  display: flex; align-items: center; gap: 12px;
  margin: 36px 0 18px;
}}
.section-header .platform-icon {{
  width: 36px; height: 36px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px;
}}
.section-header.fb .platform-icon {{ background: var(--fb); }}
.section-header.ig .platform-icon {{ background: linear-gradient(135deg,#f09433,#e6683c,#dc2743,#cc2366,#bc1888); }}
.section-header h2 {{ font-size: 20px; font-weight: 800; color: var(--dark); }}

/* Chart grid */
.chart-row {{
  display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;
}}
.chart-row.triple {{ grid-template-columns: 1fr 1fr 1fr; }}
.chart-card {{
  background: var(--card-bg); border-radius: var(--radius);
  box-shadow: var(--shadow); padding: 20px 24px;
}}
.chart-card h3 {{
  font-size: 14px; font-weight: 700; color: var(--dark);
  text-transform: uppercase; letter-spacing: .4px; margin-bottom: 16px;
}}
.chart-card canvas {{ width: 100% !important; }}

/* Post grid */
.posts-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 18px; margin-bottom: 8px;
}}
.post-card {{
  background: var(--card-bg); border-radius: var(--radius);
  box-shadow: var(--shadow); overflow: hidden;
  display: flex; flex-direction: column;
}}
.post-thumb {{
  width: 100%; aspect-ratio: 4/3; object-fit: cover;
  background: #e5e7eb; display: block;
}}
.post-thumb-placeholder {{
  width: 100%; aspect-ratio: 4/3; background: #e5e7eb;
  display: flex; align-items: center; justify-content: center;
  color: #bbb; font-size: 28px;
}}
.post-body {{ padding: 12px 14px; flex: 1; display: flex; flex-direction: column; gap: 8px; }}
.post-meta {{
  display: flex; align-items: center; gap: 8px;
  font-size: 11px; color: var(--gray); font-weight: 600;
}}
.post-type-badge {{
  padding: 2px 7px; border-radius: 8px; font-size: 10px; font-weight: 700;
}}
.badge-photo    {{ background: #e8f0fd; color: #1877F2; }}
.badge-video    {{ background: #e7f9e8; color: #1a7a1f; }}
.badge-link     {{ background: #fff3e0; color: #e65100; }}
.badge-text     {{ background: #f0f0f0; color: #555; }}
.badge-reels    {{ background: #fde8ef; color: var(--ig); }}
.badge-carousel {{ background: #f3e8fd; color: #7b1fa2; }}
.post-caption {{
  font-size: 13px; color: #444; line-height: 1.45;
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
  overflow: hidden; flex: 1;
}}
.post-stats {{
  display: flex; gap: 14px; font-size: 12px; font-weight: 600;
  color: var(--gray); padding-top: 8px; border-top: 1px solid #f0f0f0;
  flex-wrap: wrap;
}}
.post-stat {{ display: flex; align-items: center; gap: 4px; }}
.post-link {{ text-decoration: none; color: inherit; }}
.post-link:hover .post-card {{ box-shadow: 0 4px 16px rgba(0,0,0,.12); }}

/* Mailchimp campaign table */
.mc-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
.mc-table th {{
  text-align: left; font-size: 11px; font-weight: 700; color: var(--gray);
  text-transform: uppercase; letter-spacing: .4px;
  padding: 0 12px 10px; border-bottom: 2px solid #f0f0f0;
}}
.mc-table td {{ padding: 10px 12px; border-bottom: 1px solid #f7f7f7; vertical-align: middle; }}
.mc-table tr:last-child td {{ border-bottom: none; }}
.mc-table tr:hover td {{ background: #fafafa; }}
.mc-subject {{ font-weight: 600; color: var(--dark); max-width: 320px; }}
.mc-rate-bar {{ display: flex; align-items: center; gap: 8px; }}
.mc-bar {{ height: 6px; border-radius: 3px; min-width: 2px; }}
.mc-bar-open  {{ background: #00A99D; }}
.mc-bar-click {{ background: var(--orange); }}

/* Responsive */
@media (max-width: 900px) {{
  .chart-row, .chart-row.triple {{ grid-template-columns: 1fr; }}
  .posts-grid {{ grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); }}
}}
@media (max-width: 600px) {{
  .header {{ padding: 14px 16px; }}
  .container {{ padding: 16px 12px 40px; }}
  .scorecards {{ grid-template-columns: 1fr 1fr; }}
}}
</style>
</head>
<body>

{error_banner}
<header class="header">
  {logo_tag}
  <div style="flex:1">
    <div class="header-title">Social Media Dashboard</div>
    <div class="header-subtitle">Pensacola Youth Soccer</div>
  </div>
  <span class="header-date">Generated {generated}</span>
</header>

<div class="container">

  <!-- Scorecards -->
  <div class="scorecards" id="scorecards"></div>

  <!-- Facebook -->
  <div class="section-header fb">
    <div class="platform-icon">f</div>
    <h2>Facebook</h2>
  </div>

  <div class="chart-row">
    <div class="chart-card"><h3>Follower Growth <span style="font-weight:400;color:var(--gray);font-size:12px">(weekly · 90 days)</span></h3><canvas id="fbFansChart"></canvas></div>
    <div class="chart-card"><h3>Monthly Reach</h3><canvas id="fbReachChart"></canvas></div>
  </div>
  <div class="chart-row">
    <div class="chart-card"><h3>Post Engagements by Month</h3><canvas id="fbEngChart"></canvas></div>
    <div class="chart-card"><h3>Posts by Type</h3><canvas id="fbTypeChart"></canvas></div>
  </div>

  <div class="section-header fb" style="margin-top:28px;margin-bottom:14px;">
    <h2 style="font-size:16px;font-weight:700;">Top Facebook Posts</h2>
  </div>
  <div class="posts-grid" id="fbPosts"></div>

  <!-- Instagram -->
  <div class="section-header ig" style="margin-top:44px;">
    <div class="platform-icon">📷</div>
    <h2>Instagram</h2>
  </div>

  <div class="chart-row">
    <div class="chart-card"><h3>Follower Growth <span style="font-weight:400;color:var(--gray);font-size:12px">(weekly · 90 days)</span></h3><canvas id="igFolChart"></canvas></div>
    <div class="chart-card"><h3>Monthly Reach</h3><canvas id="igReachChart"></canvas></div>
  </div>
  <div class="chart-row">
    <div class="chart-card"><h3>Monthly Interactions</h3><canvas id="igIntChart"></canvas></div>
    <div class="chart-card"><h3>Posts per Month</h3><canvas id="igPostChart"></canvas></div>
  </div>

  <div class="section-header ig" style="margin-top:28px;margin-bottom:14px;">
    <h2 style="font-size:16px;font-weight:700;">Top Instagram Posts</h2>
  </div>
  <div class="posts-grid" id="igPosts"></div>

  <!-- Mailchimp -->
  <div class="section-header" style="margin-top:44px;">
    <div class="platform-icon" style="background:#00A99D;font-size:20px;">📧</div>
    <h2>Mailchimp Email Campaigns</h2>
  </div>

  <div class="chart-row">
    <div class="chart-card"><h3>Open Rate per Campaign <span style="font-weight:400;color:var(--gray);font-size:12px">(recent 10, oldest → newest)</span></h3><canvas id="mcOpenChart"></canvas></div>
    <div class="chart-card"><h3>Click Rate per Campaign</h3><canvas id="mcClickChart"></canvas></div>
  </div>

  <div class="chart-card" style="margin-bottom:20px;">
    <table class="mc-table" id="mcTable"></table>
  </div>

</div><!-- /container -->

<script>
const DATA = {data_json};

function fmt(n) {{
  n = n || 0;
  if (n >= 1000000) return (n/1000000).toFixed(1) + 'M';
  if (n >= 1000)    return (n/1000).toFixed(1) + 'K';
  return n.toLocaleString();
}}

function fmtDate(s) {{
  if (!s) return '';
  try {{
    return new Date(s).toLocaleDateString('en-US', {{month:'short', day:'numeric', year:'numeric'}});
  }} catch(e) {{ return s.slice(0,10); }}
}}

function badgeClass(type) {{
  const t = (type||'').toUpperCase();
  if (t === 'PHOTO')          return 'badge-photo';
  if (t === 'VIDEO')          return 'badge-video';
  if (t === 'LINK')           return 'badge-link';
  if (t === 'REELS')          return 'badge-reels';
  if (t === 'CAROUSEL_ALBUM') return 'badge-carousel';
  return 'badge-text';
}}

function badgeLabel(type) {{
  const map = {{
    PHOTO:'Photo', VIDEO:'Video', LINK:'Link', TEXT:'Text',
    REELS:'Reel', CAROUSEL_ALBUM:'Carousel', IMAGE:'Photo',
  }};
  return map[(type||'').toUpperCase()] || type || 'Post';
}}

Chart.defaults.font.family = "'Muli', sans-serif";
Chart.defaults.font.size   = 12;
Chart.defaults.color       = '#8C8C8C';

const FB_BLUE  = '#1877F2';
const IG_PINK  = '#E1306C';
const PRIMARY  = '#1B3A6B';
const ACCENT   = '#2D8A4E';
const ORANGE   = '#F59E0B';
const GRAY     = '#C0C0C0';

function lineChart(id, labels, datasets, opts) {{
  new Chart(document.getElementById(id), {{
    type: 'line',
    data: {{ labels, datasets }},
    options: {{
      responsive: true,
      plugins: {{ legend: {{ display: datasets.length > 1 }} }},
      scales: {{
        x: {{ grid: {{ display: false }} }},
        y: {{ grid: {{ color: '#f0f0f0' }}, ...(opts||{{}}) }},
      }},
    }},
  }});
}}

function barChart(id, labels, datasets, stacked) {{
  new Chart(document.getElementById(id), {{
    type: 'bar',
    data: {{ labels, datasets }},
    options: {{
      responsive: true,
      plugins: {{ legend: {{ display: stacked || datasets.length > 1 }} }},
      scales: {{
        x: {{ stacked: !!stacked, grid: {{ display: false }} }},
        y: {{ stacked: !!stacked, grid: {{ color: '#f0f0f0' }} }},
      }},
    }},
  }});
}}

function ds(label, data, color, fill) {{
  return {{
    label, data,
    borderColor: color, backgroundColor: fill || color + '22',
    borderWidth: 2, pointRadius: 3, fill: !!fill, tension: 0.3,
  }};
}}

function barDs(label, data, color) {{
  return {{ label, data, backgroundColor: color, borderRadius: 4 }};
}}

function weeklySlice(labels, values) {{
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - 90);
  const lbl = [], val = [];
  for (let i = 0; i < labels.length; i++) {{
    if (new Date(labels[i]) >= cutoff) {{ lbl.push(labels[i]); val.push(values[i]); }}
  }}
  const wLbl = [], wVal = [];
  for (let i = 0; i < lbl.length; i += 7) {{ wLbl.push(lbl[i]); wVal.push(val[i]); }}
  if (lbl.length && wLbl[wLbl.length - 1] !== lbl[lbl.length - 1]) {{
    wLbl.push(lbl[lbl.length - 1]); wVal.push(val[val.length - 1]);
  }}
  return {{ labels: wLbl, values: wVal }};
}}

function renderScorecards() {{
  const fb = DATA.fb, ig = DATA.ig;
  const mc = DATA.mc || {{}};
  const cards = [
    {{ tag:'fb', value: fmt(fb.followers),                                 label:'Facebook Followers' }},
    {{ tag:'fb', value: fb.latest_eng != null ? fmt(fb.latest_eng) : '—', label:'FB Engagements (Last Month)' }},
    {{ tag:'ig', value: fmt(ig.followers),                                 label:'Instagram Followers' }},
    {{ tag:'ig', value: ig.latest_reach ? fmt(ig.latest_reach) : '—',     label:'IG Reach (Recent Month)' }},
    {{ tag:'mc', value: mc.avg_open  ? mc.avg_open  + '%' : '—',          label:'Avg Email Open Rate' }},
    {{ tag:'mc', value: mc.avg_click ? mc.avg_click + '%' : '—',          label:'Avg Email Click Rate' }},
  ];
  document.getElementById('scorecards').innerHTML = cards.map(c => `
    <div class="scorecard">
      <div class="platform-tag tag-${{c.tag}}">${{c.tag === 'fb' ? 'Facebook' : c.tag === 'ig' ? 'Instagram' : 'Email'}}</div>
      <div class="value">${{c.value}}</div>
      <div class="label">${{c.label}}</div>
    </div>
  `).join('');
}}

function noDataCard(canvasId, msg) {{
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  canvas.style.display = 'none';
  const note = document.createElement('div');
  note.style.cssText = 'color:#aaa;font-size:13px;text-align:center;padding:32px 16px;line-height:1.6;';
  note.innerHTML = msg;
  canvas.parentNode.appendChild(note);
}}

function renderFBCharts() {{
  const fb = DATA.fb;

  if (fb.fan_data && fb.fan_data.length) {{
    const fbFol = weeklySlice(fb.fan_labels, fb.fan_data);
    lineChart('fbFansChart', fbFol.labels,
      [ds('Followers', fbFol.values, FB_BLUE, FB_BLUE + '18')],
      {{ suggestedMin: fbFol.values.length ? Math.min(...fbFol.values) * 0.98 : 0 }}
    );
    if (fbFol.labels.length <= 2) {{
      const note = document.createElement('p');
      note.style.cssText = 'font-size:11px;color:#aaa;margin-top:8px;text-align:center;';
      note.textContent = 'Run fetch.py daily to build trend history';
      document.getElementById('fbFansChart').parentNode.appendChild(note);
    }}
  }} else {{
    noDataCard('fbFansChart', 'No follower history yet.<br>Run fetch.py daily to build this chart.');
  }}

  if (fb.eng_labels && fb.eng_labels.length) {{
    document.getElementById('fbReachChart').closest('.chart-card').querySelector('h3').textContent = 'Engagement Breakdown';
    barChart('fbReachChart', fb.eng_labels,
      [
        barDs('Reactions', fb.reactions_series || [], FB_BLUE),
        barDs('Comments',  fb.comments_series  || [], PRIMARY),
        barDs('Shares',    fb.shares_series    || [], ORANGE),
      ],
      true
    );
  }} else {{
    noDataCard('fbReachChart', '📊 No engagement data yet');
  }}

  if (fb.engagements && fb.engagements.length) {{
    barChart('fbEngChart', fb.eng_labels,
      [barDs('Total Engagements', fb.engagements, PRIMARY + 'cc')]
    );
  }} else {{
    noDataCard('fbEngChart', '📊 No post engagement data<br><small style="color:#bbb">Post data could not be retrieved.<br>Check API permissions in Meta Developer Console.</small>');
  }}

  if (fb.type_months && fb.type_months.length) {{
    const ts = fb.type_series || {{}};
    barChart('fbTypeChart', fb.type_months,
      [
        barDs('Photo', ts.Photo || [], FB_BLUE),
        barDs('Video', ts.Video || [], ACCENT),
        barDs('Link',  ts.Link  || [], ORANGE),
        barDs('Text',  ts.Text  || [], GRAY),
      ],
      true
    );
  }} else {{
    noDataCard('fbTypeChart', '📊 No post data<br><small style="color:#bbb">Post data could not be retrieved.<br>Check API permissions in Meta Developer Console.</small>');
  }}
}}

function renderIGCharts() {{
  const ig = DATA.ig;

  if (ig.fol_counts && ig.fol_counts.length) {{
    const igFol = weeklySlice(ig.fol_labels, ig.fol_counts);
    lineChart('igFolChart', igFol.labels,
      [ds('Followers', igFol.values, IG_PINK, IG_PINK + '18')],
      {{ suggestedMin: igFol.values.length ? Math.min(...igFol.values) * 0.98 : 0 }}
    );
    if (igFol.labels.length <= 2) {{
      const note = document.createElement('p');
      note.style.cssText = 'font-size:11px;color:#aaa;margin-top:8px;text-align:center;';
      note.textContent = 'Run fetch.py daily to build trend history';
      document.getElementById('igFolChart').parentNode.appendChild(note);
    }}
  }} else if (ig.new_fol_counts && ig.new_fol_counts.length) {{
    const igNewFol = weeklySlice(ig.new_fol_labels, ig.new_fol_counts);
    lineChart('igFolChart', igNewFol.labels,
      [ds('New Followers', igNewFol.values, IG_PINK, IG_PINK + '18')]
    );
  }} else {{
    noDataCard('igFolChart', 'No follower history yet.<br>Run fetch.py daily to build this chart.');
  }}

  if (ig.reach_vals && ig.reach_vals.length) {{
    barChart('igReachChart', ig.reach_labels,
      [barDs('Reach', ig.reach_vals, IG_PINK + 'cc')]
    );
  }} else {{
    noDataCard('igReachChart', '📊 No reach data available');
  }}

  barChart('igIntChart', ig.ig_months,
    [
      barDs('Likes',    ig.likes_series,    IG_PINK),
      barDs('Comments', ig.comments_series, ORANGE),
    ],
    true
  );

  barChart('igPostChart', ig.ig_months,
    [barDs('Posts', ig.post_counts, ACCENT + 'cc')]
  );
}}

function fbPostCard(p) {{
  const thumb = p.full_picture
    ? `<img class="post-thumb" src="${{p.full_picture}}" alt="" loading="lazy" onerror="this.parentNode.innerHTML='<div class=post-thumb-placeholder>🖼</div>'">`
    : `<div class="post-thumb-placeholder">🖼</div>`;
  const stats = [
    p.reactions  && `<span class="post-stat">❤️ ${{fmt(p.reactions)}}</span>`,
    p.comments   && `<span class="post-stat">💬 ${{fmt(p.comments)}}</span>`,
    p.shares     && `<span class="post-stat">↗ ${{fmt(p.shares)}}</span>`,
  ].filter(Boolean).join('');
  const href = p.permalink_url || '#';
  return `
    <a class="post-link" href="${{href}}" target="_blank" rel="noopener">
      <div class="post-card">
        ${{thumb}}
        <div class="post-body">
          <div class="post-meta">
            <span class="post-type-badge ${{badgeClass(p.type)}}">${{badgeLabel(p.type)}}</span>
            <span>${{fmtDate(p.created_time)}}</span>
          </div>
          <div class="post-caption">${{p.message || '(no caption)'}}</div>
          <div class="post-stats">${{stats}}</div>
        </div>
      </div>
    </a>`;
}}

function igPostCard(p) {{
  const thumb = p.media_url
    ? `<img class="post-thumb" src="${{p.media_url}}" alt="" loading="lazy" onerror="this.parentNode.innerHTML='<div class=post-thumb-placeholder>📷</div>'">`
    : `<div class="post-thumb-placeholder">📷</div>`;
  const stats = [
    p.reach    && `<span class="post-stat">👁 ${{fmt(p.reach)}}</span>`,
    p.likes    && `<span class="post-stat">❤️ ${{fmt(p.likes)}}</span>`,
    p.comments && `<span class="post-stat">💬 ${{fmt(p.comments)}}</span>`,
    p.saved    && `<span class="post-stat">🔖 ${{fmt(p.saved)}}</span>`,
    p.shares   && `<span class="post-stat">↗ ${{fmt(p.shares)}}</span>`,
    p.reposts  && `<span class="post-stat">🔁 ${{fmt(p.reposts)}}</span>`,
    p.views    && `<span class="post-stat">▶️ ${{fmt(p.views)}}</span>`,
  ].filter(Boolean).join('');
  const href = p.permalink || '#';
  return `
    <a class="post-link" href="${{href}}" target="_blank" rel="noopener">
      <div class="post-card">
        ${{thumb}}
        <div class="post-body">
          <div class="post-meta">
            <span class="post-type-badge ${{badgeClass(p.media_type)}}">${{badgeLabel(p.media_type)}}</span>
            <span>${{fmtDate(p.timestamp)}}</span>
          </div>
          <div class="post-caption">${{p.caption || '(no caption)'}}</div>
          <div class="post-stats">${{stats}}</div>
        </div>
      </div>
    </a>`;
}}

const MC_TEAL   = '#00A99D';
const MC_TEAL2  = '#00A99D88';

function renderMCCharts() {{
  const mc = DATA.mc;
  if (!mc || !mc.labels || !mc.labels.length) {{
    noDataCard('mcOpenChart',  'No Mailchimp data yet.');
    noDataCard('mcClickChart', 'No Mailchimp data yet.');
    return;
  }}

  barChart('mcOpenChart',  mc.labels, [barDs('Open Rate (%)',  mc.open_rates,  MC_TEAL)]);
  barChart('mcClickChart', mc.labels, [barDs('Click Rate (%)', mc.click_rates, ORANGE)]);

  const rows = [...(mc.campaigns || [])].reverse().map(c => {{
    const openPct  = (c.open_rate  * 100).toFixed(1);
    const clickPct = (c.click_rate * 100).toFixed(1);
    const openBar  = Math.round(c.open_rate  * 120);
    const clickBar = Math.round(c.click_rate * 120);
    const date = c.send_time ? new Date(c.send_time).toLocaleDateString('en-US', {{month:'short', day:'numeric', year:'numeric'}}) : '—';
    return `<tr>
      <td class="mc-subject">${{c.subject || '(no subject)'}}</td>
      <td style="color:var(--gray)">${{date}}</td>
      <td style="text-align:right">${{(c.emails_sent||0).toLocaleString()}}</td>
      <td>
        <div class="mc-rate-bar">
          <div class="mc-bar mc-bar-open" style="width:${{openBar}}px"></div>
          <span style="font-weight:700;color:#00A99D">${{openPct}}%</span>
        </div>
      </td>
      <td>
        <div class="mc-rate-bar">
          <div class="mc-bar mc-bar-click" style="width:${{clickBar}}px"></div>
          <span style="font-weight:700;color:${{ORANGE}}">${{clickPct}}%</span>
        </div>
      </td>
    </tr>`;
  }}).join('');

  document.getElementById('mcTable').innerHTML = `
    <thead><tr>
      <th>Subject</th><th>Date</th><th style="text-align:right">Sent</th>
      <th>Open Rate</th><th>Click Rate</th>
    </tr></thead>
    <tbody>${{rows}}</tbody>`;
}}

renderScorecards();
renderFBCharts();
renderIGCharts();
renderMCCharts();
const fbTopPosts = DATA.fb.top_posts || [];
document.getElementById('fbPosts').innerHTML = fbTopPosts.length
  ? fbTopPosts.map(fbPostCard).join('')
  : '<div style="color:#aaa;font-size:13px;padding:24px 0;">No Facebook post data available. Check API permissions in Meta Developer Console — the app may need <strong>pages_read_user_content</strong> permission.</div>';
document.getElementById('igPosts').innerHTML = (DATA.ig.top_posts||[]).map(igPostCard).join('');
</script>
</body>
</html>"""


# ── Cloud Storage ─────────────────────────────────────────────────────────────

GCS_BUCKET  = "pys-social-dashboard"
GCS_OBJECT  = "dashboard.html"
GCS_PROJECT = "dashboard-494217"
GCS_URL     = f"https://storage.googleapis.com/{GCS_BUCKET}/{GCS_OBJECT}"


def upload_to_gcs(html_path):
    """Upload dashboard.html to Cloud Storage as a public file."""
    from googleapiclient.http import MediaFileUpload
    from gcs_auth import get_storage_service

    storage = get_storage_service()

    try:
        storage.buckets().insert(
            project=GCS_PROJECT,
            predefinedAcl="publicRead",
            predefinedDefaultObjectAcl="publicRead",
            body={
                "name": GCS_BUCKET,
                "location": "US",
                "iamConfiguration": {
                    "uniformBucketLevelAccess": {"enabled": False},
                },
            },
        ).execute()
        print(f"  Created bucket: {GCS_BUCKET}")
    except Exception as e:
        if "409" in str(e) or "conflict" in str(e).lower():
            pass  # already exists
        else:
            raise

    media = MediaFileUpload(html_path, mimetype="text/html", resumable=True)
    storage.objects().insert(
        bucket=GCS_BUCKET,
        name=GCS_OBJECT,
        predefinedAcl="publicRead",
        body={"cacheControl": "no-cache", "contentType": "text/html"},
        media_body=media,
    ).execute()
    print(f"  Uploaded → {GCS_URL}")
    return GCS_URL


def upload_robots_txt():
    """Upload robots.txt blocking all crawlers."""
    import tempfile
    from googleapiclient.http import MediaFileUpload
    from gcs_auth import get_storage_service

    storage = get_storage_service()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("User-agent: *\nDisallow: /\n")
        tmp_path = f.name
    try:
        media = MediaFileUpload(tmp_path, mimetype="text/plain")
        storage.objects().insert(
            bucket=GCS_BUCKET,
            name="robots.txt",
            predefinedAcl="publicRead",
            body={"cacheControl": "public, max-age=86400", "contentType": "text/plain"},
            media_body=media,
        ).execute()
        print("  Uploaded robots.txt (no indexing)")
    finally:
        os.unlink(tmp_path)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--open",   action="store_true", help="Open in browser after generating")
    parser.add_argument("--upload", action="store_true", help="Upload to Google Cloud Storage")
    args = parser.parse_args()

    print("Reading data files...")
    fb_page          = read_json("fb_page.json")
    fb_fan_history   = read_json("fb_fan_history.json")
    fb_posts         = read_json("fb_posts.json")
    ig_account       = read_json("ig_account.json")
    ig_follower_hist = read_json("ig_follower_history.json")
    ig_insights      = read_json("ig_insights.json")
    ig_media         = read_json("ig_media.json")
    mc_campaigns     = read_json("mailchimp_campaigns.json")

    print("Processing...")
    fb = process_fb(fb_page, fb_fan_history, fb_posts)
    ig = process_ig(ig_account, ig_follower_hist, ig_insights, ig_media)
    mc = process_mailchimp(mc_campaigns)

    print("Fetching IG thumbnails...")
    for post in ig["top_posts"]:
        url = post.get("media_url", "")
        if url and not url.startswith("data:"):
            b64 = fetch_image_b64(url)
            if b64:
                post["media_url"] = b64
            time.sleep(0.1)

    logo_uri  = encode_logo()
    generated = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    status_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_status.json")
    failed = []
    if os.path.exists(status_path):
        with open(status_path) as _f:
            _status = json.load(_f)
        failed = _status.get("failed", [])

    print("Generating HTML...")
    html = generate_html(fb, ig, mc, logo_uri, generated, failed=failed)

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved: {OUTPUT_HTML}")

    if args.upload:
        print("Uploading to Cloud Storage...")
        upload_to_gcs(OUTPUT_HTML)
        upload_robots_txt()

    if args.open:
        import webbrowser
        webbrowser.open(f"file://{OUTPUT_HTML}")


if __name__ == "__main__":
    main()
