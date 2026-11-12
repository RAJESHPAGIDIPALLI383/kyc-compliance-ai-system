
import random
import pandas as pd

from datetime import date, timedelta
from faker import Faker

from generator.config import (
    RANDOM_SEED,
    DOCUMENT_COUNT,
    GENERATED_DIR,
    AS_OF_DATE
)

AS_OF_DATE = date.fromisoformat(AS_OF_DATE)

random.seed(RANDOM_SEED)

fake = Faker("en_IN")
Faker.seed(RANDOM_SEED)

customers = pd.read_csv(
    GENERATED_DIR / "customers.csv"
)

requirements = pd.read_csv(
    GENERATED_DIR / "kyc_requirements.csv"
)


def is_true(value):
    return str(value).strip().lower() in (
        "true", "1", "yes"
    )


def get_risk_level(customer):
    number = int(customer.customer_id.split("-")[1])

    business_score = (
        15 if customer.customer_type_id == "BUSINESS" else 0
    )

    pattern_score = (number % 5) * 10

    score = min(
        100,
        20 + business_score + pattern_score
    )

    if score >= 70:
        return "HIGH"

    if score >= 40:
        return "MEDIUM"

    return "LOW"


documents = []
document_number = 0

for customer in customers.itertuples(index=False):

    risk_level = get_risk_level(customer)

    customer_requirements = requirements[
        (requirements["customer_type_id"] == customer.customer_type_id)
        & (requirements["is_mandatory"].apply(is_true))
        & (
            requirements["risk_level"].isin([
                "ALL",
                risk_level
            ])
        )
    ]

    required_types = sorted(
        customer_requirements["document_type"].unique()
    )

    if not required_types:
        raise ValueError(
            f"No mandatory requirements for {customer.customer_id}"
        )

    for sequence, document_type in enumerate(
        required_types,
        start=1
    ):

        document_number += 1

        issue_date = fake.date_between(
            start_date="-5y",
            end_date=AS_OF_DATE
        )

        validity_days = random.choice([
            365,
            730,
            1095,
            1825
        ])

        expiry_date = issue_date + timedelta(
            days=validity_days
        )

        days_since_issue = (
            AS_OF_DATE - issue_date
        ).days

        force_expired = (
            random.random() < 0.15
            and days_since_issue > 1
        )

        if force_expired:
            expiry_date = AS_OF_DATE - timedelta(
                days=random.randint(
                    1,
                    min(500, days_since_issue - 1)
                )
            )

        if expiry_date < AS_OF_DATE:
            verification_status = "PENDING"
        else:
            verification_status = random.choices(
                ["VERIFIED", "PENDING", "REJECTED"],
                weights=[75, 15, 10],
                k=1
            )[0]

        documents.append({
            "document_id": (
                f"DOC-{customer.customer_id}-{sequence:03d}"
            ),
            "customer_id": customer.customer_id,
            "document_type": document_type,
            "document_number": (
                f"DOCNO{document_number:08d}"
            ),
            "issue_date": issue_date,
            "expiry_date": expiry_date,
            "verification_status": verification_status,
            "file_reference": (
                f"synthetic/document_{document_number:06d}.pdf"
            )
        })


documents_df = pd.DataFrame(documents)

if len(documents_df) != DOCUMENT_COUNT:
    raise ValueError(
        f"Expected {DOCUMENT_COUNT} documents, "
        f"generated {len(documents_df)}"
    )

expired_documents = documents_df[
    pd.to_datetime(documents_df["expiry_date"]) < pd.Timestamp(AS_OF_DATE)
]

if expired_documents.empty:
    raise ValueError("No expired documents generated.")

# Exactly one intentional expired-but-VERIFIED anomaly.
anomaly_index = expired_documents.index[0]

documents_df.loc[
    anomaly_index,
    "verification_status"
] = "VERIFIED"

documents_df.to_csv(
    GENERATED_DIR / "documents.csv",
    index=False
)

expired_verified_count = (
    (
        pd.to_datetime(documents_df["expiry_date"])
        < pd.Timestamp(AS_OF_DATE)
    )
    & (documents_df["verification_status"] == "VERIFIED")
).sum()

invalid_date_count = (
    pd.to_datetime(documents_df["expiry_date"])
    <= pd.to_datetime(documents_df["issue_date"])
).sum()

business_ids = set(
    customers.loc[
        customers["customer_type_id"] == "BUSINESS",
        "customer_id"
    ]
)

ownership_document_ids = set(
    documents_df.loc[
        documents_df["document_type"] == "OWNERSHIP_PROOF",
        "customer_id"
    ]
)

missing_ownership_documents = (
    business_ids - ownership_document_ids
)

print("\nDOCUMENT DATA GENERATED SUCCESSFULLY!")
print("Total documents:", len(documents_df))
print("Unique customers:", documents_df["customer_id"].nunique())
print("Expired documents:", len(expired_documents))
print("Expired VERIFIED anomalies:", expired_verified_count)
print("Invalid issue/expiry dates:", invalid_date_count)
print(
    "Business ownership proof documents:",
    len(ownership_document_ids)
)

if expired_verified_count != 1:
    raise ValueError(
        "Expected exactly one expired VERIFIED anomaly."
    )

if invalid_date_count != 0:
    raise ValueError(
        "Invalid document dates detected."
    )

if missing_ownership_documents:
    raise ValueError(
        "Business customers missing ownership proof: "
        + str(len(missing_ownership_documents))
    )
