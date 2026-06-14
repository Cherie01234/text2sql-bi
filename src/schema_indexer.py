"""Schema-RAG: rank tables by relevance to a question and render DDL context.

This minimal implementation uses lightweight lexical overlap (no model
downloads, fully offline). The interface is deliberately the same shape you'd
get from an embedding retriever, so it can be swapped for FAISS + sentence
embeddings without touching the generator. See README "Upgrade path".
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import duckdb

# Human-written table descriptions improve retrieval and ground the LLM.
TABLE_DOCS = {
    "categories": "Product categories such as Beverages, Condiments, Seafood.",
    "products": "Products for sale, their category, unit price and whether discontinued.",
    "customers": "Customer companies and the country they are based in.",
    "employees": "Sales employees, their name and country.",
    "orders": "Order header: which customer ordered, which employee handled it, order date.",
    "order_details": "Order line items: product, quantity and unit price per order.",
}

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


@dataclass
class TableInfo:
    name: str
    ddl: str
    doc: str
    keywords: set[str]


def load_schema(con: duckdb.DuckDBPyConnection) -> list[TableInfo]:
    """Read every table's columns from DuckDB and build searchable docs."""
    tables = [r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main' ORDER BY table_name"
    ).fetchall()]

    infos: list[TableInfo] = []
    for name in tables:
        cols = con.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = ? ORDER BY ordinal_position",
            [name],
        ).fetchall()
        col_lines = ",\n  ".join(f"{c} {t}" for c, t in cols)
        ddl = f"CREATE TABLE {name} (\n  {col_lines}\n);"
        doc = TABLE_DOCS.get(name, "")
        keywords = _tokens(name) | _tokens(doc) | {c for c, _ in cols}
        infos.append(TableInfo(name=name, ddl=ddl, doc=doc, keywords=keywords))
    return infos


def select_tables(question: str, schema: list[TableInfo], top_k: int) -> list[TableInfo]:
    """Return the top_k tables most relevant to the question.

    Falls back to the full schema when it is small enough, so a weak retriever
    never silently drops a needed table.
    """
    if len(schema) <= top_k:
        return schema
    q = _tokens(question)
    scored = sorted(
        schema,
        key=lambda t: len(q & t.keywords),
        reverse=True,
    )
    return scored[:top_k]


def render_context(tables: list[TableInfo]) -> str:
    """Render selected tables as DDL + comments for the prompt."""
    blocks = []
    for t in tables:
        comment = f"-- {t.doc}\n" if t.doc else ""
        blocks.append(comment + t.ddl)
    return "\n\n".join(blocks)
