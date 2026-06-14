"""Orchestration: generate -> validate -> execute, with self-correction retries.

This is the core robustness story of the project. A raw LLM SQL call fails on
schema mistakes and dialect quirks; here every attempt is statically validated
and dry-run executed, and any error is fed back to the model for another try.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import duckdb
import pandas as pd

from . import schema_indexer, sql_generator, sql_validator
from .config import MAX_RETRIES, SCHEMA_TOP_K
from .executor import run_query


@dataclass
class Attempt:
    sql: str
    error: str = ""


@dataclass
class Text2SQLResult:
    ok: bool
    sql: str = ""
    df: pd.DataFrame | None = None
    tables_used: list[str] = field(default_factory=list)
    attempts: list[Attempt] = field(default_factory=list)
    error: str = ""


def answer(
    question: str,
    con: duckdb.DuckDBPyConnection,
    *,
    model: str | None = None,
    max_retries: int = MAX_RETRIES,
    top_k: int = SCHEMA_TOP_K,
) -> Text2SQLResult:
    schema = schema_indexer.load_schema(con)
    selected = schema_indexer.select_tables(question, schema, top_k)
    context = schema_indexer.render_context(selected)
    tables_used = [t.name for t in selected]

    attempts: list[Attempt] = []
    feedback: str | None = None

    for _ in range(max_retries + 1):
        sql = sql_generator.generate_sql(
            question, context, model=model, feedback=feedback
        )

        valid = sql_validator.validate(sql)
        if not valid.ok:
            attempts.append(Attempt(sql, valid.error))
            feedback = valid.error
            continue

        try:
            df = run_query(con, sql)
        except (duckdb.Error, Exception) as e:  # noqa: BLE001 - feed any DB error back
            attempts.append(Attempt(sql, str(e)))
            feedback = str(e)
            continue

        attempts.append(Attempt(sql))
        return Text2SQLResult(
            ok=True, sql=sql, df=df, tables_used=tables_used, attempts=attempts
        )

    return Text2SQLResult(
        ok=False,
        tables_used=tables_used,
        attempts=attempts,
        error=attempts[-1].error if attempts else "No SQL produced.",
    )
