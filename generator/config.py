
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
GENERATED_DIR = DATA_DIR / "generated"
GROUND_TRUTH_DIR = DATA_DIR / "ground_truth"
REPORTS_DIR = PROJECT_ROOT / "reports"

RANDOM_SEED = 20261022

CUSTOMER_COUNT = 8000
BUSINESS_CUSTOMER_COUNT = 1000

# 7,000 individuals x 3 documents
# 800 non-high-risk businesses x 4 documents
# 200 high-risk businesses x 5 documents
DOCUMENT_COUNT = (
    (CUSTOMER_COUNT - BUSINESS_CUSTOMER_COUNT) * 3
    + (BUSINESS_CUSTOMER_COUNT - 200) * 4
    + 200 * 5
)

REVIEW_CASE_COUNT = 3000

AS_OF_DATE = "2026-11-12"

for folder in (
    GENERATED_DIR,
    GROUND_TRUTH_DIR,
    REPORTS_DIR
):
    folder.mkdir(parents=True, exist_ok=True)
