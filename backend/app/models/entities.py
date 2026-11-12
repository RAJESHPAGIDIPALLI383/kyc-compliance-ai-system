
from datetime import datetime, timezone

from sqlalchemy import (
    String, Integer, Float, Boolean, Date, DateTime,
    ForeignKey, Text, JSON, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class CustomerType(Base):
    __tablename__ = "customer_types"

    customer_type_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    type_name: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[str] = mapped_column(Text)

    customers: Mapped[list["Customer"]] = relationship(back_populates="customer_type")
    requirements: Mapped[list["KYCRequirement"]] = relationship(back_populates="customer_type")


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    customer_type_id: Mapped[str] = mapped_column(ForeignKey("customer_types.customer_type_id"))
    full_name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(150), unique=True)
    country: Mapped[str] = mapped_column(String(80), default="India")
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    customer_type: Mapped["CustomerType"] = relationship(back_populates="customers")
    documents: Mapped[list["Document"]] = relationship(back_populates="customer")
    risk_ratings: Mapped[list["RiskRating"]] = relationship(back_populates="customer")
    reviews: Mapped[list["ReviewCase"]] = relationship(back_populates="customer")
    beneficial_owners: Mapped[list["BeneficialOwner"]] = relationship(back_populates="customer")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="customer")
    audit_events: Mapped[list["AuditEvent"]] = relationship(back_populates="customer")


class KYCRequirement(Base):
    __tablename__ = "kyc_requirements"

    requirement_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    customer_type_id: Mapped[str] = mapped_column(ForeignKey("customer_types.customer_type_id"))
    requirement_name: Mapped[str] = mapped_column(String(100))
    document_type: Mapped[str] = mapped_column(String(50))
    risk_level: Mapped[str] = mapped_column(String(20), default="ALL")
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    effective_from: Mapped[Date] = mapped_column(Date)
    effective_to: Mapped[Date | None] = mapped_column(Date, nullable=True)

    customer_type: Mapped["CustomerType"] = relationship(back_populates="requirements")


class Document(Base):
    __tablename__ = "documents"

    document_id: Mapped[str] = mapped_column(String(60), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"))
    document_type: Mapped[str] = mapped_column(String(50))
    document_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    issue_date: Mapped[Date] = mapped_column(Date)
    expiry_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(30), default="PENDING")
    file_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    customer: Mapped["Customer"] = relationship(back_populates="documents")
    verifications: Mapped[list["Verification"]] = relationship(back_populates="document")



class Verification(Base):
    __tablename__ = "verifications"

    verification_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.document_id"))
    status: Mapped[str] = mapped_column(String(30))
    verifier_role: Mapped[str] = mapped_column(String(50))
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    document: Mapped["Document"] = relationship(back_populates="verifications")

class RiskRating(Base):
    __tablename__ = "risk_ratings"

    risk_rating_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"))
    risk_level: Mapped[str] = mapped_column(String(20))
    risk_score: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text)
    rules_version: Mapped[str] = mapped_column(String(30), default="1.0")
    assessed_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    customer: Mapped["Customer"] = relationship(back_populates="risk_ratings")



class ReviewCase(Base):
    __tablename__ = "review_cases"

    review_case_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"))
    review_type: Mapped[str] = mapped_column(String(40))
    risk_level: Mapped[str] = mapped_column(String(20))
    opened_date: Mapped[Date] = mapped_column(Date)
    due_date: Mapped[Date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="OPEN")
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_date: Mapped[Date | None] = mapped_column(Date, nullable=True)

    customer: Mapped["Customer"] = relationship(back_populates="reviews")


class BeneficialOwner(Base):
    __tablename__ = "beneficial_owners"

    owner_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"))
    owner_name: Mapped[str] = mapped_column(String(150))
    ownership_percentage: Mapped[float] = mapped_column(Float)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        CheckConstraint(
            "ownership_percentage >= 0 AND ownership_percentage <= 100",
            name="ck_owner_percentage_range"
        ),
    )

    customer: Mapped["Customer"] = relationship(back_populates="beneficial_owners")



class Alert(Base):
    __tablename__ = "alerts"

    alert_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"))
    document_id: Mapped[str | None] = mapped_column(
        ForeignKey("documents.document_id"),
        nullable=True
    )
    review_id: Mapped[str | None] = mapped_column(
        ForeignKey("review_cases.review_case_id"),
        nullable=True
    )
    alert_type: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    created_date: Mapped[Date] = mapped_column(Date)

    customer: Mapped["Customer"] = relationship(back_populates="alerts")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    audit_event_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    customer_id: Mapped[str | None] = mapped_column(
        ForeignKey("customers.customer_id"), nullable=True
    )
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[str] = mapped_column(String(60))
    action: Mapped[str] = mapped_column(String(50))
    actor_role: Mapped[str] = mapped_column(String(50))
    event_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    customer: Mapped["Customer | None"] = relationship(back_populates="audit_events")
