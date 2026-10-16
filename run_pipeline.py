"""Run the full analysis end to end:  python run_pipeline.py

raw Excel -> clean parquet -> SQLite + SQL analyses -> statistics -> churn model
          -> market basket -> figures -> Power BI export
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import basket  # noqa: E402
import churn_model  # noqa: E402
import clean  # noqa: E402
import export_powerbi  # noqa: E402
import figures  # noqa: E402
import hypothesis_test  # noqa: E402
import ingest  # noqa: E402
import run_sql  # noqa: E402

STEPS = [
    ("Ingest raw Excel", ingest.main),
    ("Clean & audit", clean.main),
    ("SQL analyses", run_sql.main),
    ("Hypothesis tests", hypothesis_test.main),
    ("Churn model", churn_model.main),
    ("Market basket", basket.main),
    ("Figures", figures.main),
    ("Power BI export", export_powerbi.main),
]

if __name__ == "__main__":
    start = time.time()
    for i, (name, fn) in enumerate(STEPS, 1):
        print(f"\n[{i}/{len(STEPS)}] {name}")
        fn()
    print(f"\nPipeline finished in {time.time() - start:.0f}s")
