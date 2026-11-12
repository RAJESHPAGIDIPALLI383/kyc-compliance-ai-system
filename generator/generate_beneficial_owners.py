import random
import pandas as pd

from faker import Faker
from generator.config import RANDOM_SEED, GENERATED_DIR

random.seed(RANDOM_SEED)

fake = Faker("en_IN")
Faker.seed(RANDOM_SEED)

customers = pd.read_csv(
    GENERATED_DIR / "customers.csv"
)

business_customers = customers[
    customers["customer_type_id"] == "BUSINESS"
]

owners = []

for index, customer in enumerate(
    business_customers.itertuples(index=False),
    start=1
):
    owner_count = random.randint(1, 3)

    split_points = sorted(
        random.sample(range(1, 10000), owner_count - 1)
    )

    amounts = (
        [0] + split_points + [10000]
    )

    percentages = [
        (amounts[i + 1] - amounts[i]) / 100
        for i in range(owner_count)
    ]

    # One intentional ownership anomaly
    if index == 1:
        percentages = [70.0, 60.0]

    for owner_index, percentage in enumerate(
        percentages,
        start=1
    ):
        owners.append({
            "owner_id": f"OWN-{index:06d}-{owner_index:02d}",
            "customer_id": customer.customer_id,
            "owner_name": fake.name(),
            "ownership_percentage": percentage,
            "is_verified": random.choice([True, False])
        })

owners_df = pd.DataFrame(owners)

owners_df.to_csv(
    GENERATED_DIR / "beneficial_owners.csv",
    index=False
)

ownership_totals = owners_df.groupby("customer_id")[
    "ownership_percentage"
].sum().round(2)

print("BENEFICIAL OWNERS GENERATED SUCCESSFULLY!")
print("Business customers:", len(business_customers))
print("Total beneficial owners:", len(owners_df))
print(
    "Customers with ownership above 100%:",
    int((ownership_totals > 100).sum())
)
