import requests
import json
import os
from datetime import datetime, timezone

MATCHES_URL = "https://api.fifa.com/api/v3/calendar/matches?language=en&count=500&idSeason=285023"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://www.fifa.com/",
}
OUTPUT_PATH = "data/matches.json"


def fetch_with_retries(retries=3):
    last_err = None
    for attempt in range(retries):
        try:
            res = requests.get(MATCHES_URL, headers=HEADERS, timeout=15)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            last_err = str(e)
            print(f"Attempt {attempt + 1} failed: {last_err}")
    raise RuntimeError(f"All {retries} attempts failed. Last error: {last_err}")


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    data = fetch_with_retries()
    payload = {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "results": data.get("Results", []),
    }
    with open(OUTPUT_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Saved {len(payload['results'])} matches to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
