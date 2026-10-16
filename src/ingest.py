"""Step 1: read both Excel sheets once and cache them as parquet.

The Excel file takes a few minutes to parse; every later step reads the cache.
"""
import pandas as pd

from config import RAW_CACHE, RAW_XLSX


def main() -> None:
    if RAW_CACHE.exists():
        print(f"Cache already exists: {RAW_CACHE.name}")
        return
    print("Reading Excel (both sheets) - this takes a few minutes...")
    sheets = pd.read_excel(RAW_XLSX, sheet_name=None, dtype={"Invoice": str, "StockCode": str, "Description": str, "Country": str})
    frames = []
    for name, df in sheets.items():
        df["source_sheet"] = name
        frames.append(df)
        print(f"  {name}: {len(df):,} rows")
    raw = pd.concat(frames, ignore_index=True)
    raw.to_parquet(RAW_CACHE, index=False)
    print(f"Saved {len(raw):,} rows -> {RAW_CACHE}")


if __name__ == "__main__":
    main()
