
from sqlalchemy import inspect, text

from database.database import engine

inspector = inspect(engine)

tables = inspector.get_table_names()

print("\nDATABASE TABLE CHECK")
print("====================")

with engine.connect() as connection:
    for table in tables:
        result = connection.execute(
            text(f'SELECT COUNT(*) FROM "{table}"')
        )

        count = result.scalar()

        print(f"{table}: {count} records")

print("\nDATABASE CHECK COMPLETE!")
