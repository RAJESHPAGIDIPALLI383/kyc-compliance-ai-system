
from sqlalchemy import inspect, text
from database.database import engine

inspector = inspect(engine)

print("\nDATABASE SCHEMA AUDIT")
print("=====================")

with engine.connect() as connection:
    for table in inspector.get_table_names():
        print(f"\nTABLE: {table}")
        print("-" * 50)

        result = connection.execute(
            text(f'PRAGMA table_info("{table}")')
        )

        for row in result:
            print(
                f"Column: {row[1]} | "
                f"Type: {row[2]} | "
                f"Not Null: {row[3]} | "
                f"Primary Key: {row[5]}"
            )

        if table == "beneficial_owners":
            sql = connection.execute(
                text("""
                    SELECT sql
                    FROM sqlite_master
                    WHERE type = 'table'
                    AND name = 'beneficial_owners'
                """)
            ).scalar()

            print("\nBENEFICIAL OWNERS TABLE SQL:")
            print(sql)

print("\nSCHEMA AUDIT COMPLETE!")
