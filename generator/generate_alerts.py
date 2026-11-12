
import pandas as pd

from generator.config import (
    GENERATED_DIR,
    GROUND_TRUTH_DIR,
    AS_OF_DATE
)

TODAY = pd.Timestamp(AS_OF_DATE)
EXPIRY_WARNING_DAYS = (7, 15, 30)

documents = pd.read_csv(
    GENERATED_DIR / "documents.csv"
)

customers = pd.read_csv(
    GENERATED_DIR / "customers.csv"
)

risk_ratings = pd.read_csv(
    GENERATED_DIR / "risk_ratings.csv"
)

review_cases = pd.read_csv(
    GENERATED_DIR / "review_cases.csv"
)

requirements = pd.read_csv(
    GENERATED_DIR / "kyc_requirements.csv"
)

owners = pd.read_csv(
    GENERATED_DIR / "beneficial_owners.csv"
)

documents["expiry_date"] = pd.to_datetime(
    documents["expiry_date"],
    errors="coerce"
)

review_cases["due_date"] = pd.to_datetime(
    review_cases["due_date"],
    errors="coerce"
)

requirements["effective_from"] = pd.to_datetime(
    requirements["effective_from"],
    errors="coerce"
)

requirements["effective_to"] = pd.to_datetime(
    requirements["effective_to"],
    errors="coerce"
)

alerts = []


def is_true(value):
    return str(value).strip().lower() in (
        "true", "1", "yes"
    )


def add_alert(
    customer_id,
    alert_type,
    severity,
    description
):
    alerts.append({
        "alert_id": f"ALT-{len(alerts) + 1:06d}",
        "customer_id": customer_id,
        "alert_type": alert_type,
        "severity": severity,
        "description": description,
        "status": "OPEN",
        "created_date": TODAY.date()
    })


risk_lookup = risk_ratings.set_index(
    "customer_id"
)["risk_level"].to_dict()


# 1. Expired documents.
for doc in documents.itertuples(index=False):

    if pd.notna(doc.expiry_date) and doc.expiry_date < TODAY:

        add_alert(
            doc.customer_id,
            "DOCUMENT_EXPIRED",
            "HIGH",
            f"Document {doc.document_id} expired on {doc.expiry_date.date()}"
        )


# 2. Documents expiring soon.
for doc in documents.itertuples(index=False):

    if pd.isna(doc.expiry_date):
        continue

    days_remaining = (
        doc.expiry_date - TODAY
    ).days

    if not 0 <= days_remaining <= 30:
        continue

    if days_remaining <= 7:
        severity = "HIGH"
        warning_level = 7

    elif days_remaining <= 15:
        severity = "MEDIUM"
        warning_level = 15

    else:
        severity = "LOW"
        warning_level = 30

    add_alert(
        doc.customer_id,
        "DOCUMENT_EXPIRING",
        severity,
        (
            f"Document {doc.document_id} expires in "
            f"{days_remaining} days. "
            f"Warning threshold: {warning_level} days"
        )
    )


# 3. High-risk customers.
for customer_id in risk_ratings.loc[
    risk_ratings["risk_level"] == "HIGH",
    "customer_id"
]:

    add_alert(
        customer_id,
        "HIGH_RISK_CUSTOMER",
        "HIGH",
        "Customer has a HIGH risk rating"
    )


# 4. Overdue reviews.
overdue_reviews = review_cases[
    review_cases["due_date"].notna()
    & (review_cases["due_date"] < TODAY)
    & (review_cases["status"] != "CLOSED")
]

for review in overdue_reviews.itertuples(index=False):

    add_alert(
        review.customer_id,
        "REVIEW_OVERDUE",
        "HIGH",
        f"Review case {review.review_case_id} is overdue"
    )


# 5. Missing valid mandatory evidence.
for customer in customers.itertuples(index=False):

    customer_risk = risk_lookup.get(
        customer.customer_id
    )

    if customer_risk is None:
        raise ValueError(
            f"Missing risk rating for {customer.customer_id}"
        )

    customer_requirements = requirements[
        (requirements["customer_type_id"] == customer.customer_type_id)
        & (requirements["is_mandatory"].apply(is_true))
        & (
            requirements["risk_level"].isin([
                "ALL",
                customer_risk
            ])
        )
        & (
            requirements["effective_from"].isna()
            | (requirements["effective_from"] <= TODAY)
        )
        & (
            requirements["effective_to"].isna()
            | (requirements["effective_to"] >= TODAY)
        )
    ]

    valid_documents = documents[
        (documents["customer_id"] == customer.customer_id)
        & (documents["verification_status"] == "VERIFIED")
        & (
            documents["expiry_date"].isna()
            | (documents["expiry_date"] >= TODAY)
        )
    ]

    required_types = set(
        customer_requirements["document_type"]
    )

    available_types = set(
        valid_documents["document_type"]
    )

    missing_types = required_types - available_types

    if missing_types:

        add_alert(
            customer.customer_id,
            "MISSING_EVIDENCE",
            "HIGH",
            "Missing valid mandatory documents: "
            + ", ".join(sorted(missing_types))
        )


alerts_df = pd.DataFrame(
    alerts,
    columns=[
        "alert_id",
        "customer_id",
        "alert_type",
        "severity",
        "description",
        "status",
        "created_date"
    ]
)

GENERATED_DIR.mkdir(
    parents=True,
    exist_ok=True
)

GROUND_TRUTH_DIR.mkdir(
    parents=True,
    exist_ok=True
)

alerts_df.to_csv(
    GENERATED_DIR / "alerts.csv",
    index=False
)

ground_truth_df = alerts_df[
    alerts_df["alert_type"].isin([
        "DOCUMENT_EXPIRED",
        "DOCUMENT_EXPIRING",
        "HIGH_RISK_CUSTOMER",
        "REVIEW_OVERDUE",
        "MISSING_EVIDENCE"
    ])
].copy()

ground_truth_df["expected_detection"] = True

ground_truth_df.to_csv(
    GROUND_TRUTH_DIR / "alert_ground_truth.csv",
    index=False
)

print("\nALERT DATA GENERATED SUCCESSFULLY!")
print("Total alerts:", len(alerts_df))

if not alerts_df.empty:
    print("\nAlert type distribution:")
    print(alerts_df["alert_type"].value_counts().to_string())

    print("\nSeverity distribution:")
    print(alerts_df["severity"].value_counts().to_string())

    print("\nMissing evidence alerts:",
          (alerts_df["alert_type"] == "MISSING_EVIDENCE").sum())

    print("\nExpired document alerts:",
          (alerts_df["alert_type"] == "DOCUMENT_EXPIRED").sum())

print("\nGround truth records:", len(ground_truth_df))
print("Output:", GENERATED_DIR / "alerts.csv")
