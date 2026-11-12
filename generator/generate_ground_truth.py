
import pandas as pd

from generator.config import (
    GENERATED_DIR,
    GROUND_TRUTH_DIR,
    AS_OF_DATE
)

TODAY = pd.Timestamp(AS_OF_DATE)

customers = pd.read_csv(
    GENERATED_DIR / "customers.csv"
)

documents = pd.read_csv(
    GENERATED_DIR / "documents.csv"
)

requirements = pd.read_csv(
    GENERATED_DIR / "kyc_requirements.csv"
)

risk_ratings = pd.read_csv(
    GENERATED_DIR / "risk_ratings.csv"
)

owners = pd.read_csv(
    GENERATED_DIR / "beneficial_owners.csv"
)

reviews = pd.read_csv(
    GENERATED_DIR / "review_cases.csv"
)

documents["expiry_date"] = pd.to_datetime(
    documents["expiry_date"],
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

anomalies = []


def is_true(value):
    return str(value).strip().lower() in (
        "true", "1", "yes"
    )


def add_anomaly(
    anomaly_type,
    entity_id,
    related_entity_id,
    evidence
):
    anomalies.append({
        "anomaly_id": f"GT-{len(anomalies) + 1:03d}",
        "anomaly_type": anomaly_type,
        "entity_id": entity_id,
        "related_entity_id": related_entity_id,
        "expected_detection": True,
        "evidence": evidence
    })


# 1. Expired document marked VERIFIED.
expired_verified = documents[
    (documents["expiry_date"] < TODAY)
    & (documents["verification_status"] == "VERIFIED")
]

if len(expired_verified) != 1:
    raise ValueError(
        f"Expected one expired VERIFIED anomaly, found {len(expired_verified)}"
    )

expired_doc = expired_verified.iloc[0]

add_anomaly(
    "EXPIRED_DOCUMENT_MARKED_VALID",
    expired_doc["document_id"],
    expired_doc["customer_id"],
    f"Expired on {expired_doc['expiry_date'].date()} but marked VERIFIED"
)


# 2. Determine actual evidence completeness.
customer_data = customers.merge(
    risk_ratings[["customer_id", "risk_level"]],
    on="customer_id",
    validate="one_to_one"
)

ownership_totals = owners.groupby(
    "customer_id"
)["ownership_percentage"].sum().to_dict()

missing_by_customer = {}
eligible_by_customer = {}

for customer in customer_data.itertuples(index=False):

    required = requirements[
        (requirements["customer_type_id"] == customer.customer_type_id)
        & (requirements["is_mandatory"].apply(is_true))
        & (
            requirements["risk_level"].isin([
                "ALL",
                customer.risk_level
            ])
        )
        & (requirements["effective_from"] <= TODAY)
        & (
            requirements["effective_to"].isna()
            | (requirements["effective_to"] >= TODAY)
        )
    ]

    required_types = set(
        required["document_type"]
    )

    valid_documents = documents[
        (documents["customer_id"] == customer.customer_id)
        & (documents["verification_status"] == "VERIFIED")
        & (
            documents["expiry_date"].isna()
            | (documents["expiry_date"] >= TODAY)
        )
    ]

    available_types = set(
        valid_documents["document_type"]
    )

    missing_types = required_types - available_types

    missing_by_customer[customer.customer_id] = missing_types

    ownership_valid = True

    if customer.customer_type_id == "BUSINESS":
        total = ownership_totals.get(
            customer.customer_id,
            0
        )

        ownership_valid = abs(total - 100.0) <= 0.01

    eligible_by_customer[customer.customer_id] = (
        not missing_types and ownership_valid
    )


# Synchronize ordinary customer lifecycle status.
for index, customer in customers.iterrows():

    customer_id = customer["customer_id"]

    customers.loc[index, "status"] = (
        "APPROVED"
        if eligible_by_customer[customer_id]
        else "PENDING"
    )


# Select one customer missing actual verified evidence.
candidate_id = None

for customer in customer_data.itertuples(index=False):

    if missing_by_customer[customer.customer_id]:
        candidate_id = customer.customer_id
        break


# Defensive fallback: create a missing-evidence case if none exists.
if candidate_id is None:

    candidate_id = customers.iloc[0]["customer_id"]

    candidate_requirements = requirements[
        (requirements["customer_type_id"] == customers.iloc[0]["customer_type_id"])
        & (requirements["is_mandatory"].apply(is_true))
        & (
            requirements["risk_level"].isin([
                "ALL",
                customer_data.iloc[0]["risk_level"]
            ])
        )
    ]

    required_type = candidate_requirements.iloc[0]["document_type"]

    candidate_document = documents[
        (documents["customer_id"] == candidate_id)
        & (documents["document_type"] == required_type)
    ]

    if candidate_document.empty:
        raise ValueError(
            "Cannot create approved missing-evidence anomaly."
        )

    document_index = candidate_document.index[0]

    if documents.loc[document_index, "document_id"] == expired_doc["document_id"]:
        alternatives = candidate_document[
            candidate_document["document_id"] != expired_doc["document_id"]
        ]

        if alternatives.empty:
            raise ValueError(
                "Cannot preserve expired document anomaly while creating missing evidence."
            )

        document_index = alternatives.index[0]

    documents.loc[
        document_index,
        "verification_status"
    ] = "REJECTED"

    documents.to_csv(
        GENERATED_DIR / "documents.csv",
        index=False
    )

    missing_by_customer[candidate_id] = {required_type}


customers.loc[
    customers["customer_id"] == candidate_id,
    "status"
] = "APPROVED"

missing_types = sorted(
    missing_by_customer[candidate_id]
)

if not missing_types:
    raise ValueError(
        "Approved anomaly customer has no missing evidence."
    )

add_anomaly(
    "APPROVED_WITH_MISSING_EVIDENCE",
    candidate_id,
    "",
    "Approved customer lacks valid mandatory evidence: "
    + ", ".join(missing_types)
)

customers.to_csv(
    GENERATED_DIR / "customers.csv",
    index=False
)


# 3. Ownership percentages exceed 100%.
ownership_totals = owners.groupby(
    "customer_id"
)["ownership_percentage"].sum()

invalid_ownership = ownership_totals[
    ownership_totals > 100.01
]

if len(invalid_ownership) != 1:
    raise ValueError(
        f"Expected one ownership anomaly, found {len(invalid_ownership)}"
    )

owner_customer_id = invalid_ownership.index[0]

add_anomaly(
    "OWNERSHIP_EXCEEDS_100",
    owner_customer_id,
    "",
    f"Total ownership is {invalid_ownership.iloc[0]:.2f}%"
)


# 4. Closed review without resolution.
closed_without_resolution = reviews[
    (reviews["status"] == "CLOSED")
    & (
        reviews["resolution"].isna()
        | (reviews["resolution"].astype(str).str.strip() == "")
    )
]

if len(closed_without_resolution) != 1:
    raise ValueError(
        "Expected exactly one closed review without resolution."
    )

review = closed_without_resolution.iloc[0]

add_anomaly(
    "REVIEW_CLOSED_WITHOUT_RESOLUTION",
    review["review_case_id"],
    review["customer_id"],
    "Review is CLOSED but resolution is missing"
)


# 5. Duplicate document number across unrelated customers.
duplicate_groups = documents.groupby(
    "document_number"
).filter(
    lambda group: group["customer_id"].nunique() > 1
)

if duplicate_groups.empty:

    first_doc = documents.iloc[0]

    second_doc = documents[
        documents["customer_id"] != first_doc["customer_id"]
    ].iloc[0]

    documents.loc[
        documents["document_id"] == second_doc["document_id"],
        "document_number"
    ] = first_doc["document_number"]

    documents.to_csv(
        GENERATED_DIR / "documents.csv",
        index=False
    )

    duplicate_group = documents[
        documents["document_number"] == first_doc["document_number"]
    ]

else:
    duplicate_numbers = duplicate_groups["document_number"].unique()

    if len(duplicate_numbers) != 1:
        raise ValueError(
            "Unexpected multiple cross-customer duplicate groups."
        )

    duplicate_group = duplicate_groups[
        duplicate_groups["document_number"] == duplicate_numbers[0]
    ]

if duplicate_group["customer_id"].nunique() < 2:
    raise ValueError("Duplicate anomaly does not involve two customers.")

first_doc = duplicate_group.iloc[0]
second_doc = duplicate_group[
    duplicate_group["customer_id"] != first_doc["customer_id"]
].iloc[0]

add_anomaly(
    "DUPLICATE_DOCUMENT_ACROSS_CUSTOMERS",
    first_doc["document_id"],
    second_doc["document_id"],
    (
        f"Document number {first_doc['document_number']} is shared by "
        f"{first_doc['customer_id']} and {second_doc['customer_id']}"
    )
)


# Save exactly five anomaly records.
ground_truth_df = pd.DataFrame(anomalies)

if len(ground_truth_df) != 5:
    raise ValueError(
        f"Expected five anomalies, found {len(ground_truth_df)}"
    )

ground_truth_df.to_csv(
    GROUND_TRUTH_DIR / "anomaly_ground_truth.csv",
    index=False
)

print("\nANOMALY GROUND TRUTH GENERATED SUCCESSFULLY!")
print("Total anomalies:", len(ground_truth_df))
print("\nAnomaly distribution:")
print(ground_truth_df["anomaly_type"].value_counts().to_string())

print("\nCustomer status distribution:")
print(customers["status"].value_counts().to_string())

print("\nGround truth:", GROUND_TRUTH_DIR / "anomaly_ground_truth.csv")
