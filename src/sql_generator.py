"""LLM-backed SQL generation via OpenRouter."""
from __future__ import annotations

import re

from openai import OpenAI

from .config import DEFAULT_MODEL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL

# Greedy decoding keeps outputs as stable as the provider allows (not fully deterministic).
TEMPERATURE = 0

SYSTEM_PROMPT = """You are an expert data analyst who writes DuckDB SQL.
Rules:
- Use ONLY the tables and columns in the provided schema.
- Output a single read-only SELECT statement. Never write or modify data.
- Prefer explicit JOINs and clear column aliases.
- Return ONLY the SQL, with no prose and no markdown code fences.
"""

USER_TEMPLATE = """Schema:
{schema}

Question: {question}

SQL:"""

_FENCE = re.compile(r"^```(?:sql)?|```$", re.MULTILINE)


def _client() -> OpenAI:
    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return OpenAI(base_url=OPENROUTER_BASE_URL, api_key=OPENROUTER_API_KEY)


def _clean(sql: str) -> str:
    return _FENCE.sub("", sql).strip().rstrip(";")


def generate_sql(
    question: str,
    schema_context: str,
    *,
    model: str | None = None,
    feedback: str | None = None,
) -> str:
    """Generate SQL for a question. `feedback` carries a prior error for retries."""
    user = USER_TEMPLATE.format(schema=schema_context, question=question)
    if feedback:
        user += (
            f"\n\nThe previous attempt failed with this error:\n{feedback}\n"
            "Fix the SQL and return only the corrected SELECT."
        )

    resp = _client().chat.completions.create(
        model=model or DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        temperature=TEMPERATURE,
    )
    return _clean(resp.choices[0].message.content or "")
