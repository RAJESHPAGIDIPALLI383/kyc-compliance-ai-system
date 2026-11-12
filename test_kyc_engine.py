
from database.database import SessionLocal
from backend.app.engines.kyc_engine import check_customer_compliance

db = SessionLocal()

try:
    customer_ids = [
        "CUS-000001",
        "CUS-000002",
        "CUS-000003",
    ]

    for customer_id in customer_ids:
        result = check_customer_compliance(db, customer_id)

        print("\n" + "=" * 50)
        print("CUSTOMER:", customer_id)
        print("=" * 50)

        for key, value in result.items():
            print(f"{key}: {value}")

finally:
    db.close()
