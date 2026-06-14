"""Project paths and runtime settings."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "northwind.duckdb"

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
DEFAULT_MODEL = os.getenv("TEXT2SQL_MODEL", "openai/gpt-4o-mini")

# How many schema tables to inject into the prompt (schema-RAG top-k).
SCHEMA_TOP_K = int(os.getenv("TEXT2SQL_SCHEMA_TOP_K", "6"))
# Max self-correction attempts after a validation/execution error.
MAX_RETRIES = int(os.getenv("TEXT2SQL_MAX_RETRIES", "2"))
