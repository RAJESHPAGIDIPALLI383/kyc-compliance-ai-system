
from database.database import SessionLocal
from backend.app.models.entities import AuditEvent

db = SessionLocal()

try:
    document_ids = [
        "DOC-CUS-000006-001",
        "DOC-CUS-000014-001",
        "DOC-CUS-000016-001",
    ]

    for document_id in document_ids:

        print("\nDOCUMENT:", document_id)
        print("-" * 50)

        events = db.query(AuditEvent).filter(
            AuditEvent.entity_type == "DOCUMENT",
            AuditEvent.entity_id == document_id,
        ).order_by(AuditEvent.created_at).all()

        for event in events:
            print("Action:", event.action)
            print("Actor:", event.actor_role)
            print("Created:", event.created_at)
            print("Event data:", event.event_data)

finally:
    db.close()
