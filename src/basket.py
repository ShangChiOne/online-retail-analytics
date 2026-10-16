"""Step 6: market-basket analysis - which products are bought together?

Pair support / confidence / lift over invoices, restricted to the 300 best-selling products
(by number of orders) so every rule has enough evidence. Computed with a sparse
invoice x product matrix: co-occurrence = B.T @ B.
"""
import numpy as np
import pandas as pd
from scipy import sparse

from config import PROCESSED

TOP_N_PRODUCTS = 300
MIN_PAIR_ORDERS = 150


def main() -> pd.DataFrame:
    tx = pd.read_parquet(PROCESSED / "transactions.parquet", columns=["Invoice", "StockCode", "Description", "is_return"])
    sales = tx[~tx["is_return"]].drop_duplicates(["Invoice", "StockCode"])
    names = sales.groupby("StockCode")["Description"].agg(lambda s: s.mode()[0])

    top = sales["StockCode"].value_counts().head(TOP_N_PRODUCTS).index
    s = sales[sales["StockCode"].isin(top)]
    inv_idx, invoices = pd.factorize(s["Invoice"])
    prod_idx, products = pd.factorize(s["StockCode"])
    n_orders = sales["Invoice"].nunique()

    B = sparse.csr_matrix((np.ones(len(s)), (inv_idx, prod_idx)), shape=(len(invoices), len(products)))
    co = (B.T @ B).toarray()
    item_orders = np.diag(co).copy()
    np.fill_diagonal(co, 0)

    i, j = np.where(np.triu(co) >= MIN_PAIR_ORDERS)
    pairs = pd.DataFrame({
        "product_a": products[i], "product_b": products[j],
        "orders_together": co[i, j].astype(int),
    })
    pairs["support_pct"] = 100 * pairs["orders_together"] / n_orders
    pairs["confidence_a_to_b_pct"] = 100 * pairs["orders_together"] / item_orders[i]
    pairs["confidence_b_to_a_pct"] = 100 * pairs["orders_together"] / item_orders[j]
    pairs["lift"] = pairs["orders_together"] * n_orders / (item_orders[i] * item_orders[j])
    pairs["name_a"] = pairs["product_a"].map(names)
    pairs["name_b"] = pairs["product_b"].map(names)
    pairs = pairs.sort_values("lift", ascending=False).round(2)
    pairs.to_csv(PROCESSED / "basket_pairs.csv", index=False)
    print(f"  {len(pairs):,} product pairs with >= {MIN_PAIR_ORDERS} shared orders; top lift {pairs['lift'].max():.1f}x")
    return pairs


if __name__ == "__main__":
    main()
