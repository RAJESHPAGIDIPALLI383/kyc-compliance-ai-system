
from datetime import date

from database.database import SessionLocal
from backend.app.models.entities import Document, Verification

db = SessionLocal()

try:
    document_ids = [
        "DOC-CUS-000006-001",
        "DOC-CUS-000014-001",
        "DOC-CUS-000016-001",
    ]

    for document_id in document_ids:

        document = db.query(Document).filter(
            Document.document_id == document_id
        ).first()

        print("\nDOCUMENT:", document_id)

        if not document:
            print("Document not found")
            continue

        print("Customer:", document.customer_id)
        print("Document type:", document.document_type)
        print("Expiry date:", document.expiry_date)
        print("Verification status:", document.verification_status)

        verifications = db.query(Verification).filter(
            Verification.document_id == document_id
        ).all()

        for verification in verifications:
            print("Verification status:", verification.status)
            print("Verified at:", verification.verified_at)

finally:
    db.close()
