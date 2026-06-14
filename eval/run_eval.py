"""Execution Accuracy benchmark.

Compares the *result set* of generated SQL against the gold SQL (order-
insensitive), which is the standard Text-to-SQL metric and robust to
equivalent-but-different SQL. Run:

    python eval/run_eval.py
    python eval/run_eval.py --model anthropic/claude-3.5-sonnet
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import DEFAULT_MODEL  # noqa: E402
from src.executor import connect, run_query  # noqa: E402
from src.self_correct import answer  # noqa: E402

BENCHMARK = Path(__file__).resolve().parent / "benchmark.jsonl"


def _normalize(df: pd.DataFrame) -> set:
    """Order-insensitive comparable form of a result set."""
    rounded = df.round(4) if not df.empty else df
    return set(map(tuple, rounded.astype(str).values.tolist()))


def evaluate(model: str) -> float:
    con = connect()
    cases = [json.loads(line) for line in BENCHMARK.read_text(encoding="utf-8").splitlines() if line.strip()]

    passed = 0
    for case in cases:
        gold = _normalize(run_query(con, case["gold_sql"]))
        result = answer(case["question"], con, model=model)
        ok = result.ok and _normalize(result.df) == gold
        passed += ok
        flag = "PASS" if ok else "FAIL"
        retries = len(result.attempts) - 1
        print(f"[{flag}] {case['id']}: {case['question']}  (retries={retries})")
        if not ok:
            print(f"        generated: {result.sql or result.error}")

    acc = passed / len(cases) if cases else 0.0
    print(f"\nExecution Accuracy ({model}): {passed}/{len(cases)} = {acc:.1%}")
    return acc


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()
    evaluate(args.model)
