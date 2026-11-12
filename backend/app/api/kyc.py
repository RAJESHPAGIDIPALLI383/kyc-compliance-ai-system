
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import get_db

from backend.app.engines.kyc_engine import check_customer_compliance
from backend.app.engines.anomaly_engine import detect_anomalies
from backend.app.engines.dashboard_engine import get_dashboard_summary

from backend.app.models.entities import (
    RiskRating,
    ReviewCase,
    Customer,
    Alert,
    AuditEvent
)

router = APIRouter(
    prefix="/api/kyc",
    tags=["KYC Compliance"]
)


@router.get("/customer/{customer_id}")
def get_customer_compliance(
    customer_id: str,
    db: Session = Depends(get_db)
):
    result = check_customer_compliance(db, customer_id)

    if result["compliance_status"] == "NOT_FOUND":
        raise HTTPException(status_code=404, detail="Customer not found")

    return result


@router.get("/anomalies")
def get_anomalies(
    db: Session = Depends(get_db)
):
    anomalies = detect_anomalies(db)

    return {
        "total_anomalies": len(anomalies),
        "anomalies": anomalies
    }


@router.get("/risk/{customer_id}")
def get_customer_risk(
    customer_id: str,
    db: Session = Depends(get_db)
):
    risk = (
        db.query(RiskRating)
        .filter(RiskRating.customer_id == customer_id)
        .order_by(RiskRating.assessed_at.desc())
        .first()
    )

    if not risk:
        raise HTTPException(
            status_code=404,
            detail="Risk rating not found for this customer"
        )

    return {
        "risk_rating_id": risk.risk_rating_id,
        "customer_id": risk.customer_id,
        "risk_level": risk.risk_level,
        "risk_score": risk.risk_score,
        "reason": risk.reason,
        "rules_version": risk.rules_version,
        "assessed_at": risk.assessed_at
    }


@router.get("/reviews/{customer_id}")
def get_customer_reviews(
    customer_id: str,
    db: Session = Depends(get_db)
):
    customer = (
        db.query(Customer)
        .filter(Customer.customer_id == customer_id)
        .first()
    )

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    reviews = (
        db.query(ReviewCase)
        .filter(ReviewCase.customer_id == customer_id)
        .order_by(ReviewCase.opened_date.desc())
        .all()
    )

    return {
        "customer_id": customer_id,
        "total_reviews": len(reviews),
        "reviews": [
            {
                "review_case_id": review.review_case_id,
                "review_type": review.review_type,
                "risk_level": review.risk_level,
                "opened_date": review.opened_date,
                "due_date": review.due_date,
                "status": review.status,
                "resolution": review.resolution,
                "closed_date": review.closed_date
            }
            for review in reviews
        ]
    }


@router.get("/alerts/{customer_id}")
def get_customer_alerts(
    customer_id: str,
    db: Session = Depends(get_db)
):
    customer = (
        db.query(Customer)
        .filter(Customer.customer_id == customer_id)
        .first()
    )

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    alerts = (
        db.query(Alert)
        .filter(Alert.customer_id == customer_id)
        .order_by(Alert.created_date.desc())
        .all()
    )

    return {
        "customer_id": customer_id,
        "total_alerts": len(alerts),
        "alerts": [
            {
                "alert_id": alert.alert_id,
                "document_id": alert.document_id,
                "review_id": alert.review_id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "description": alert.description,
                "status": alert.status,
                "created_date": alert.created_date
            }
            for alert in alerts
        ]
    }


@router.get("/audit/{customer_id}")
def get_customer_audit_history(
    customer_id: str,
    db: Session = Depends(get_db)
):
    customer = (
        db.query(Customer)
        .filter(Customer.customer_id == customer_id)
        .first()
    )

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.customer_id == customer_id)
        .order_by(AuditEvent.created_at.desc())
        .all()
    )

    return {
        "customer_id": customer_id,
        "total_events": len(events),
        "audit_history": [
            {
                "audit_event_id": event.audit_event_id,
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "action": event.action,
                "actor_role": event.actor_role,
                "event_data": event.event_data,
                "created_at": event.created_at
            }
            for event in events
        ]
    }


@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db)
):
    return get_dashboard_summary(db)
