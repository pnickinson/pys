import pandas as pd
from datetime import datetime

# === CONFIG ===
INPUT_FILE = "input_schedule.csv"
OUTPUT_FILE = "ts1_output.csv"
DEFAULT_DURATION = "01:00"
DEFAULT_ARRIVAL = "30"

# === HELPER FUNCTIONS ===

def format_date(date_str):
    try:
        dt = pd.to_datetime(date_str)
        return dt.strftime("%m/%d/%Y")
    except:
        return ""

def format_time(time_str):
    try:
        dt = pd.to_datetime(time_str)
        return dt.strftime("%I:%M %p").lower()
    except:
        return ""

def split_location(location):
    if pd.isna(location):
        return "", ""
    
    parts = str(location).split("-")
    if len(parts) >= 2:
        return parts[0].strip(), parts[1].strip()
    else:
        return location.strip(), ""

def extract_division(team_name):
    # Customize if division is embedded (e.g., "U12 Tigers")
    if pd.isna(team_name):
        return ""
    
    words = str(team_name).split()
    for w in words:
        if w.upper().startswith("U") and any(char.isdigit() for char in w):
            return w.upper()
    return ""

# === LOAD DATA ===
df = pd.read_csv(INPUT_FILE)

# === MAP YOUR COLUMNS HERE ===
# Adjust these to match your file!
DATE_COL = "Date"
TIME_COL = "Time"
HOME_COL = "Home Team"
AWAY_COL = "Away Team"
LOCATION_COL = "Location"
DIVISION_COL = None  # Set to column name if exists, else None

# === BUILD OUTPUT ===
output_rows = []

for _, row in df.iterrows():
    team1 = row.get(HOME_COL, "")
    team2 = row.get(AWAY_COL, "")

    date = format_date(row.get(DATE_COL, ""))
    time = format_time(row.get(TIME_COL, ""))

    venue, subvenue = split_location(row.get(LOCATION_COL, ""))

    if DIVISION_COL:
        div1 = div2 = row.get(DIVISION_COL, "")
    else:
        div1 = extract_division(team1)
        div2 = extract_division(team2)

    output_rows.append({
        "Team 1 Name": team1,
        "Team 1 Type": "internal",
        "Team 1 Home/Away": "home",
        "Team 2 Name": team2,
        "Team 2 Type": "internal",
        "Team 2 Home/Away": "away",
        "Date": date,
        "Start Time": time,
        "Duration": DEFAULT_DURATION,
        "Arrival Time": DEFAULT_ARRIVAL,
        "Team 1 Division": div1,
        "Team 2 Division": div2,
        "Venue": venue,
        "Sub-venue": subvenue
    })

# === EXPORT ===
output_df = pd.DataFrame(output_rows)

# Ensure correct column order
columns = [
    "Team 1 Name",
    "Team 1 Type",
    "Team 1 Home/Away",
    "Team 2 Name",
    "Team 2 Type",
    "Team 2 Home/Away",
    "Date",
    "Start Time",
    "Duration",
    "Arrival Time",
    "Team 1 Division",
    "Team 2 Division",
    "Venue",
    "Sub-venue"
]

output_df = output_df[columns]
output_df.to_csv(OUTPUT_FILE, index=False)

print(f"✅ TS1 file created: {OUTPUT_FILE}")