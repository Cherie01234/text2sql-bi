"""DuckDB connection + query execution helpers."""
from __future__ import annotations

import duckdb
import pandas as pd

from .config import DB_PATH


def connect() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. "
            "Run `python data/build_northwind.py` first."
        )
    # read_only so a generated query can never mutate the warehouse.
    return duckdb.connect(str(DB_PATH), read_only=True)


def run_query(con: duckdb.DuckDBPyConnection, sql: str) -> pd.DataFrame:
    """Execute SQL and return a DataFrame. Raises on SQL errors."""
    return con.execute(sql).df()
