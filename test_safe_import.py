
import tempfile
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from database.database import Base
from backend.app.models import entities
from import_data import IMPORT_ORDER, import_csv

DATA_DIR = Path("data/generated")

def main():
    print("\nSAFE TEMPORARY DATABASE IMPORT TEST")
    print("=" * 40)

    if not DATA_DIR.exists():
        raise FileNotFoundError(f"Generated data folder missing: {DATA_DIR}")

    for filename, model in IMPORT_ORDER:
        if not (DATA_DIR / filename).exists():
            raise FileNotFoundError(f"Missing CSV: {DATA_DIR / filename}")

    with tempfile.TemporaryDirectory(prefix="kyc_import_test_") as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        test_engine = create_engine(
            f"sqlite:///{db_path.as_posix()}",
            connect_args={"check_same_thread": False}
        )

        try:
            Base.metadata.create_all(bind=test_engine)

            with Session(test_engine) as session:
                try:
                    for filename, model in IMPORT_ORDER:
                        import_csv(session, filename, model)

                    session.commit()
                    print("\nIMPORT COMMIT: SUCCESS")

                except Exception:
                    session.rollback()
                    raise

            with test_engine.connect() as connection:
                print("\nIMPORTED ROW COUNTS")
                print("-" * 30)

                for _, model in IMPORT_ORDER:
                    table_name = model.__tablename__
                    count = connection.execute(
                        text(f'SELECT COUNT(*) FROM "{table_name}"')
                    ).scalar_one()
                    print(f"{table_name}: {count:,}")

                violations = connection.execute(
                    text("PRAGMA foreign_key_check")
                ).fetchall()

                print("\nFOREIGN KEY VIOLATIONS:", len(violations))

                owner_total = connection.execute(text("""
                    SELECT customer_id, SUM(ownership_percentage)
                    FROM beneficial_owners
                    GROUP BY customer_id
                    HAVING SUM(ownership_percentage) > 100
                """)).fetchall()

                print("OWNERSHIP TOTAL ABOVE 100%:", len(owner_total))

                integrity = connection.execute(
                    text("PRAGMA integrity_check")
                ).scalar_one()

                print("TEMP DB INTEGRITY:", integrity)

            if violations:
                print("\nRESULT: FAILED - Foreign key violations found")
            elif integrity != "ok":
                print("\nRESULT: FAILED - Database integrity issue")
            else:
                print("\nRESULT: TEMPORARY IMPORT TEST PASSED")

        finally:
            test_engine.dispose()

    print("\nTEMPORARY DATABASE REMOVED")
    print("PRODUCTION DATABASE WAS NOT MODIFIED")


if __name__ == "__main__":
    main()
