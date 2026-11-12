
from sqlalchemy import text

from database.database import engine

indexes = [
    "CREATE INDEX IF NOT EXISTS idx_documents_customer ON documents(customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(customer_id, document_type)",
    "CREATE INDEX IF NOT EXISTS idx_risk_customer ON risk_ratings(customer_id, assessed_at)",
    "CREATE INDEX IF NOT EXISTS idx_review_customer ON review_cases(customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_review_status_due ON review_cases(status, due_date)",
    "CREATE INDEX IF NOT EXISTS idx_alert_status ON alerts(status)",
    "CREATE INDEX IF NOT EXISTS idx_alert_customer ON alerts(customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_owners_customer ON beneficial_owners(customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_requirements_type ON kyc_requirements(customer_type_id, is_mandatory)",
    "CREATE INDEX IF NOT EXISTS idx_audit_customer ON audit_events(customer_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_verifications_document ON verifications(document_id)"
]

with engine.begin() as connection:

    for index_sql in indexes:
        connection.execute(text(index_sql))

print("DATABASE INDEXES CREATED SUCCESSFULLY!")
print("Total indexes added:", len(indexes))
