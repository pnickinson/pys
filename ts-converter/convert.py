import pandas as pd
import re
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: python3 convert.py <schedule.csv> [roster.csv]")
    sys.exit(1)

input_path = Path(sys.argv[1])
if not input_path.exists():
    print(f"File not found: {input_path}")
    sys.exit(1)

df = pd.read_csv(input_path)

# === TEAM NAME RESOLUTION ===
# If a roster CSV is provided, resolve short schedule names (e.g. "Team 3-Kennedy")
# to full TS1 names (e.g. "Team 3-Brian Kennedy") by matching team number + division.
team_lookup = {}  # (team_number, normalized_division) -> full team name

def normalize_division(div):
    # Handles mismatched formats between schedule and roster exports, e.g.:
    #   schedule: "Under 12-Boys"  →  roster: "Under-12 Boys"
    #   schedule: "Under 10-Boys-Spring"  →  roster: "Under-10 Boys"
    # Strip seasonal suffixes, then hyphens/spaces, then lowercase.
    s = re.sub(r"\b(spring|fall|summer|winter)\b", "", str(div), flags=re.IGNORECASE)
    return re.sub(r"[\s\-]+", "", s).lower()

if len(sys.argv) >= 3:
    roster_path = Path(sys.argv[2])
    if not roster_path.exists():
        print(f"Roster file not found: {roster_path}")
        sys.exit(1)
    roster = pd.read_csv(roster_path, usecols=["Team", "Division"])
    for _, row in roster.drop_duplicates().iterrows():
        m = re.match(r"^Team (\d+)", str(row["Team"]))
        if m:
            key = (m.group(1), normalize_division(row["Division"]))
            team_lookup[key] = str(row["Team"]).strip()

def resolve_team(name, division):
    m = re.match(r"^Team (\d+)", str(name))
    if m:
        key = (m.group(1), normalize_division(division))
        if key in team_lookup:
            return team_lookup[key]
    return name  # fall back to original if no match found

# === TIME & DURATION ===
start_dt = pd.to_datetime(df["Start Date"].astype(str) + " " + df["Start Time"].astype(str))
end_dt   = pd.to_datetime(df["Start Date"].astype(str) + " " + df["End Time"].astype(str))

duration_minutes = (end_dt - start_dt).dt.total_seconds() / 60
df["_Duration"] = duration_minutes.apply(lambda m: f"{int(m)//60:02d}:{int(m)%60:02d}")

# === VENUE MAPPING ===
# Add non-Hitzman venues here once you know their old TeamSnap names.
VENUE_MAP = {
    # "Old Location Name": ("TS1 Venue Name", "TS1 Sub-Venue Name"),
    # Estramadura, Perdido-Southwest, Ashton Brosnaham entries TBD
}

def map_location(location):
    if pd.isna(location):
        return "", ""
    location = str(location).strip()
    if location in VENUE_MAP:
        return VENUE_MAP[location]
    # Hitzman Park fields: "Field 3-A" → "Hitzman Park" / "Field 3A"
    m = re.match(r"^(Field \d+)-([A-D])$", location, re.IGNORECASE)
    if m:
        return "Hitzman Park", f"Field {m.group(1).split()[1]}{m.group(2).upper()}"
    print(f"  WARNING: unmapped location '{location}' — set venue manually in TS1")
    return location, ""

venues, subvenues = zip(*df["Location"].map(map_location))

# === BUILD OUTPUT ===
out = pd.DataFrame()
out["Team 1 Name"]      = [resolve_team(n, d) for n, d in zip(df["Home Team"], df["Division"])]
out["Team 1 Division"]  = df["Division"]
out["Team 1 Type"]      = "Internal"
out["Team 1 Home/Away"] = "Home"
out["Team 2 Name"]      = [resolve_team(n, d) for n, d in zip(df["Away Team"], df["Division"])]
out["Team 2 Division"]  = df["Division"]
out["Team 2 Type"]      = "Internal"
out["Team 2 Home/Away"] = "Away"
out["Date"]             = pd.to_datetime(df["Start Date"]).dt.strftime("%m/%d/%Y")
out["Start Time"]       = start_dt.dt.strftime("%I:%M %p").str.lstrip("0")
out["Duration"]         = df["_Duration"]
out["Arrival Time"]     = "30"
out["Venue"]            = venues
out["Sub-Venue"]        = subvenues

output_dir = input_path.parent / "converted"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / (input_path.stem + "_ts1.csv")
out.to_csv(output_path, index=False)
print(f"Done: {output_path}")
