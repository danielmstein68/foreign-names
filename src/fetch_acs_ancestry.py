"""Download Census ancestry counts (ACS 5-year 2006-2010, table B04006) and
total population (B01003) for every county and every place (city).

Saves to data/raw/acs/ancestry_county.csv and ancestry_place.csv. Run once;
these files are then treated as raw data like the rest of data/raw.
Run:  .venv/bin/python src/fetch_acs_ancestry.py
"""

import json
import os
import sys
import time
import urllib.request

import pandas as pd

from common import RAW

BASE = "https://api.census.gov/data/2010/acs/acs5"
VARS = ["B01003_001E"] + [f"B04006_{i:03d}E" for i in range(1, 110)]
# The Census API needs a free key: https://api.census.gov/data/key_signup.html
# It is read from the environment, never written into the code or the repo.
KEY = os.environ.get("CENSUS_API_KEY", "")

STATES = ["01", "02", "04", "05", "06", "08", "09", "10", "11", "12", "13", "15", "16", "17", "18", "19", "20",
          "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37",
          "38", "39", "40", "41", "42", "44", "45", "46", "47", "48", "49", "50", "51", "53", "54", "55", "56"]


def get(geo: str) -> pd.DataFrame:
    """The API allows 50 variables per request, so fetch in chunks and join."""
    parts = []
    for i in range(0, len(VARS), 45):
        url = f"{BASE}?get={','.join(VARS[i:i + 45])}&{geo}&key={KEY}"
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=120) as r:
                    rows = json.load(r)
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
        df = pd.DataFrame(rows[1:], columns=rows[0])
        keys = [c for c in df.columns if c in ("state", "county", "place")]
        parts.append(df.set_index(keys))
    return pd.concat(parts, axis=1).reset_index()


def main() -> None:
    if not KEY:
        sys.exit("Set the CENSUS_API_KEY environment variable first (free key: "
                 "https://api.census.gov/data/key_signup.html).")
    out = RAW / "acs"
    out.mkdir(exist_ok=True)
    county = get("for=county:*&in=state:*")
    county.to_csv(out / "ancestry_county.csv", index=False)
    places = pd.concat([get(f"for=place:*&in=state:{s}") for s in STATES])
    places.to_csv(out / "ancestry_place.csv", index=False)
    print(f"counties: {len(county):,}, places: {len(places):,}")


if __name__ == "__main__":
    main()
