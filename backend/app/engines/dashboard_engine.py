
from collections import defaultdict
from datetime import date

from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from backend.app.models.entities import (
    Customer,
    RiskRating,
    KYCRequirement,
    Document,
    BeneficialOwner,
    ReviewCase,
    Alert,
)

from backend.app.engines.anomaly_engine import detect_anomalies


def get_dashboard_summary(db: Session):

    today = date.today()

    total_customers = (
        db.query(func.count(Customer.customer_id)).scalar() or 0
    )

    high_risk_customers = (
        db.query(func.count(distinct(RiskRating.customer_id)))
        .filter(RiskRating.risk_level == "HIGH")
        .scalar() or 0
    )

    active_alerts = (
        db.query(func.count(Alert.alert_id))
        .filter(Alert.status == "OPEN")
        .scalar() or 0
    )

    open_reviews = (
        db.query(func.count(ReviewCase.review_case_id))
        .filter(ReviewCase.status != "CLOSED")
        .scalar() or 0
    )

    overdue_reviews = (
        db.query(func.count(ReviewCase.review_case_id))
        .filter(
            ReviewCase.status != "CLOSED",
            ReviewCase.due_date < today
        )
        .scalar() or 0
    )

    customers = db.query(Customer).all()

    risk_by_customer = {}

    risk_ratings = (
        db.query(RiskRating)
        .order_by(RiskRating.assessed_at.desc())
        .all()
    )

    for risk in risk_ratings:
        if risk.customer_id not in risk_by_customer:
            risk_by_customer[risk.customer_id] = risk.risk_level

    requirements_by_type = defaultdict(list)

    requirements = (
        db.query(KYCRequirement)
        .filter(
            KYCRequirement.is_mandatory.is_(True),
            KYCRequirement.effective_from <= today,
            (
                KYCRequirement.effective_to.is_(None)
                | (KYCRequirement.effective_to >= today)
            )
        )
        .all()
    )

    for requirement in requirements:
        requirements_by_type[
            requirement.customer_type_id
        ].append(requirement)

    documents_by_customer = defaultdict(list)

    for document in db.query(Document).all():
        documents_by_customer[document.customer_id].append(document)

    ownership_by_customer = defaultdict(float)

    for owner in db.query(BeneficialOwner).all():
        ownership_by_customer[owner.customer_id] += (
            owner.ownership_percentage
        )

    reviews_by_customer = defaultdict(list)

    for review in db.query(ReviewCase).all():
        reviews_by_customer[review.customer_id].append(review)

    compliant_customers = 0
    non_compliant_customers = 0

    for customer in customers:

        risk_level = risk_by_customer.get(
            customer.customer_id,
            "UNKNOWN"
        )

        required_types = {
            requirement.document_type
            for requirement in requirements_by_type[
                customer.customer_type_id
            ]
            if requirement.risk_level in ("ALL", risk_level)
        }

        customer_documents = documents_by_customer[
            customer.customer_id
        ]

        errors_found = False

        for document_type in required_types:

            matching_documents = [
                document
                for document in customer_documents
                if document.document_type == document_type
            ]

            if not matching_documents:
                errors_found = True
                break

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
                errors_found = True
                break

        if (
            customer.customer_type_id == "BUSINESS"
            and ownership_by_customer[customer.customer_id] > 100
        ):
            errors_found = True

        for review in reviews_by_customer[customer.customer_id]:

            if (
                review.status != "CLOSED"
                and review.due_date < today
            ):
                errors_found = True
                break

            if (
                review.status == "CLOSED"
                and not review.resolution
            ):
                errors_found = True
                break

        if errors_found:
            non_compliant_customers += 1
        else:
            compliant_customers += 1

    anomalies = detect_anomalies(db)

    return {
        "total_customers": total_customers,
        "compliant_customers": compliant_customers,
        "non_compliant_customers": non_compliant_customers,
        "high_risk_customers": high_risk_customers,
        "active_alerts": active_alerts,
        "open_reviews": open_reviews,
        "overdue_reviews": overdue_reviews,
        "total_anomalies": len(anomalies),
        "message": "Dashboard metrics loaded successfully"
    }
