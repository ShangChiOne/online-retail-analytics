"""Shared paths and constants for the pipeline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_XLSX = ROOT / "data" / "raw" / "online_retail_II.xlsx"
RAW_CACHE = ROOT / "data" / "raw" / "online_retail_raw.parquet"
PROCESSED = ROOT / "data" / "processed"
DB_PATH = ROOT / "data" / "retail.db"
SQL_DIR = ROOT / "sql"
FIG_DIR = ROOT / "reports" / "figures"
POWERBI_DIR = ROOT / "powerbi" / "data"

# Stock codes that are fees, postage or manual adjustments, not merchandise.
NON_PRODUCT_CODES = {
    "POST", "DOT", "M", "m", "C2", "D", "S", "B", "CRUK", "PADS",
    "BANK CHARGES", "AMAZONFEE", "ADJUST", "ADJUST2", "TEST001", "TEST002",
}
NON_PRODUCT_PREFIXES = ("gift_", "DCGS")

# Analysis window: two full calendar years plus Dec-2009 for cohort seeding.
ANALYSIS_END = "2011-12-09"
