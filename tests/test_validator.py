"""Offline tests for the deterministic layers (no API key needed)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.sql_validator import validate  # noqa: E402


@pytest.mark.parametrize("sql", [
    "SELECT 1",
    "SELECT * FROM products WHERE unit_price > 10",
    "WITH t AS (SELECT 1 AS a) SELECT a FROM t",
    "SELECT country, COUNT(*) FROM customers GROUP BY country",
])
def test_valid_selects_pass(sql):
    assert validate(sql).ok


@pytest.mark.parametrize("sql", [
    "DROP TABLE products",
    "DELETE FROM orders",
    "UPDATE products SET unit_price = 0",
    "INSERT INTO products VALUES (1)",
    "SELECT * FROM",          # parse error
    "SELECT 1; SELECT 2",     # multiple statements
    "",                        # empty
])
def test_unsafe_or_invalid_sql_rejected(sql):
    assert not validate(sql).ok
