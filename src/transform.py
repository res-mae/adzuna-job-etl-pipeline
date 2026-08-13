import json
import os
import glob
from datetime import datetime
import csv

RAW_FOLDER = os.path.join("..", "data", "raw")
PROCESSED_FOLDER = os.path.join("..", "data", "processed")

def get_latest_raw_file(folder=RAW_FOLDER):
    
    files = glob.glob(os.path.join(folder, "*.json"))

    if not files:
        raise FileNotFoundError("No raw files found in folder.")

    return max(files, key=os.path.getmtime)


def load_raw(filepath):
    try:
        with open(filepath, "r") as f:
            data = json.load(f)

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON file: {filepath}") from e

    return data["results"]


def clean_job(job):
    return {
        "id": job["id"],

        # Remove whitespace
        "title": job.get("title", "").strip(),

        # Flatten company.display_name -> company_name and strip whitespace
        "company_name": job.get("company", {}).get("display_name", "").strip(),

        # Flatten location.display_name -> location_name and strip whitespace
        "location_name": job.get("location", {}).get("display_name", "").strip(),

        # Flatten category.label -> category_label
        "category_label": job.get("category", {}).get("label", ""),

        # Flatten category.tag -> category_tag
        "category_tag": job.get("category", {}).get("tag", ""),

        # Assign "not_specified" if it does not exists
        "contract_time": job.get("contract_time") or "not_specified",

        # Assign "not_specified" if it does not exists
        "contract_type": job.get("contract_type") or "not_specified",

        "salary_min": job["salary_min"],

        "salary_max": job["salary_max"],

        # Convert type from string to boolean
        "salary_is_predicted": bool(int(job["salary_is_predicted"])),

        # Convert from string to datetime
        "created": job["created"],

        # Remove whitespace
        "redirect_url": job.get("redirect_url", "").strip(),

        # Remove whitespace
        "description": job.get("description", "").strip()
    }


def transform(jobs):
    cleaned_jobs = []
    failed_count = 0

    for job in jobs:
        try:
            cleaned = clean_job(job)
            cleaned_jobs.append(cleaned)

        except Exception as e:
            print(f"Failed to clean job {job.get("id", "unknown")}: {e}")
            failed_count += 1

    print(f"Transformed {len(cleaned_jobs)}/{len(jobs)} records ({failed_count} failed)")
    return cleaned_jobs


def save_processed(cleaned_jobs, folder=PROCESSED_FOLDER):
    try:
        current_datetime = datetime.now().strftime("%Y%m%dT%H%M%S")

        os.makedirs(folder, exist_ok=True)
        filename = os.path.join(
            folder, 
            f"proc_jobs_{current_datetime}.csv"
        )

        fieldnames = cleaned_jobs[0].keys()

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerows(cleaned_jobs)
        
        return filename

    except Exception as e:
        print(f"Error occurred while saving: {e}")
        return None


if __name__ == "__main__":
    try:
        latest_file = get_latest_raw_file()
        raw_jobs = load_raw(latest_file)

    except FileNotFoundError as e:
        print(f"No data to process: {e}")

    except ValueError as e:
        print(f"Could not read raw data: {e}")

    else:
        cleaned_jobs = transform(raw_jobs)

        if not cleaned_jobs:
            print("No records were successfully cleaned - nothing to save.")
        else:
            saved_path = save_processed(cleaned_jobs)

            if saved_path is not None:
                print(f"Processed data saved to: {saved_path}")
            else:
                print("Transform succeeded, but saving failed.")

