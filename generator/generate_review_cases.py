
import random
import pandas as pd

from datetime import date, timedelta

from generator.config import (
    RANDOM_SEED,
    REVIEW_CASE_COUNT,
    GENERATED_DIR,
    GROUND_TRUTH_DIR
)

random.seed(RANDOM_SEED)

AS_OF_DATE = date(2026, 11, 12)

customers = pd.read_csv(
    GENERATED_DIR / "customers.csv"
)

risk_ratings = pd.read_csv(
    GENERATED_DIR / "risk_ratings.csv"
)

customer_data = customers.merge(
    risk_ratings[["customer_id", "risk_level"]],
    on="customer_id"
)

selected = customer_data.head(REVIEW_CASE_COUNT)

review_cases = []
ground_truth = []

for index, customer in enumerate(
    selected.itertuples(index=False),
    start=1
):
    if customer.risk_level == "HIGH":
        review_days = 90
    elif customer.risk_level == "MEDIUM":
        review_days = 180
    else:
        review_days = 365

    days_ago = random.randint(30, 400)

    opened_date = AS_OF_DATE - timedelta(
        days=days_ago
    )

    due_date = opened_date + timedelta(
        days=review_days
    )

    resolution = None
    closed_date = None

    if index == 1:
        status = "CLOSED"
        closed_date = AS_OF_DATE - timedelta(days=2)
        resolution = None

        ground_truth.append({
            "review_case_id": f"REV-{index:06d}",
            "anomaly_type": "CLOSED_WITHOUT_RESOLUTION",
            "expected_detection": True
        })

    elif index % 4 == 0:
        status = "CLOSED"
        closed_date = AS_OF_DATE - timedelta(
            days=random.randint(1, 30)
        )
        resolution = "Evidence reviewed and case resolved"

    elif due_date < AS_OF_DATE:
        status = "IN_PROGRESS"

    else:
        status = "OPEN"

    review_cases.append({
        "review_case_id": f"REV-{index:06d}",
        "customer_id": customer.customer_id,
        "review_type": "PERIODIC",
        "risk_level": customer.risk_level,
        "opened_date": opened_date,
        "due_date": due_date,
        "status": status,
        "resolution": resolution,
        "closed_date": closed_date
    })

review_df = pd.DataFrame(review_cases)

review_df.to_csv(
    GENERATED_DIR / "review_cases.csv",
    index=False
)

ground_truth_df = pd.DataFrame(ground_truth)

ground_truth_df.to_csv(
    GROUND_TRUTH_DIR / "review_case_ground_truth.csv",
    index=False
)

print("REVIEW CASES GENERATED SUCCESSFULLY!")
print("Total review cases:", len(review_df))
print("\nReview status distribution:")
print(review_df["status"].value_counts().to_string())
print(
    "\nCases closed without resolution:",
    int(
        (
            (review_df["status"] == "CLOSED")
            & (review_df["resolution"].isna())
        ).sum()
    )
)
print("\nOutput:", GENERATED_DIR / "review_cases.csv")
