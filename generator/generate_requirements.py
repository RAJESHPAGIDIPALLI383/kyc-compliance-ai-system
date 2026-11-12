
import pandas as pd

from generator.config import GENERATED_DIR

requirements = [
    {
        "requirement_id": "KYC-2026-000001",
        "customer_type_id": "INDIVIDUAL",
        "requirement_name": "Identity Proof",
        "document_type": "AADHAAR",
        "risk_level": "ALL",
        "is_mandatory": True,
        "effective_from": "2026-01-01",
        "effective_to": None
    },
    {
        "requirement_id": "KYC-2026-000002",
        "customer_type_id": "INDIVIDUAL",
        "requirement_name": "Permanent Account Number",
        "document_type": "PAN",
        "risk_level": "ALL",
        "is_mandatory": True,
        "effective_from": "2026-01-01",
        "effective_to": None
    },
    {
        "requirement_id": "KYC-2026-000003",
        "customer_type_id": "INDIVIDUAL",
        "requirement_name": "Address Proof",
        "document_type": "ADDRESS_PROOF",
        "risk_level": "ALL",
        "is_mandatory": True,
        "effective_from": "2026-01-01",
        "effective_to": None
    },
    {
        "requirement_id": "KYC-2026-000004",
        "customer_type_id": "INDIVIDUAL",
        "requirement_name": "Additional High Risk Evidence",
        "document_type": "PASSPORT",
        "risk_level": "HIGH",
        "is_mandatory": True,
        "effective_from": "2026-01-01",
        "effective_to": None
    },
    {
        "requirement_id": "KYC-2026-000005",
        "customer_type_id": "BUSINESS",
        "requirement_name": "Business Registration",
        "document_type": "BUSINESS_LICENSE",
        "risk_level": "ALL",
        "is_mandatory": True,
        "effective_from": "2026-01-01",
        "effective_to": None
    },
    {
        "requirement_id": "KYC-2026-000006",
        "customer_type_id": "BUSINESS",
        "requirement_name": "Business PAN",
        "document_type": "PAN",
        "risk_level": "ALL",
        "is_mandatory": True,
        "effective_from": "2026-01-01",
        "effective_to": None
    },
    {
        "requirement_id": "KYC-2026-000007",
        "customer_type_id": "BUSINESS",
        "requirement_name": "Business Address Proof",
        "document_type": "ADDRESS_PROOF",
        "risk_level": "ALL",
        "is_mandatory": True,
        "effective_from": "2026-01-01",
        "effective_to": None
    },
    {
        "requirement_id": "KYC-2026-000008",
        "customer_type_id": "BUSINESS",
        "requirement_name": "Ownership Evidence",
        "document_type": "OWNERSHIP_PROOF",
        "risk_level": "ALL",
        "is_mandatory": True,
        "effective_from": "2026-01-01",
        "effective_to": None
    },
    {
        "requirement_id": "KYC-2026-000009",
        "customer_type_id": "BUSINESS",
        "requirement_name": "Additional High Risk Evidence",
        "document_type": "PASSPORT",
        "risk_level": "HIGH",
        "is_mandatory": True,
        "effective_from": "2026-01-01",
        "effective_to": None
    }
]

df = pd.DataFrame(requirements)

df.to_csv(
    GENERATED_DIR / "kyc_requirements.csv",
    index=False
)

print("KYC REQUIREMENTS GENERATED SUCCESSFULLY!")
print("Total requirements:", len(df))
print("Individual requirements:", len(df[df["customer_type_id"] == "INDIVIDUAL"]))
print("Business requirements:", len(df[df["customer_type_id"] == "BUSINESS"]))
