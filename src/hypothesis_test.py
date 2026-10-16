"""Step 4: hypothesis tests that back up the two biggest claims in the report.

H1  Customers acquired in the Q4 peak (Sep-Nov 2010) are less likely to make a second
    purchase within 90 days than customers acquired Jan-Aug 2010.  (two-proportion chi-square)
H2  New-customer acquisition fell from Jul-Nov 2010 to Jul-Nov 2011.  (Poisson rate test on
    monthly counts; Jul-Nov chosen so the Dec-2009 left-censoring effect has washed out)
"""
import json

import numpy as np
import pandas as pd
from scipy import stats

from config import PROCESSED


def repeat_within_90_days(tx: pd.DataFrame) -> pd.DataFrame:
    orders = (tx[~tx["is_return"] & tx["CustomerID"].notna()]
              .groupby(["CustomerID", "Invoice"], as_index=False)["InvoiceDay"].min())
    first = orders.groupby("CustomerID")["InvoiceDay"].min().rename("first_day")
    orders = orders.join(first, on="CustomerID")
    later = orders[(orders["InvoiceDay"] > orders["first_day"])
                   & (orders["InvoiceDay"] <= orders["first_day"] + pd.Timedelta(days=90))]
    out = first.to_frame()
    out["repeat_90d"] = out.index.isin(later["CustomerID"].unique())
    return out


def proportion_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval."""
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return centre - half, centre + half


def test_q4_cohort_repeat(tx: pd.DataFrame) -> dict:
    cust = repeat_within_90_days(tx)
    # 2010 acquisitions only: full 90-day follow-up exists and Dec-2009 (left-censored) is excluded.
    cust = cust[(cust["first_day"] >= "2010-01-01") & (cust["first_day"] < "2010-12-01")]
    cust["group"] = np.where(cust["first_day"].dt.month >= 9, "Q4 peak (Sep-Nov)", "Rest of year (Jan-Aug)")

    table = pd.crosstab(cust["group"], cust["repeat_90d"])
    chi2, p_value, _, _ = stats.chi2_contingency(table)
    rows = {}
    for g, r in table.iterrows():
        n, k = int(r.sum()), int(r[True])
        lo, hi = proportion_ci(k, n)
        rows[g] = {"customers": n, "repeaters": k, "repeat_rate": k / n, "ci95": [lo, hi]}
    peak, rest = rows["Q4 peak (Sep-Nov)"], rows["Rest of year (Jan-Aug)"]
    # Cohen's h effect size for two proportions.
    h = 2 * np.arcsin(np.sqrt(peak["repeat_rate"])) - 2 * np.arcsin(np.sqrt(rest["repeat_rate"]))
    return {
        "hypothesis": "Q4-acquired customers repeat less within 90 days",
        "groups": rows,
        "difference_pp": 100 * (peak["repeat_rate"] - rest["repeat_rate"]),
        "chi2": float(chi2),
        "p_value": float(p_value),
        "cohens_h": float(h),
        "significant_at_5pct": bool(p_value < 0.05),
    }


def test_acquisition_drop(kpis: pd.DataFrame) -> dict:
    k = kpis.set_index("month")["new_customers"]
    months_2010 = [f"2010-{m:02d}" for m in range(7, 12)]
    months_2011 = [f"2011-{m:02d}" for m in range(7, 12)]
    n10, n11 = int(k[months_2010].sum()), int(k[months_2011].sum())
    # Conditional binomial test for equal Poisson rates over equal exposure.
    result = stats.binomtest(n11, n10 + n11, 0.5, alternative="less")
    return {
        "hypothesis": "New-customer acquisition fell Jul-Nov 2011 vs Jul-Nov 2010",
        "new_customers_2010": n10,
        "new_customers_2011": n11,
        "change_pct": 100 * (n11 - n10) / n10,
        "p_value": float(result.pvalue),
        "significant_at_5pct": bool(result.pvalue < 0.05),
    }


def main() -> dict:
    tx = pd.read_parquet(PROCESSED / "transactions.parquet")
    kpis = pd.read_csv(PROCESSED / "01_monthly_kpis.csv")
    results = {"q4_cohort_repeat": test_q4_cohort_repeat(tx), "acquisition_drop": test_acquisition_drop(kpis)}
    (PROCESSED / "hypothesis_tests.json").write_text(json.dumps(results, indent=2))
    for name, r in results.items():
        print(f"  {name}: p={r['p_value']:.2e}  significant={r['significant_at_5pct']}")
    return results


if __name__ == "__main__":
    main()
