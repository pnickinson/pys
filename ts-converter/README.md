# PYS TeamSnap → TS1 Schedule Converter

A Python script that converts TeamSnap schedule exports into the format required for TeamSnap One (TS1) game imports.

## Background

When migrating to TeamSnap One, schedule CSVs exported from the old TeamSnap system cannot be imported directly — the column names, date/time formats, and venue structure all need to be remapped. This script handles that conversion automatically.

## What it does

- Remaps column names and order to match the TS1 Import Games template
- Converts dates from `YYYY-MM-DD` to `MM/DD/YYYY`
- Converts times from 24-hour (`17:30:00`) to 12-hour (`5:30 PM`) format
- Calculates game duration from start and end times (rather than using a hardcoded default)
- Maps old field names (e.g. `Field 3-A`) to TS1 venue/sub-venue pairs (e.g. `Hitzman Park` / `Field 3A`)
- Resolves short team names from the schedule (e.g. `Team 3-Kennedy`) to full team names as they exist in TS1 (e.g. `Team 3-Brian Kennedy`) using a roster export

## Requirements

- Python 3
- pandas (`pip install pandas`)

## Usage

Schedules are exported one age group at a time from TeamSnap. Run the script once per age group:

```
python3 convert.py <schedule_export.csv> <roster_export.csv>
```

**Example:**
```
python3 convert.py under-6.csv roster_export_pys_rec_spring_2026.csv
```

This produces a `_ts1.csv` file in the same folder, ready to upload via the TS1 Import Games screen.

The roster file covers all age groups, so the same file is used for every run — only the schedule file changes.

## Venue mapping

Hitzman Park fields are automatically detected and mapped:

| Schedule export | TS1 Venue | TS1 Sub-Venue |
|---|---|---|
| Field 1-A | Hitzman Park | Field 1A |
| Field 2-B | Hitzman Park | Field 2B |
| Field 3-C | Hitzman Park | Field 3C |
| *(etc.)* | | |

Other venues (Estramadura Park, Perdido-Southwest Sports Park, Ashton Brosnaham) can be added to the `VENUE_MAP` dictionary at the top of `convert.py` once their old TeamSnap location names are known.

## Notes

- TS1 may ask you to manually confirm sub-venue mappings on the first import — this is normal
- A team named `Team 6-` with no coach name indicates missing data in TeamSnap registration, not a script error
- The `skipped_entities.csv` file that TS1 generates on a partial import can be re-uploaded to recover skipped rows
