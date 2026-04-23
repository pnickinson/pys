# Pensacola Youth Soccer — Tools & Dashboards

This repo contains tools and dashboards for Pensacola Youth Soccer (PYS).

---

## `meta/` — Social Media Dashboard

Pulls Facebook + Instagram analytics via the Meta Graph API and generates a
self-contained HTML dashboard hosted on Google Cloud Storage. Runs monthly
on the Raspberry Pi via Cronicle.

**Dashboard:** https://storage.googleapis.com/pys-social-dashboard/dashboard.html

See `meta/README.md` for setup and usage details.

---

## `convert.py` — TeamSnap → TS1 Schedule Converter

Converts TeamSnap schedule exports into the format required for TeamSnap One
(TS1) game imports.

```bash
python3 convert.py <schedule_export.csv> <roster_export.csv>
```

---

## `ts-converter/` — Web-based Schedule Converter

Browser-based version of the schedule converter.

---

## `age-group-calculator.html` — Age Group Calculator

Calculates player age groups based on birth date for PYS registration.

---

## `shop-ad-rotator.html` — Shop Ad Rotator

Rotating ad display for the PYS merch shop.

---

## `coaches/` — Coaches Directory

Coaches contact directory tools.
