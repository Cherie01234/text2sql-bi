"""Static SQL validation: reject unsafe / unparseable SQL before it runs.

This is a deterministic guard layer that runs *before* the database. It catches
two classes of problem without spending an LLM call or touching data:
  1. Non-SELECT / data-mutating statements (defense in depth on top of the
     read-only connection).
  2. Syntactically invalid SQL (via sqlglot parsing into DuckDB dialect).
"""
from __future__ import annotations

from dataclasses import dataclass

import sqlglot
from sqlglot import expressions as exp

WRITE_NODES = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop,
    exp.Create, exp.Alter, exp.Command,
)


@dataclass
class ValidationResult:
    ok: bool
    error: str = ""


def validate(sql: str) -> ValidationResult:
    sql = sql.strip().rstrip(";")
    if not sql:
        return ValidationResult(False, "Empty SQL.")

    try:
        statements = sqlglot.parse(sql, read="duckdb")
    except sqlglot.errors.ParseError as e:
        return ValidationResult(False, f"Parse error: {e}")

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        return ValidationResult(False, "Exactly one statement is allowed.")

    tree = statements[0]
    if isinstance(tree, WRITE_NODES) or tree.find(*WRITE_NODES):
        return ValidationResult(False, "Only read-only SELECT queries are allowed.")
    if not isinstance(tree, (exp.Select, exp.Subquery, exp.With, exp.Union)):
        return ValidationResult(False, "Query must be a SELECT.")

    return ValidationResult(True)
