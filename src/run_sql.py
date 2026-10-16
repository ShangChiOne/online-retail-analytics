"""Step 3: load clean data into SQLite and run every query in sql/.

Each sql/NN_name.sql (except 00_views) produces data/processed/NN_name.csv.
"""
import sqlite3

import pandas as pd

from config import DB_PATH, PROCESSED, SQL_DIR


def load_database() -> sqlite3.Connection:
    df = pd.read_parquet(PROCESSED / "transactions.parquet")
    df["InvoiceDate"] = df["InvoiceDate"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df["is_return"] = df["is_return"].astype(int)
    df = df.drop(columns="InvoiceDay")

    DB_PATH.unlink(missing_ok=True)
    con = sqlite3.connect(DB_PATH)
    df.to_sql("transactions", con, index=False)
    con.executescript(
        """
        CREATE INDEX ix_tx_customer ON transactions (CustomerID);
        CREATE INDEX ix_tx_invoice  ON transactions (Invoice);
        CREATE INDEX ix_tx_stock    ON transactions (StockCode);
        """
    )
    print(f"Loaded {len(df):,} rows into {DB_PATH.name}")
    return con


def main() -> None:
    con = load_database()
    con.executescript((SQL_DIR / "00_views.sql").read_text())
    for path in sorted(SQL_DIR.glob("[0-9][0-9]_*.sql")):
        if path.name.startswith("00_"):
            continue
        result = pd.read_sql_query(path.read_text(), con)
        out = PROCESSED / f"{path.stem}.csv"
        result.to_csv(out, index=False)
        print(f"  {path.name:<30} -> {len(result):>6,} rows")
    con.close()


if __name__ == "__main__":
    main()
