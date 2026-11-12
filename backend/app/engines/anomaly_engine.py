
from datetime import date

from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from backend.app.models.entities import (
    Customer,
    Document,
    BeneficialOwner,
    ReviewCase,
    RiskRating,
    KYCRequirement,
)


def detect_anomalies(db: Session):

    anomalies = []
    today = date.today()

    expired_documents = (
        db.query(Document)
        .filter(
            Document.verification_status == "VERIFIED",
            Document.expiry_date.isnot(None),
            Document.expiry_date < today,
        )
        .all()
    )

    for document in expired_documents:
        anomalies.append({
            "anomaly_type": "EXPIRED_DOCUMENT_MARKED_VALID",
            "entity_id": document.document_id,
            "related_entity_id": document.customer_id,
            "evidence": (
                f"Document expired on {document.expiry_date} "
                "but verification status is VERIFIED"
            ),
        })

    approved_customers = (
        db.query(Customer)
        .filter(Customer.status == "APPROVED")
        .all()
    )

    for customer in approved_customers:

        risk = (
            db.query(RiskRating)
            .filter(RiskRating.customer_id == customer.customer_id)
            .order_by(RiskRating.assessed_at.desc())
            .first()
        )

        risk_level = risk.risk_level if risk else "UNKNOWN"

        requirements = (
            db.query(KYCRequirement)
            .filter(
                KYCRequirement.customer_type_id == customer.customer_type_id,
                KYCRequirement.is_mandatory.is_(True),
                KYCRequirement.effective_from <= today,
                (
                    KYCRequirement.effective_to.is_(None)
                    | (KYCRequirement.effective_to >= today)
                ),
            )
            .all()
        )

        required_types = {
            req.document_type
            for req in requirements
            if req.risk_level in ("ALL", risk_level)
        }

        customer_documents = (
            db.query(Document)
            .filter(Document.customer_id == customer.customer_id)
            .all()
        )

        issues = []

        for document_type in required_types:

            matching = [
                document
                for document in customer_documents
                if document.document_type == document_type
            ]

            valid = [
                document
                for document in matching
                if document.verification_status == "VERIFIED"
                and (
                    document.expiry_date is None
                    or document.expiry_date >= today
                )
            ]

            if not valid:
                if not matching:
                    issues.append(f"{document_type} missing")
                else:
                    issues.append(f"{document_type} invalid")

        if issues:
            anomalies.append({
                "anomaly_type": "APPROVED_WITH_MISSING_EVIDENCE",
                "entity_id": customer.customer_id,
                "related_entity_id": None,
                "evidence": (
                    "Approved customer has incomplete "
                    "mandatory evidence: " + ", ".join(issues)
                ),
            })

    ownership_rows = (
        db.query(
            BeneficialOwner.customer_id,
            func.sum(BeneficialOwner.ownership_percentage)
        )
        .join(
            Customer,
            Customer.customer_id == BeneficialOwner.customer_id
        )
        .filter(Customer.customer_type_id == "BUSINESS")
        .group_by(BeneficialOwner.customer_id)
        .having(func.sum(BeneficialOwner.ownership_percentage) > 100)
        .all()
    )

    for customer_id, ownership_total in ownership_rows:
        anomalies.append({
            "anomaly_type": "OWNERSHIP_EXCEEDS_100",
            "entity_id": customer_id,
            "related_entity_id": None,
            "evidence": f"Total ownership is {ownership_total:.2f}%",
        })

    closed_reviews = (
        db.query(ReviewCase)
        .filter(
            ReviewCase.status == "CLOSED",
            (
                ReviewCase.resolution.is_(None)
                | (ReviewCase.resolution == "")
            ),
        )
        .all()
    )

    for review in closed_reviews:
        anomalies.append({
            "anomaly_type": "REVIEW_CLOSED_WITHOUT_RESOLUTION",
            "entity_id": review.review_case_id,
            "related_entity_id": review.customer_id,
            "evidence": (
                "Review status is CLOSED "
                "but resolution is missing"
            ),
        })

    duplicate_rows = (
        db.query(
            Document.document_number,
            func.count(distinct(Document.customer_id)).label("customer_count")
        )
        .filter(
            Document.document_number.isnot(None),
            Document.document_number != "",
        )
        .group_by(Document.document_number)
        .having(func.count(distinct(Document.customer_id)) > 1)
        .all()
    )

    for document_number, customer_count in duplicate_rows:

        matching_documents = (
            db.query(Document)
            .filter(Document.document_number == document_number)
            .all()
        )

        for index, doc1 in enumerate(matching_documents):
            for doc2 in matching_documents[index + 1:]:

                if doc1.customer_id != doc2.customer_id:
                    anomalies.append({
                        "anomaly_type": "DUPLICATE_DOCUMENT_ACROSS_CUSTOMERS",
                        "entity_id": doc1.document_id,
                        "related_entity_id": doc2.document_id,
                        "evidence": (
                            f"Document number {document_number} "
                            f"is shared by {doc1.customer_id} "
                            f"and {doc2.customer_id}"
                        ),
                    })

    return anomalies
