
import json
import random
import pandas as pd

from datetime import datetime, timedelta

from generator.config import (
    RANDOM_SEED,
    GENERATED_DIR
)

random.seed(RANDOM_SEED)

AS_OF_DATE = datetime(2026, 11, 12, 12, 0, 0)

audit_events = []


def add_events(
    dataframe,
    entity_type,
    id_column,
    action,
    actor_role,
    customer_column=None
):
    for index, record in enumerate(
        dataframe.to_dict("records"),
        start=1
    ):
        entity_id = str(record[id_column])

        customer_id = (
            str(record[customer_column])
            if customer_column and pd.notna(record[customer_column])
            else None
        )

        event_time = AS_OF_DATE - timedelta(
            minutes=random.randint(1, 500000)
        )

        event_data = {
            "source": "synthetic_generator",
            "entity_type": entity_type,
            "record_id": entity_id,
            "action_details": action
        }

        audit_events.append({
            "audit_event_id": f"AUD-{len(audit_events) + 1:08d}",
            "customer_id": customer_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "actor_role": actor_role,
            "event_data": json.dumps(event_data),
            "created_at": event_time.isoformat()
        })


# 1. Customer events
customers = pd.read_csv(
    GENERATED_DIR / "customers.csv"
)

add_events(
    customers,
    "CUSTOMER",
    "customer_id",
    "CUSTOMER_CREATED",
    "SYSTEM",
    "customer_id"
)


# 2. Document events
documents = pd.read_csv(
    GENERATED_DIR / "documents.csv"
)

add_events(
    documents,
    "DOCUMENT",
    "document_id",
    "DOCUMENT_SUBMITTED",
    "CUSTOMER",
    "customer_id"
)


# 3. Verification events
verifications = pd.read_csv(
    GENERATED_DIR / "verifications.csv"
)

document_customers = documents[
    ["document_id", "customer_id"]
]

verifications = verifications.merge(
    document_customers,
    on="document_id",
    how="left"
)

add_events(
    verifications,
    "VERIFICATION",
    "verification_id",
    "DOCUMENT_VERIFICATION_RECORDED",
    "COMPLIANCE_OFFICER",
    "customer_id"
)


# 4. Risk rating events
risk_ratings = pd.read_csv(
    GENERATED_DIR / "risk_ratings.csv"
)

add_events(
    risk_ratings,
    "RISK_RATING",
    "risk_rating_id",
    "RISK_ASSESSED",
    "RISK_ENGINE",
    "customer_id"
)


# 5. Review case events
review_cases = pd.read_csv(
    GENERATED_DIR / "review_cases.csv"
)

add_events(
    review_cases,
    "REVIEW_CASE",
    "review_case_id",
    "REVIEW_CASE_CREATED",
    "COMPLIANCE_OFFICER",
    "customer_id"
)


# 6. Beneficial owner events
owners = pd.read_csv(
    GENERATED_DIR / "beneficial_owners.csv"
)

add_events(
    owners,
    "BENEFICIAL_OWNER",
    "owner_id",
    "OWNERSHIP_RECORDED",
    "KYC_ANALYST",
    "customer_id"
)


# 7. Alert events
alerts = pd.read_csv(
    GENERATED_DIR / "alerts.csv"
)

add_events(
    alerts,
    "ALERT",
    "alert_id",
    "ALERT_CREATED",
    "COMPLIANCE_ENGINE",
    "customer_id"
)


# Save audit history
audit_df = pd.DataFrame(audit_events)

audit_df.to_csv(
    GENERATED_DIR / "audit_events.csv",
    index=False
)

print("AUDIT EVENTS GENERATED SUCCESSFULLY!")
print("Total audit events:", len(audit_df))

print("\nEntity type distribution:")
print(
    audit_df["entity_type"].value_counts().to_string()
)

print("\nUnique audit event IDs:", audit_df["audit_event_id"].nunique())

print("\nOutput:", GENERATED_DIR / "audit_events.csv")
