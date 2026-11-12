
from datetime import date

from sqlalchemy.orm import Session

from backend.app.models.entities import (
    Customer,
    KYCRequirement,
    Document,
    BeneficialOwner,
    ReviewCase,
    RiskRating,
)


def check_customer_compliance(db: Session, customer_id: str):

    customer = db.query(Customer).filter(
        Customer.customer_id == customer_id
    ).first()

    if not customer:
        return {
            "customer_id": customer_id,
            "compliance_status": "NOT_FOUND",
            "errors": ["Customer does not exist"],
        }

    today = date.today()

    risk_rating = db.query(RiskRating).filter(
        RiskRating.customer_id == customer_id
    ).order_by(
        RiskRating.assessed_at.desc()
    ).first()

    risk_level = (
        risk_rating.risk_level
        if risk_rating
        else "UNKNOWN"
    )

    requirements = db.query(KYCRequirement).filter(
        KYCRequirement.customer_type_id == customer.customer_type_id,
        KYCRequirement.is_mandatory.is_(True),
        KYCRequirement.effective_from <= today,
        (
            KYCRequirement.effective_to.is_(None)
            | (KYCRequirement.effective_to >= today)
        ),
    ).all()

    required_types = {
        req.document_type
        for req in requirements
        if req.risk_level in ("ALL", risk_level)
    }

    documents = db.query(Document).filter(
        Document.customer_id == customer_id
    ).all()

    documents_by_type = {}

    for document in documents:
        if document.document_type in required_types:
            documents_by_type.setdefault(
                document.document_type, []
            ).append(document)

    missing_documents = []
    document_issues = []

    for document_type in sorted(required_types):

        matching_documents = documents_by_type.get(
            document_type, []
        )

        if not matching_documents:
            missing_documents.append(document_type)
            continue

        valid_documents = [
            document
            for document in matching_documents
            if document.verification_status == "VERIFIED"
            and (
                document.expiry_date is None
                or document.expiry_date >= today
            )
        ]

        if not valid_documents:

            statuses = {
                document.verification_status
                for document in matching_documents
            }

            expired_exists = any(
                document.verification_status == "VERIFIED"
                and document.expiry_date is not None
                and document.expiry_date < today
                for document in matching_documents
            )

            if expired_exists:
                document_issues.append(
                    f"{document_type} is expired"
                )
            else:
                document_issues.append(
                    f"{document_type} is not verified: "
                    + ", ".join(sorted(statuses))
                )

    owners = db.query(BeneficialOwner).filter(
        BeneficialOwner.customer_id == customer_id
    ).all()

    ownership_total = sum(
        owner.ownership_percentage for owner in owners
    )

    ownership_issue = (
        customer.customer_type_id == "BUSINESS"
        and ownership_total > 100
    )

    reviews = db.query(ReviewCase).filter(
        ReviewCase.customer_id == customer_id
    ).all()

    overdue_reviews = [
        review.review_case_id
        for review in reviews
        if review.status != "CLOSED"
        and review.due_date < today
    ]

    closed_without_resolution = [
        review.review_case_id
        for review in reviews
        if review.status == "CLOSED"
        and not review.resolution
    ]

    errors = []

    if missing_documents:
        errors.append(
            "Missing mandatory documents: "
            + ", ".join(missing_documents)
        )

    if document_issues:
        errors.extend(document_issues)

    if ownership_issue:
        errors.append(
            f"Ownership exceeds 100%: {ownership_total:.2f}%"
        )

    if overdue_reviews:
        errors.append(
            "Overdue review cases: "
            + ", ".join(overdue_reviews)
        )

    if closed_without_resolution:
        errors.append(
            "Closed reviews without resolution: "
            + ", ".join(closed_without_resolution)
        )

    return {
        "customer_id": customer_id,
        "customer_name": customer.full_name,
        "customer_type": customer.customer_type_id,
        "risk_level": risk_level,
        "compliance_status": (
            "COMPLIANT" if not errors else "NON_COMPLIANT"
        ),
        "required_documents": sorted(required_types),
        "missing_documents": missing_documents,
        "document_issues": document_issues,
        "ownership_percentage_total": round(
            ownership_total, 2
        ),
        "ownership_issue": ownership_issue,
        "overdue_review_cases": overdue_reviews,
        "closed_reviews_without_resolution": (
            closed_without_resolution
        ),
        "errors": errors,
    }
