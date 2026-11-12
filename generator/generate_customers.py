
import random
import pandas as pd
from faker import Faker

from generator.config import (
    RANDOM_SEED,
    CUSTOMER_COUNT,
    BUSINESS_CUSTOMER_COUNT,
    GENERATED_DIR
)

fake = Faker("en_IN")
Faker.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

individual_count = CUSTOMER_COUNT - BUSINESS_CUSTOMER_COUNT

customer_types = pd.DataFrame([
    {
        "customer_type_id": "INDIVIDUAL",
        "type_name": "Individual",
        "description": "Personal account holder"
    },
    {
        "customer_type_id": "BUSINESS",
        "type_name": "Business",
        "description": "Business or corporate account holder"
    }
])

customer_types.to_csv(
    GENERATED_DIR / "customer_types.csv",
    index=False
)

customers = []

for i in range(1, CUSTOMER_COUNT + 1):

    if i <= individual_count:
        customer_type = "INDIVIDUAL"
        name = fake.name()
    else:
        customer_type = "BUSINESS"
        name = fake.company()

    customers.append({
        "customer_id": f"CUS-{i:06d}",
        "customer_type_id": customer_type,
        "full_name": name,
        "email": f"customer{i:06d}@example.com",
        "country": "India",
        "status": "PENDING"
    })

customers_df = pd.DataFrame(customers)

customers_df.to_csv(
    GENERATED_DIR / "customers.csv",
    index=False
)

print("CUSTOMER DATA GENERATED SUCCESSFULLY!")
print("Total customers:", len(customers_df))
print("Individual customers:", individual_count)
print("Business customers:", BUSINESS_CUSTOMER_COUNT)
print("Output folder:", GENERATED_DIR)
