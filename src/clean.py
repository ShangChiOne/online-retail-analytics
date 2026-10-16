"""Step 2: clean the raw data and write an auditable data-quality log.

Output
------
data/processed/transactions.parquet  one row per product line; returns have negative quantity
data/processed/data_quality_log.csv   every rule applied and how many rows it removed
"""
import pandas as pd

from config import NON_PRODUCT_CODES, NON_PRODUCT_PREFIXES, PROCESSED, RAW_CACHE

log: list[dict] = []


def step(df: pd.DataFrame, mask_drop: pd.Series, rule: str, why: str) -> pd.DataFrame:
    """Drop rows matching mask_drop and record the rule in the audit log."""
    n = int(mask_drop.sum())
    value = float((df.loc[mask_drop, "Quantity"] * df.loc[mask_drop, "Price"]).sum())
    log.append({"rule": rule, "rows_removed": n, "value_removed_gbp": round(value, 2), "reason": why})
    print(f"  - {rule:<42} {n:>9,} rows")
    return df.loc[~mask_drop].copy()


def remove_voided_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Pair each cancellation with the sale it exactly reverses and remove both.

    A cancellation voids a sale when customer, stock code and absolute quantity match and
    the sale happened first. These pairs net to zero revenue but inflate order counts and
    quantities (e.g. an 80,995-unit order cancelled 12 minutes later).
    """
    df = df.reset_index(drop=True)
    df["_row"] = df.index
    known = df["CustomerID"].notna()
    sales = df[known & ~df["is_return"]][["_row", "CustomerID", "StockCode", "Quantity", "InvoiceDate"]]
    cancels = df[known & df["is_return"]][["_row", "CustomerID", "StockCode", "Quantity", "InvoiceDate"]].copy()
    cancels["Quantity"] = -cancels["Quantity"]

    pairs = cancels.merge(sales, on=["CustomerID", "StockCode", "Quantity"], suffixes=("_c", "_s"))
    pairs = pairs[pairs["InvoiceDate_s"] <= pairs["InvoiceDate_c"]]
    # Each cancellation voids its most recent preceding sale; each sale is voided at most once.
    pairs = pairs.sort_values("InvoiceDate_s", ascending=False).drop_duplicates("_row_c")
    pairs = pairs.drop_duplicates("_row_s")

    void_rows = set(pairs["_row_c"]) | set(pairs["_row_s"])
    df = step(df, df["_row"].isin(void_rows), "Voided order pairs (sale + exact cancellation)",
              "Sale fully reversed by a matching cancellation; nets to zero but distorts volumes")
    return df.drop(columns="_row")


def main() -> None:
    raw = pd.read_parquet(RAW_CACHE)
    print(f"Raw rows: {len(raw):,}")
    log.append({"rule": "Raw input", "rows_removed": 0, "value_removed_gbp": 0.0, "reason": f"{len(raw):,} rows"})

    df = raw.rename(columns={"Customer ID": "CustomerID"})
    df["Invoice"] = df["Invoice"].astype(str).str.strip()
    df["StockCode"] = df["StockCode"].astype(str).str.strip()
    df["Description"] = df["Description"].str.strip()

    # 1. The two sheets overlap on 2010-12-01..09; keep that window from the first sheet only.
    overlap = (df["source_sheet"] == "Year 2010-2011") & (df["InvoiceDate"] < "2010-12-10")
    df = step(df, overlap, "Sheet overlap (1-9 Dec 2010 in both sheets)",
              "Same invoices appear in both Excel sheets; would double-count revenue")

    # 2. Exact duplicate lines.
    cols = [c for c in df.columns if c != "source_sheet"]
    df = step(df, df.duplicated(subset=cols), "Exact duplicate lines",
              "Identical invoice, product, quantity, time and price")

    # 3. Accounting adjustments (A-invoices: 'Adjust bad debt').
    df = step(df, df["Invoice"].str.startswith("A"), "Bad-debt adjustments (A-invoices)",
              "Accounting entries, not customer transactions")

    # 4. Non-merchandise stock codes: postage, fees, manual entries, samples, gift vouchers.
    non_product = df["StockCode"].isin(NON_PRODUCT_CODES) | df["StockCode"].str.startswith(NON_PRODUCT_PREFIXES)
    df = step(df, non_product, "Non-product codes (postage, fees, manual, vouchers)",
              "Not merchandise; would distort product and basket analysis")

    # 5. Zero / negative prices: stock write-offs ('damaged', 'given away') with no customer.
    df = step(df, df["Price"] <= 0, "Zero or negative unit price",
              "Inventory write-offs and free samples, not sales")

    df["is_return"] = df["Invoice"].str.startswith("C")

    # 6. Negative quantity that is not a C-invoice = warehouse stock adjustment.
    df = step(df, (df["Quantity"] <= 0) & ~df["is_return"], "Negative qty without cancellation invoice",
              "Warehouse stock adjustments")

    # 7. Orders created by mistake and fully reversed.
    df = remove_voided_orders(df)

    df["CustomerID"] = df["CustomerID"].astype("Int64")
    df["Revenue"] = (df["Quantity"] * df["Price"]).round(2)
    df["InvoiceDay"] = df["InvoiceDate"].dt.normalize()
    df = df.drop(columns="source_sheet").sort_values("InvoiceDate").reset_index(drop=True)

    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PROCESSED / "transactions.parquet", index=False)

    log.append({"rule": "Clean output", "rows_removed": 0, "value_removed_gbp": 0.0, "reason": f"{len(df):,} rows"})
    pd.DataFrame(log).to_csv(PROCESSED / "data_quality_log.csv", index=False)

    sales = df[~df["is_return"]]
    print(f"Clean rows: {len(df):,}  ({len(df) / len(raw):.1%} of raw)")
    print(f"Sales lines: {len(sales):,} | returns lines: {int(df['is_return'].sum()):,}")
    print(f"Lines without CustomerID: {df['CustomerID'].isna().mean():.1%} (kept for revenue, excluded from customer analysis)")
    print(f"Net revenue: £{df['Revenue'].sum():,.0f}")


if __name__ == "__main__":
    main()
