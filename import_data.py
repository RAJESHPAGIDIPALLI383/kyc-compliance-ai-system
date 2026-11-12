
import csv
import json

from datetime import date, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from database.database import engine
from backend.app.models.entities import (
    CustomerType,
    Customer,
    KYCRequirement,
    Document,
    Verification,
    RiskRating,
    ReviewCase,
    BeneficialOwner,
    Alert,
    AuditEvent,
)

DATA_DIR = Path("data/generated")

IMPORT_ORDER = [
    ("customer_types.csv", CustomerType),
    ("customers.csv", Customer),
    ("kyc_requirements.csv", KYCRequirement),
    ("documents.csv", Document),
    ("verifications.csv", Verification),
    ("risk_ratings.csv", RiskRating),
    ("review_cases.csv", ReviewCase),
    ("beneficial_owners.csv", BeneficialOwner),
    ("alerts.csv", Alert),
    ("audit_events.csv", AuditEvent),
]

DATE_FIELDS = {
    "effective_from", "effective_to", "issue_date",
    "expiry_date", "opened_date", "due_date",
    "closed_date", "created_date",
}

DATETIME_FIELDS = {"verified_at", "created_at"}

BOOLEAN_FIELDS = {"is_mandatory", "is_verified"}

FLOAT_FIELDS = {"risk_score", "ownership_percentage"}


def convert_value(key, value):
    if value is None or value.strip() == "":
        return None

    value = value.strip()

    if key in BOOLEAN_FIELDS:
        return value.lower() in ("true", "1", "yes")

    if key in FLOAT_FIELDS:
        return float(value)

    if key in DATE_FIELDS:
        return date.fromisoformat(value[:10])

    if key in DATETIME_FIELDS:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

    if key == "event_data":
        return json.loads(value)

    return value


def import_csv(session, filename, model):
    file_path = DATA_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(f"Missing file: {file_path}")

    records = []

    with file_path.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            converted = {
                key: convert_value(key, value)
                for key, value in row.items()
            }
            records.append(converted)

    for start in range(0, len(records), 1000):
        batch = records[start:start + 1000]
        session.bulk_insert_mappings(model, batch)

    print(f"{filename}: {len(records)} records imported")


def main():
    print("\nKYC DATABASE DATA IMPORT")
    print("========================")

    with Session(engine) as session:
        try:
            for filename, model in IMPORT_ORDER:
                import_csv(session, filename, model)

            session.commit()

            print("\nALL CSV DATA IMPORTED SUCCESSFULLY!")

        except Exception:
            session.rollback()
            raise


if __name__ == "__main__":
    main()
