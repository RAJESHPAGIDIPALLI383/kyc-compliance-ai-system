
import sys
import runpy
import hashlib
import tempfile

from pathlib import Path

ROOT = Path(__file__).resolve().parent

sys.path.insert(0, str(ROOT))

import generator.config as config


GENERATOR_ORDER = [
    "generate_customers.py",
    "generate_requirements.py",
    "generate_documents.py",
    "generate_risk_ratings.py",
    "generate_beneficial_owners.py",
    "generate_review_cases.py",
    "generate_ground_truth.py",
    "generate_verifications.py",
    "generate_alerts.py",
    "generate_audit_events.py",
    "validate_generated_data.py"
]


def checksum_folder(folder):
    results = {}

    for path in sorted(folder.rglob("*")):
        if path.is_file():
            relative_path = str(path.relative_to(folder))
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            results[relative_path] = digest

    return results


def run_test(test_name):

    print("\n" + "=" * 65)
    print("RUNNING:", test_name)
    print("=" * 65)

    with tempfile.TemporaryDirectory(
        prefix="kyc_regeneration_"
    ) as temporary_folder:

        temporary_root = Path(temporary_folder)

        generated_dir = temporary_root / "generated"
        ground_truth_dir = temporary_root / "ground_truth"

        generated_dir.mkdir(parents=True)
        ground_truth_dir.mkdir(parents=True)

        # Redirect all generator outputs to temporary folders.
        config.GENERATED_DIR = generated_dir
        config.GROUND_TRUTH_DIR = ground_truth_dir

        # Run generators in dependency order.
        for script in GENERATOR_ORDER:

            script_path = ROOT / "generator" / script

            print("\nRUNNING:", script)

            runpy.run_path(
                str(script_path),
                run_name="__main__"
            )

        # Required output files.
        required_files = [
            "customer_types.csv",
            "customers.csv",
            "kyc_requirements.csv",
            "documents.csv",
            "risk_ratings.csv",
            "beneficial_owners.csv",
            "review_cases.csv",
            "verifications.csv",
            "alerts.csv",
            "audit_events.csv"
        ]

        for filename in required_files:
            if not (generated_dir / filename).exists():
                raise AssertionError(
                    f"Missing generated file: {filename}"
                )

        # Read final generated data.
        import pandas as pd

        customers = pd.read_csv(
            generated_dir / "customers.csv"
        )

        documents = pd.read_csv(
            generated_dir / "documents.csv"
        )

        owners = pd.read_csv(
            generated_dir / "beneficial_owners.csv"
        )

        reviews = pd.read_csv(
            generated_dir / "review_cases.csv"
        )

        alerts = pd.read_csv(
            generated_dir / "alerts.csv"
        )

        verifications = pd.read_csv(
            generated_dir / "verifications.csv"
        )

        audit_events = pd.read_csv(
            generated_dir / "audit_events.csv"
        )

        ground_truth = pd.read_csv(
            ground_truth_dir / "anomaly_ground_truth.csv"
        )

        validation_report = pd.read_csv(
            ground_truth_dir / "validation_report.csv"
        )

        # Additional anomaly checks.
        required_anomalies = {
            "EXPIRED_DOCUMENT_MARKED_VALID",
            "APPROVED_WITH_MISSING_EVIDENCE",
            "OWNERSHIP_EXCEEDS_100",
            "REVIEW_CLOSED_WITHOUT_RESOLUTION",
            "DUPLICATE_DOCUMENT_ACROSS_CUSTOMERS"
        }

        found_anomalies = set(
            ground_truth["anomaly_type"].dropna()
        )

        if not required_anomalies.issubset(found_anomalies):
            raise AssertionError(
                "One or more required anomalies are missing."
            )

        expired_verified = documents[
            (pd.to_datetime(documents["expiry_date"]) < pd.Timestamp("2026-11-12"))
            & (documents["verification_status"] == "VERIFIED")
        ]

        if len(expired_verified) != 1:
            raise AssertionError(
                "Expected exactly one expired VERIFIED document."
            )

        ownership_totals = owners.groupby(
            "customer_id"
        )["ownership_percentage"].sum()

        if not (ownership_totals > 100).any():
            raise AssertionError(
                "Ownership anomaly not found."
            )

        closed_reviews = reviews[
            (reviews["status"] == "CLOSED")
            & (
                reviews["resolution"].isna()
                | (reviews["resolution"].astype(str).str.strip() == "")
            )
        ]

        if closed_reviews.empty:
            raise AssertionError(
                "Closed review without resolution not found."
            )

        duplicate_groups = documents.groupby(
            "document_number"
        )["customer_id"].nunique()

        if not (duplicate_groups > 1).any():
            raise AssertionError(
                "Cross-customer duplicate document not found."
            )

        approved_anomaly = ground_truth[
            ground_truth["anomaly_type"]
            == "APPROVED_WITH_MISSING_EVIDENCE"
        ]

        if approved_anomaly.empty:
            raise AssertionError(
                "Approved missing-evidence anomaly not recorded."
            )

        approved_customer_id = approved_anomaly.iloc[0]["entity_id"]

        approved_customer = customers[
            customers["customer_id"] == approved_customer_id
        ]

        if approved_customer.empty or approved_customer.iloc[0]["status"] != "APPROVED":
            raise AssertionError(
                "Missing-evidence anomaly customer is not APPROVED."
            )

        # Check missing-evidence alert for intentional anomaly.
        anomaly_alert = alerts[
            (alerts["customer_id"] == approved_customer_id)
            & (alerts["alert_type"] == "MISSING_EVIDENCE")
        ]

        if anomaly_alert.empty:
            raise AssertionError(
                "Missing-evidence alert not generated for anomaly customer."
            )

        # Check verification records.
        if len(verifications) != len(documents):
            raise AssertionError(
                "Verification count does not match document count."
            )

        if verifications["document_id"].nunique() != len(documents):
            raise AssertionError(
                "Duplicate or missing verification document references."
            )

        # Check audit history.
        if audit_events.empty:
            raise AssertionError(
                "Audit event data is empty."
            )

        if audit_events["audit_event_id"].duplicated().any():
            raise AssertionError(
                "Duplicate audit event IDs found."
            )

        # Check standard validator results.
        failed_checks = validation_report[
            validation_report["status"] != "PASS"
        ]

        if not failed_checks.empty:
            raise AssertionError(
                "Standard validation checks failed:\n"
                + failed_checks.to_string(index=False)
            )

        # Confirm expected volumes.
        if len(customers) != config.CUSTOMER_COUNT:
            raise AssertionError("Customer count mismatch.")

        if len(documents) != config.DOCUMENT_COUNT:
            raise AssertionError("Document count mismatch.")

        print("\nADDITIONAL SAFETY CHECKS PASSED!")
        print("Customers:", len(customers))
        print("Documents:", len(documents))
        print("Verifications:", len(verifications))
        print("Beneficial owners:", len(owners))
        print("Reviews:", len(reviews))
        print("Alerts:", len(alerts))
        print("Audit events:", len(audit_events))
        print("Ground-truth anomalies:", len(found_anomalies))
        print("Standard validation:", len(validation_report), "checks passed")

        # Include all generated and ground-truth files in checksum.
        all_checksums = {}

        all_checksums.update(
            {
                "generated/" + key: value
                for key, value in checksum_folder(generated_dir).items()
            }
        )

        all_checksums.update(
            {
                "ground_truth/" + key: value
                for key, value in checksum_folder(ground_truth_dir).items()
            }
        )

        print("\nTEMPORARY TEST PASSED:", test_name)

        return all_checksums


def main():

    print("KYC SAFE REGENERATION TEST")
    print("Production database will not be accessed.")
    print("Production CSV files will not be modified.")

    first_run = run_test("GENERATION RUN 1")
    second_run = run_test("GENERATION RUN 2")

    if first_run != second_run:
        raise AssertionError(
            "Deterministic generation failed. Checksums differ."
        )

    print("\n" + "=" * 65)
    print("FINAL RESULT")
    print("=" * 65)

    print("Generation run 1: PASS")
    print("Generation run 2: PASS")
    print("Checksum comparison: PASS")
    print("Deterministic generation: PASS")
    print("Production data modified: NO")
    print("Production database modified: NO")

    print("\nALL SAFE REGENERATION TESTS PASSED!")


if __name__ == "__main__":
    main()
