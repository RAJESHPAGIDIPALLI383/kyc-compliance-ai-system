
import csv
from pathlib import Path

from sqlalchemy import inspect
from database.database import engine

DATA_DIR = Path("data/generated")

TABLE_FILES = {
    "customer_types": "customer_types.csv",
    "customers": "customers.csv",
    "kyc_requirements": "kyc_requirements.csv",
    "documents": "documents.csv",
    "verifications": "verifications.csv",
    "risk_ratings": "risk_ratings.csv",
    "review_cases": "review_cases.csv",
    "beneficial_owners": "beneficial_owners.csv",
    "alerts": "alerts.csv",
    "audit_events": "audit_events.csv",
}

inspector = inspect(engine)

print("\nCSV AND DATABASE COLUMN AUDIT")
print("==============================")

for table, filename in TABLE_FILES.items():
    path = DATA_DIR / filename

    print(f"\nTABLE: {table}")
    print(f"CSV: {filename}")

    if not path.exists():
        print("FILE MISSING!")
        continue

    with path.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        reader = csv.DictReader(file)
        csv_columns = set(reader.fieldnames or [])

    db_columns = {
        column["name"]
        for column in inspector.get_columns(table)
    }

    print("CSV columns:", sorted(csv_columns))
    print("DB columns:", sorted(db_columns))

    missing = db_columns - csv_columns
    extra = csv_columns - db_columns

    print("Missing CSV columns:", sorted(missing))
    print("Extra CSV columns:", sorted(extra))

    if not missing and not extra:
        print("COLUMN CHECK: PASS")
    else:
        print("COLUMN CHECK: REVIEW REQUIRED")

print("\nAUDIT COMPLETE!")
