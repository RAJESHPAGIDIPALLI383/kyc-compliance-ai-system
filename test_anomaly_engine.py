
from collections import Counter

from database.database import SessionLocal
from backend.app.engines.anomaly_engine import detect_anomalies


db = SessionLocal()

try:
    print("\nKYC ANOMALY DETECTION TEST")
    print("=========================")

    anomalies = detect_anomalies(db)

    print("\nTOTAL ANOMALIES DETECTED:", len(anomalies))

    counts = Counter(
        anomaly["anomaly_type"]
        for anomaly in anomalies
    )

    print("\nANOMALY TYPE SUMMARY")
    print("--------------------")

    for anomaly_type, count in sorted(counts.items()):
        print(f"{anomaly_type}: {count}")

    print("\nGROUND TRUTH ANOMALY CHECK")
    print("-------------------------")

    expected_types = [
        "EXPIRED_DOCUMENT_MARKED_VALID",
        "APPROVED_WITH_MISSING_EVIDENCE",
        "OWNERSHIP_EXCEEDS_100",
        "REVIEW_CLOSED_WITHOUT_RESOLUTION",
        "DUPLICATE_DOCUMENT_ACROSS_CUSTOMERS",
    ]

    for anomaly_type in expected_types:
        status = "PASS" if counts[anomaly_type] > 0 else "FAIL"
        print(f"{anomaly_type}: {status}")

    print("\nSAMPLE DETECTED ANOMALIES")
    print("------------------------")

    for anomaly in anomalies[:10]:
        print(anomaly)

finally:
    db.close()
