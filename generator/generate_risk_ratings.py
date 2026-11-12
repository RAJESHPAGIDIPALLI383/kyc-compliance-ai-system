
import pandas as pd

from generator.config import GENERATED_DIR

customers = pd.read_csv(
    GENERATED_DIR / "customers.csv"
)

risk_ratings = []

for index, customer in enumerate(
    customers.itertuples(index=False),
    start=1
):
    customer_number = int(customer.customer_id.split("-")[1])

    # Deterministic synthetic risk factors
    business_score = 15 if customer.customer_type_id == "BUSINESS" else 0
    pattern_score = (customer_number % 5) * 10

    risk_score = min(100, 20 + business_score + pattern_score)

    if risk_score >= 70:
        risk_level = "HIGH"
    elif risk_score >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    reasons = []

    if business_score:
        reasons.append("Business customer risk factor")

    if pattern_score:
        reasons.append("Synthetic customer risk indicator")

    if not reasons:
        reasons.append("Standard baseline risk")

    risk_ratings.append({
        "risk_rating_id": f"RSK-2026-{index:06d}",
        "customer_id": customer.customer_id,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "reason": "; ".join(reasons),
        "rules_version": "1.0"
    })

df = pd.DataFrame(risk_ratings)

df.to_csv(
    GENERATED_DIR / "risk_ratings.csv",
    index=False
)

print("RISK RATINGS GENERATED SUCCESSFULLY!")
print("Total risk ratings:", len(df))
print("\nRisk level distribution:")
print(df["risk_level"].value_counts().to_string())
