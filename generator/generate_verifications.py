
import random
import pandas as pd

from datetime import datetime, timedelta

from generator.config import (
    RANDOM_SEED,
    GENERATED_DIR
)

random.seed(RANDOM_SEED)

AS_OF_DATE = datetime(2026, 11, 12, 12, 0, 0)

documents = pd.read_csv(
    GENERATED_DIR / "documents.csv"
)

verifications = []

for index, document in enumerate(
    documents.itertuples(index=False),
    start=1
):
    document_status = document.verification_status

    if document_status == "VERIFIED":
        status = "APPROVED"
        remarks = "Document passed synthetic verification rules"

    elif document_status == "REJECTED":
        status = "REJECTED"
        remarks = "Document failed synthetic verification rules"

    else:
        status = "PENDING"
        remarks = "Awaiting document verification"

    verified_at = AS_OF_DATE - timedelta(
        days=random.randint(1, 180)
    )

    if status == "PENDING":
        verified_at = None

    verifications.append({
        "verification_id": f"VER-{index:08d}",
        "document_id": document.document_id,
        "status": status,
        "verifier_role": (
            "COMPLIANCE_OFFICER"
            if index % 2 == 0
            else "KYC_ANALYST"
        ),
        "remarks": remarks,
        "verified_at": verified_at
    })

df = pd.DataFrame(verifications)

df.to_csv(
    GENERATED_DIR / "verifications.csv",
    index=False
)

print("VERIFICATION DATA GENERATED SUCCESSFULLY!")
print("Total verification records:", len(df))

print("\nVerification status distribution:")
print(df["status"].value_counts().to_string())

print("\nUnique documents:", df["document_id"].nunique())
print("Output:", GENERATED_DIR / "verifications.csv")
