import requests
import json
import os
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path

load_dotenv()
APP_ID = os.getenv("ADZUNA_APP_ID")
APP_KEY = os.getenv("ADZUNA_APP_KEY")

if not APP_ID or not APP_KEY:
    raise ValueError("Adzuna API credentials are missing.")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_FOLDER = PROJECT_ROOT / "data" / "raw"

def fetch_jobs(country="gb", what="data engineer", results_per_page=50):
    try:
        response = requests.get(
            f"https://api.adzuna.com/v1/api/jobs/{country}/search/1", 
            params={
                "app_id": APP_ID,
                "app_key": APP_KEY,
                "results_per_page": results_per_page,
                "what": what
            },
            timeout=30
        )

        response.raise_for_status()

    except requests.RequestException as error:
        print(f"Error occurred: {error}")
        return None

    else:
        return response.json()


def save_raw(data, folder=RAW_FOLDER):
    if data is None:
        print("No data to save - skipping.")
        return

    try:
        # Use a timestamp to keep each raw API response as a separate file.
        current_datetime = datetime.now().strftime("%Y%m%dT%H%M%S")

        os.makedirs(folder, exist_ok=True)
        filename = os.path.join(folder, f"adzuna_jobs_{current_datetime}.json")

        with open(filename, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
        return filename
    except Exception as error:
            print(f"Error occurred: {error}")
            return None

if __name__ == "__main__":
    data = fetch_jobs()
    
    if data is not None:
        saved_file = save_raw(data)
        if saved_file:
            print(f"Saved to {saved_file}")
    else:
        print("Fetch failed - nothing to save.")
