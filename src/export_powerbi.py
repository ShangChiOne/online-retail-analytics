"""Step 8: export a Power BI-ready star schema to powerbi/data/.

fact_sales      -> data/processed/transactions.parquet (load directly; Power BI reads Parquet)
dim_customer    customer attributes + RFM segment + churn risk
dim_product     product attributes + ABC class
dim_date        calendar table (mark as date table in Power BI)
cohort_retention, basket_pairs  ready-made analysis tables
"""
import shutil

import pandas as pd

from config import POWERBI_DIR, PROCESSED


def main() -> None:
    POWERBI_DIR.mkdir(parents=True, exist_ok=True)

    rfm = pd.read_csv(PROCESSED / "03_rfm_segments.csv")
    churn = pd.read_csv(PROCESSED / "churn_scores.csv",
                        usecols=["CustomerID", "churn_probability", "risk_band", "revenue_at_risk"])
    dim_customer = rfm.merge(churn, on="CustomerID", how="left")
    dim_customer.to_csv(POWERBI_DIR / "dim_customer.csv", index=False)

    products = pd.read_csv(PROCESSED / "04_product_pareto.csv")
    products.rename(columns={"description": "Description"}).to_csv(POWERBI_DIR / "dim_product.csv", index=False)

    tx = pd.read_parquet(PROCESSED / "transactions.parquet", columns=["InvoiceDate"])
    days = pd.date_range(tx["InvoiceDate"].min().normalize(), tx["InvoiceDate"].max().normalize(), freq="D")
    dim_date = pd.DataFrame({
        "Date": days,
        "Year": days.year,
        "Quarter": "Q" + days.quarter.astype(str),
        "MonthNum": days.month,
        "Month": days.strftime("%b"),
        "YearMonth": days.strftime("%Y-%m"),
        "WeekdayNum": days.weekday + 1,
        "Weekday": days.strftime("%a"),
        "IsPeakSeason": days.month.isin([9, 10, 11]).astype(int),
    })
    dim_date.to_csv(POWERBI_DIR / "dim_date.csv", index=False)

    for name in ("02_cohort_retention.csv", "basket_pairs.csv", "01_monthly_kpis.csv"):
        shutil.copy(PROCESSED / name, POWERBI_DIR / name)
    print(f"  Power BI tables -> {POWERBI_DIR} ({len(dim_customer):,} customers, {len(products):,} products)")


if __name__ == "__main__":
    main()
