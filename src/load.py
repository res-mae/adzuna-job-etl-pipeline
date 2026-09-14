import os
import csv
import glob
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_FOLDER = PROJECT_ROOT / "data" / "processed"
REJECTED_FOLDER = PROJECT_ROOT / "data" / "rejected"

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

COLUMNS = [ 
    "id", "title", "company_name", "location_name", "category_label",
    "category_tag", "contract_time", "contract_type", "salary_min", "salary_max",
    "salary_is_predicted", "created", "redirect_url", "description"
]

def get_latest_processed_file(folder=PROCESSED_FOLDER):
    files = glob.glob(os.path.join(folder, "*.csv"))

    if not files:
        raise FileNotFoundError(f"No processed files found in directory {folder}")

    return max(files, key=os.path.getmtime)


def read_processed(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            return list(reader)

    except Exception as e:
        raise ValueError(f"Error occurred while opening the processed file: {e}")

def validate_job(job):
    try:
        cleaned = dict(job)

        # verify `id` is present
        if not cleaned.get("id"):
            return False, "Missing `id`"

        # verify `contract_time` is present
        if not cleaned.get("contract_time"):
            return False, "Missing `contract_time`"

        # verify `contract_type` is present
        if not cleaned.get("contract_type"):
            return False, "Missing `contract_type`"

        # Verify salary values are present and numeric
        try:
            cleaned["salary_min"] = float(cleaned.get("salary_min"))
            cleaned["salary_max"] = float(cleaned.get("salary_max"))
        except ValueError as e:
            return False, "Missing/Invalid salary value"

        # cast `salary_is_predicted` to boolean
        if cleaned.get("salary_is_predicted").lower() not in ("true", "false"):
            return False, "Invalid `salary_is_predicted` value"
        
        cleaned["salary_is_predicted"] = cleaned.get("salary_is_predicted").lower() == "true"

        # cast `created` to timestamp
        try:
            cleaned["created"] = datetime.fromisoformat(cleaned.get("created"))
        except ValueError as e:
            return False, "Invalid `created` value"

        return True, cleaned

    except Exception as e:
        return False, str(e)


def split_valid_invalid(jobs):
    valid_rows = []
    invalid_rows = []

    for job in jobs:
        is_valid, result = validate_job(job)

        if is_valid:
            valid_rows.append(result)
        else:
            invalid_rows.append((job, result))

    return valid_rows, invalid_rows


def log_invalid(invalid_rows, folder=REJECTED_FOLDER):

    if not invalid_rows:
        return None # nothing to log
    
    try:
        current_datetime = datetime.now().strftime("%Y%m%dT%H%M%S")

        os.makedirs(folder, exist_ok=True)
        filename = os.path.join(
            folder,
            f"reject_jobs_{current_datetime}.log"
        )

        with open(filename, "w", encoding="utf-8") as f:
            for job, result in invalid_rows:
                f.write(f"Error: {result} | Job: {job}\n")

        return filename

    except Exception as e:
        print(f"Error occurred while saving the error log file: {e}")
        return None


def build_insert_sql(columns=COLUMNS):
    column_list = ", ".join(columns)
    update_clause = ", ".join(f"{col} = EXCLUDED.{col}" for col in columns if col != "id")

    sql = f"""
        INSERT INTO jobs ({column_list})
        VALUES %s
        ON CONFLICT(id) DO UPDATE SET
        {update_clause}
    """

    return sql


def rows_to_tuples(valid_rows, columns=COLUMNS):
    tuples = []
    
    for row in valid_rows:
        row_tuple = tuple(row[col] for col in columns)
        tuples.append(row_tuple)

    return tuples


def bulk_insert(valid_rows, db_config=DB_CONFIG):
    if not valid_rows:
        print("No valid rows to insert.")
        return False

    sql = build_insert_sql()
    values = rows_to_tuples(valid_rows)

    conn = None

    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()

        execute_values(cur, sql, values)

        conn.commit()
        print(f"Inserted/updated {len(valid_rows)} rows.")

        return True

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Bulk insert failed: {e}")
        return False

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    try:
        latest_processed_file = get_latest_processed_file()
        job_records = read_processed(latest_processed_file)

    except FileNotFoundError as e:
        print(f"No data to load: {e}")

    except ValueError as e:
            print(f"No data to load: {e}")

    else:
        valid_job_records, invalid_job_records = split_valid_invalid(job_records)

        if not valid_job_records:
            print("No records were successfully validated - nothing to load.")
        else:
            inserted_records = bulk_insert(valid_job_records)

            if inserted_records:
                print("Job records were successfully inserted to the database")
            else:
                print("No records were inserted to the database")
                
        if invalid_job_records:
            error_log = log_invalid(invalid_job_records)
            print(f"See error log for invalid job records: {error_log}")
