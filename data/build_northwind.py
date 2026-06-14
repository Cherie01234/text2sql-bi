"""Build a compact, offline Northwind subset as a DuckDB database.

Run once before launching the app:

    python data/build_northwind.py

This keeps the demo fully self-contained (no downloads, deterministic data so
the evaluation benchmark has stable ground-truth answers).
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import DB_PATH  # noqa: E402

SCHEMA = """
DROP TABLE IF EXISTS order_details;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS employees;

CREATE TABLE categories (
    category_id   INTEGER PRIMARY KEY,
    category_name VARCHAR
);

CREATE TABLE products (
    product_id   INTEGER PRIMARY KEY,
    product_name VARCHAR,
    category_id  INTEGER,
    unit_price   DECIMAL(10,2),
    discontinued BOOLEAN
);

CREATE TABLE customers (
    customer_id   INTEGER PRIMARY KEY,
    company_name  VARCHAR,
    country       VARCHAR
);

CREATE TABLE employees (
    employee_id INTEGER PRIMARY KEY,
    first_name  VARCHAR,
    last_name   VARCHAR,
    country     VARCHAR
);

CREATE TABLE orders (
    order_id    INTEGER PRIMARY KEY,
    customer_id INTEGER,
    employee_id INTEGER,
    order_date  DATE
);

CREATE TABLE order_details (
    order_id   INTEGER,
    product_id INTEGER,
    quantity   INTEGER,
    unit_price DECIMAL(10,2)
);
"""

DATA = {
    "categories": [
        (1, "Beverages"),
        (2, "Condiments"),
        (3, "Confections"),
        (4, "Seafood"),
    ],
    "products": [
        (1, "Chai", 1, 18.00, False),
        (2, "Chang", 1, 19.00, False),
        (3, "Aniseed Syrup", 2, 10.00, False),
        (4, "Chef Anton's Cajun Seasoning", 2, 22.00, False),
        (5, "Pavlova", 3, 17.45, False),
        (6, "Sir Rodney's Marmalade", 3, 81.00, False),
        (7, "Ikura", 4, 31.00, False),
        (8, "Boston Crab Meat", 4, 18.40, True),
    ],
    "customers": [
        (1, "Alfreds Futterkiste", "Germany"),
        (2, "Around the Horn", "UK"),
        (3, "Bottom-Dollar Markets", "Canada"),
        (4, "Eastern Connection", "UK"),
        (5, "Great Lakes Food Market", "USA"),
    ],
    "employees": [
        (1, "Nancy", "Davolio", "USA"),
        (2, "Andrew", "Fuller", "USA"),
        (3, "Janet", "Leverling", "UK"),
    ],
    "orders": [
        (10248, 1, 1, "1997-07-04"),
        (10249, 2, 3, "1997-07-05"),
        (10250, 3, 1, "1997-07-08"),
        (10251, 1, 2, "1997-08-12"),
        (10252, 5, 2, "1998-01-15"),
        (10253, 4, 3, "1998-02-20"),
        (10254, 5, 1, "1998-03-21"),
    ],
    "order_details": [
        (10248, 1, 12, 18.00),
        (10248, 5, 10, 17.45),
        (10249, 2, 9, 19.00),
        (10250, 7, 35, 31.00),
        (10250, 1, 15, 18.00),
        (10251, 3, 6, 10.00),
        (10251, 6, 4, 81.00),
        (10252, 5, 40, 17.45),
        (10253, 4, 20, 22.00),
        (10254, 7, 25, 31.00),
        (10254, 2, 18, 19.00),
    ],
}


def build() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = duckdb.connect(str(DB_PATH))
    try:
        con.execute(SCHEMA)
        for table, rows in DATA.items():
            placeholders = ", ".join(["?"] * len(rows[0]))
            con.executemany(f"INSERT INTO {table} VALUES ({placeholders})", rows)
        con.commit()
        n = con.execute("SELECT COUNT(*) FROM order_details").fetchone()[0]
        print(f"Built {DB_PATH} ({n} order detail rows).")
    finally:
        con.close()


if __name__ == "__main__":
    build()
