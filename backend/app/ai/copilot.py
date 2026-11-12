
from sqlalchemy.orm import Session

from backend.app.engines.kyc_engine import check_customer_compliance
from backend.app.models.entities import (
    Customer,
    RiskRating,
    Alert,
    ReviewCase,
    AuditEvent,
)


def generate_compliance_explanation(
    db: Session,
    customer_id: str
):

    result = check_customer_compliance(db, customer_id)

    if result["compliance_status"] == "NOT_FOUND":
        return {
            "customer_id": customer_id,
            "answer": "Customer not found.",
            "status": "NOT_FOUND",
            "recommendations": []
        }

    customer = (
        db.query(Customer)
        .filter(Customer.customer_id == customer_id)
        .first()
    )

    risk = (
        db.query(RiskRating)
        .filter(RiskRating.customer_id == customer_id)
        .order_by(RiskRating.assessed_at.desc())
        .first()
    )

    alerts = (
        db.query(Alert)
        .filter(
            Alert.customer_id == customer_id,
            Alert.status == "OPEN"
        )
        .all()
    )

    reviews = (
        db.query(ReviewCase)
        .filter(ReviewCase.customer_id == customer_id)
        .all()
    )

    audit_count = (
        db.query(AuditEvent)
        .filter(AuditEvent.customer_id == customer_id)
        .count()
    )

    recommendations = []

    if result["missing_documents"]:
        recommendations.append(
            "Collect missing mandatory documents: "
            + ", ".join(result["missing_documents"])
        )

    if result["document_issues"]:
        recommendations.append(
            "Resolve document verification or expiry issues."
        )

    if result["ownership_issue"]:
        recommendations.append(
            "Review beneficial ownership because the total exceeds 100%."
        )

    if result["overdue_review_cases"]:
        recommendations.append(
            "Complete overdue review cases: "
            + ", ".join(result["overdue_review_cases"])
        )

    if result["closed_reviews_without_resolution"]:
        recommendations.append(
            "Add valid resolution details to closed review cases: "
            + ", ".join(result["closed_reviews_without_resolution"])
        )

    if not recommendations:
        recommendations.append(
            "No compliance issues detected. Continue periodic monitoring."
        )

    status = result["compliance_status"]

    if status == "COMPLIANT":
        answer = (
            f"Customer {customer.full_name} is compliant. "
            "All mandatory compliance checks passed."
        )
    else:
        answer = (
            f"Customer {customer.full_name} is non-compliant. "
            f"{len(result['errors'])} compliance issue(s) detected."
        )

    return {
        "customer_id": customer_id,
        "customer_name": customer.full_name,
        "customer_type": customer.customer_type_id,
        "compliance_status": status,
        "risk_level": risk.risk_level if risk else "UNKNOWN",
        "risk_score": risk.risk_score if risk else None,
        "answer": answer,
        "compliance_issues": result["errors"],
        "missing_documents": result["missing_documents"],
        "document_issues": result["document_issues"],
        "active_alert_count": len(alerts),
        "total_review_cases": len(reviews),
        "audit_event_count": audit_count,
        "recommendations": recommendations,
        "explanation_source": "Deterministic Python compliance rules"
    }


def answer_compliance_question(db: Session, customer_id: str, question: str):

    result = generate_compliance_explanation(db, customer_id)

    if result["compliance_status"] == "NOT_FOUND":
        return {
            "customer_id": customer_id,
            "question": question,
            "answer": "Customer not found.",
            "source": "Python compliance rules"
        }

    q = question.lower()

    if any(word in q for word in ["missing", "document", "evidence"]):
        missing = result["missing_documents"]
        issues = result["document_issues"]

        answer = "Missing documents: " + (
            ", ".join(missing) if missing else "None"
        )

        answer += ". Document issues: " + (
            "; ".join(issues) if issues else "None"
        )

    elif any(word in q for word in ["risk", "score", "rating"]):
        answer = (
            f"Customer risk level is {result['risk_level']} "
            f"with a risk score of {result['risk_score']}."
        )

    elif any(word in q for word in ["recommend", "action", "next", "should"]):
        answer = "Recommended actions: " + "; ".join(
            result["recommendations"]
        )

    elif any(word in q for word in ["audit", "history", "events"]):
        events = (
            db.query(AuditEvent)
            .filter(AuditEvent.customer_id == customer_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(10)
            .all()
        )

        if events:
            answer = "Recent audit history: " + "; ".join(
                f"{event.action} on {event.created_at}"
                for event in events
            )
        else:
            answer = "No audit history found."

    elif any(word in q for word in ["alert", "warning"]):
        alerts = (
            db.query(Alert)
            .filter(
                Alert.customer_id == customer_id,
                Alert.status == "OPEN"
            )
            .all()
        )

        answer = (
            "Active alerts: "
            + "; ".join(
                f"{alert.alert_type}: {alert.description}"
                for alert in alerts
            )
            if alerts
            else "No active alerts found."
        )

    else:
        answer = (
            result["answer"]
            + " Compliance issues: "
            + "; ".join(result["compliance_issues"])
        )

    return {
        "customer_id": customer_id,
        "question": question,
        "answer": answer,
        "compliance_status": result["compliance_status"],
        "risk_level": result["risk_level"],
        "source": "Deterministic Python compliance rules"
    }

