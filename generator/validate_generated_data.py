
import pandas as pd

from generator.config import (
    GENERATED_DIR,
    GROUND_TRUTH_DIR,
    CUSTOMER_COUNT,
    DOCUMENT_COUNT,
    REVIEW_CASE_COUNT
)

checks = []


def record_check(name, passed, details):
    checks.append({
        "check_name": name,
        "status": "PASS" if passed else "FAIL",
        "details": str(details)
    })


def load_csv(filename):
    path = GENERATED_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Required file not found: {path}"
        )

    return pd.read_csv(path)


customers = load_csv("customers.csv")
customer_types = load_csv("customer_types.csv")
documents = load_csv("documents.csv")
requirements = load_csv("kyc_requirements.csv")
risk_ratings = load_csv("risk_ratings.csv")
owners = load_csv("beneficial_owners.csv")
reviews = load_csv("review_cases.csv")
alerts = load_csv("alerts.csv")
verifications = load_csv("verifications.csv")
audit_events = load_csv("audit_events.csv")

ground_truth = pd.read_csv(
    GROUND_TRUTH_DIR / "anomaly_ground_truth.csv"
)

TODAY = pd.Timestamp("2026-11-12")

required_anomalies = {
    "EXPIRED_DOCUMENT_MARKED_VALID",
    "APPROVED_WITH_MISSING_EVIDENCE",
    "OWNERSHIP_EXCEEDS_100",
    "REVIEW_CLOSED_WITHOUT_RESOLUTION",
    "DUPLICATE_DOCUMENT_ACROSS_CUSTOMERS"
}

found_anomalies = set(
    ground_truth["anomaly_type"].dropna()
)


# 1. Primary key validation.
datasets = {
    "customers": (customers, "customer_id"),
    "documents": (documents, "document_id"),
    "requirements": (requirements, "requirement_id"),
    "risk_ratings": (risk_ratings, "risk_rating_id"),
    "owners": (owners, "owner_id"),
    "reviews": (reviews, "review_case_id"),
    "alerts": (alerts, "alert_id"),
    "verifications": (verifications, "verification_id"),
    "audit_events": (audit_events, "audit_event_id")
}

for name, (df, column) in datasets.items():

    passed = (
        column in df.columns
        and df[column].notna().all()
        and df[column].is_unique
    )

    record_check(
        f"{name}_primary_key",
        passed,
        f"{df[column].nunique()} unique IDs / {len(df)} rows"
    )


# 2. Customer foreign keys.
customer_ids = set(customers["customer_id"])

for name, df in [
    ("documents", documents),
    ("risk_ratings", risk_ratings),
    ("owners", owners),
    ("reviews", reviews),
    ("alerts", alerts),
    ("audit_events", audit_events)
]:

    passed = df["customer_id"].isin(customer_ids).all()

    record_check(
        f"{name}_customer_foreign_key",
        passed,
        "All customer references exist"
        if passed
        else "Invalid customer references found"
    )


# 3. Customer type foreign key.
customer_type_ids = set(
    customer_types["customer_type_id"]
)

passed = customers[
    "customer_type_id"
].isin(customer_type_ids).all()

record_check(
    "customer_type_foreign_key",
    passed,
    "All customer types exist"
    if passed
    else "Invalid customer type references"
)


# 4. Verification document foreign key and uniqueness.
document_ids = set(documents["document_id"])

passed = (
    verifications["document_id"].isin(document_ids).all()
    and verifications["document_id"].is_unique
)

record_check(
    "verification_document_relationship",
    passed,
    "Every document has at most one verification record"
)


# 5. Document dates.
documents["issue_date"] = pd.to_datetime(
    documents["issue_date"],
    errors="coerce"
)

documents["expiry_date"] = pd.to_datetime(
    documents["expiry_date"],
    errors="coerce"
)

valid_dates = (
    documents["issue_date"].notna().all()
    and (
        documents["expiry_date"].isna()
        | (
            documents["expiry_date"]
            > documents["issue_date"]
        )
    ).all()
)

record_check(
    "document_date_validation",
    valid_dates,
    "Issue dates and expiry dates are valid"
)


# 6. Document status values.
valid_document_statuses = {
    "VERIFIED",
    "PENDING",
    "REJECTED"
}

passed = set(
    documents["verification_status"].dropna()
).issubset(valid_document_statuses)

record_check(
    "document_status_values",
    passed,
    "Document verification statuses use supported values"
)


# 7. Risk score validation.
passed = risk_ratings[
    "risk_score"
].between(0, 100).all()

record_check(
    "risk_score_range",
    passed,
    "All risk scores are between 0 and 100"
)


# 8. Individual owner percentage validation.
passed = owners[
    "ownership_percentage"
].between(0, 100).all()

record_check(
    "individual_ownership_percentage",
    passed,
    "Each individual ownership percentage is between 0 and 100"
)


# 9. Required document type coverage.
requirements["effective_from"] = pd.to_datetime(
    requirements["effective_from"],
    errors="coerce"
)

requirements["effective_to"] = pd.to_datetime(
    requirements["effective_to"],
    errors="coerce"
)

risk_lookup = risk_ratings.set_index(
    "customer_id"
)["risk_level"].to_dict()

missing_type_customers = []

for customer in customers.itertuples(index=False):

    customer_risk = risk_lookup.get(
        customer.customer_id
    )

    required = requirements[
        (requirements["customer_type_id"] == customer.customer_type_id)
        & (requirements["is_mandatory"].astype(str).str.lower().isin([
            "true", "1"
        ]))
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

    required_types = set(
        required["document_type"]
    )

    customer_docs = documents[
        documents["customer_id"] == customer.customer_id
    ]

    available_types = set(
        customer_docs["document_type"]
    )

    if not required_types.issubset(available_types):
        missing_type_customers.append(
            customer.customer_id
        )

record_check(
    "mandatory_document_type_coverage",
    len(missing_type_customers) == 0,
    f"{len(missing_type_customers)} customers missing required document types"
)


# 10. Actual evidence completeness and approved anomaly.
approved_missing_evidence = []

for customer in customers.itertuples(index=False):

    if customer.status != "APPROVED":
        continue

    customer_risk = risk_lookup[customer.customer_id]

    required = requirements[
        (requirements["customer_type_id"] == customer.customer_type_id)
        & (requirements["is_mandatory"].astype(str).str.lower().isin([
            "true", "1"
        ]))
        & (
            requirements["risk_level"].isin([
                "ALL",
                customer_risk
            ])
        )
    ]

    valid_docs = documents[
        (documents["customer_id"] == customer.customer_id)
        & (documents["verification_status"] == "VERIFIED")
        & (
            documents["expiry_date"].isna()
            | (documents["expiry_date"] >= TODAY)
        )
    ]

    missing = (
        set(required["document_type"])
        - set(valid_docs["document_type"])
    )

    if missing:
        approved_missing_evidence.append(
            customer.customer_id
        )

approved_anomaly_expected = (
    "APPROVED_WITH_MISSING_EVIDENCE"
    in found_anomalies
)

record_check(
    "approved_missing_evidence_anomaly",
    (
        approved_anomaly_expected
        and len(approved_missing_evidence) == 1
    ),
    (
        f"{len(approved_missing_evidence)} approved customers "
        "have missing valid mandatory evidence"
    )
)


# 11. Expired VERIFIED anomaly.
expired_verified = documents[
    (documents["expiry_date"] < TODAY)
    & (documents["verification_status"] == "VERIFIED")
]

passed = (
    len(expired_verified) == 1
    and "EXPIRED_DOCUMENT_MARKED_VALID" in found_anomalies
)

record_check(
    "expired_verified_anomaly",
    passed,
    f"Found {len(expired_verified)} expired VERIFIED documents"
)


# 12. Ownership anomaly.
ownership_totals = owners.groupby(
    "customer_id"
)["ownership_percentage"].sum()

ownership_anomalies = ownership_totals[
    ownership_totals > 100.01
]

passed = (
    len(ownership_anomalies) == 1
    and "OWNERSHIP_EXCEEDS_100" in found_anomalies
)

record_check(
    "ownership_reconciliation_anomaly",
    passed,
    f"Found {len(ownership_anomalies)} ownership groups above 100%"
)


# 13. Review lifecycle anomaly.
closed_reviews = reviews[
    reviews["status"] == "CLOSED"
]

closed_without_resolution = closed_reviews[
    closed_reviews["resolution"].isna()
    | (
        closed_reviews["resolution"]
        .astype(str)
        .str.strip() == ""
    )
]

passed = (
    len(closed_without_resolution) == 1
    and "REVIEW_CLOSED_WITHOUT_RESOLUTION" in found_anomalies
)

record_check(
    "review_resolution_lifecycle",
    passed,
    f"Found {len(closed_without_resolution)} closed reviews without resolution"
)


# 14. Cross-customer duplicate anomaly.
duplicate_groups = documents.groupby(
    "document_number"
)["customer_id"].nunique()

duplicate_groups = duplicate_groups[
    duplicate_groups > 1
]

passed = (
    len(duplicate_groups) == 1
    and "DUPLICATE_DOCUMENT_ACROSS_CUSTOMERS" in found_anomalies
)

record_check(
    "duplicate_document_across_customers",
    passed,
    f"Found {len(duplicate_groups)} cross-customer duplicate groups"
)


# 15. Ground truth coverage.
passed = (
    required_anomalies == found_anomalies
    and len(ground_truth) == 5
)

record_check(
    "ground_truth_coverage",
    passed,
    f"{len(found_anomalies)}/5 required anomaly types recorded"
)


# 16. Dataset volumes.
volume_checks = [
    ("customer_count", len(customers), CUSTOMER_COUNT),
    ("document_count", len(documents), DOCUMENT_COUNT),
    ("risk_rating_count", len(risk_ratings), CUSTOMER_COUNT),
    ("review_case_count", len(reviews), REVIEW_CASE_COUNT),
    ("verification_count", len(verifications), DOCUMENT_COUNT)
]

for name, actual, expected in volume_checks:

    record_check(
        name,
        actual == expected,
        f"Expected {expected}, found {actual}"
    )


# 17. Business ownership coverage.
business_ids = set(
    customers.loc[
        customers["customer_type_id"] == "BUSINESS",
        "customer_id"
    ]
)

owner_customer_ids = set(
    owners["customer_id"]
)

passed = business_ids.issubset(owner_customer_ids)

record_check(
    "business_ownership_coverage",
    passed,
    f"{len(business_ids & owner_customer_ids)}/{len(business_ids)} businesses have owner records"
)


# 18. Missing-evidence alert for approved anomaly.
anomaly_row = ground_truth[
    ground_truth["anomaly_type"]
    == "APPROVED_WITH_MISSING_EVIDENCE"
]

if not anomaly_row.empty:

    anomaly_customer_id = anomaly_row.iloc[0]["entity_id"]

    anomaly_alert = alerts[
        (alerts["customer_id"] == anomaly_customer_id)
        & (alerts["alert_type"] == "MISSING_EVIDENCE")
    ]

    passed = not anomaly_alert.empty

else:
    passed = False

record_check(
    "approved_anomaly_missing_evidence_alert",
    passed,
    "Approved missing-evidence customer has a corresponding alert"
)


# Save validation report.
report = pd.DataFrame(checks)

report.to_csv(
    GROUND_TRUTH_DIR / "validation_report.csv",
    index=False
)

passed_count = int(
    (report["status"] == "PASS").sum()
)

failed_count = int(
    (report["status"] == "FAIL").sum()
)

print("\nGENERATED DATA VALIDATION COMPLETE!")
print(report.to_string(index=False))

print("\nTotal checks:", len(report))
print("Passed:", passed_count)
print("Failed:", failed_count)

print(
    "\nValidation report:",
    GROUND_TRUTH_DIR / "validation_report.csv"
)

if failed_count:
    print("\nFAILED CHECKS:")

    for _, row in report[
        report["status"] == "FAIL"
    ].iterrows():
        print("-", row["check_name"], ":", row["details"])

else:
    print("\nALL VALIDATION CHECKS PASSED!")
