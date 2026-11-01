"""Execution Accuracy benchmark.

Compares the *result set* of generated SQL against the gold SQL (order-
insensitive), which is the standard Text-to-SQL metric and robust to
equivalent-but-different SQL. Run:

    python eval/run_eval.py
    python eval/run_eval.py --model anthropic/claude-3.5-sonnet
    python eval/run_eval.py --model openai/gpt-4o-mini --repeat 3 --out eval/results/gpt-4o-mini.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import DEFAULT_MODEL, MAX_RETRIES, SCHEMA_TOP_K  # noqa: E402
from src.executor import connect, run_query  # noqa: E402
from src.self_correct import answer  # noqa: E402
from src.sql_generator import TEMPERATURE  # noqa: E402

BENCHMARK = Path(__file__).resolve().parent / "benchmark.jsonl"


def _normalize(df: pd.DataFrame) -> set:
    """Order-insensitive comparable form of a result set."""
    rounded = df.round(4) if not df.empty else df
    return set(map(tuple, rounded.astype(str).values.tolist()))


def evaluate(model: str) -> dict:
    con = connect()
    cases = [json.loads(line) for line in BENCHMARK.read_text(encoding="utf-8").splitlines() if line.strip()]

    passed = 0
    records = []
    for case in cases:
        gold_df = run_query(con, case["gold_sql"])
        gold = _normalize(gold_df)
        result = answer(case["question"], con, model=model)
        ok = result.ok and _normalize(result.df) == gold
        passed += ok
        flag = "PASS" if ok else "FAIL"
        retries = len(result.attempts) - 1
        print(f"[{flag}] {case['id']}: {case['question']}  (retries={retries})")
        if not ok:
            print(f"        generated: {result.sql or result.error}")
        records.append({
            "id": case["id"],
            "passed": bool(ok),
            "retries": retries,
            "sql": result.sql,
            "error": result.error,
            # Kept so that vacuous matches (e.g. an empty gold result) can be spotted later.
            "gold_rows": len(gold_df),
            "rows": len(result.df) if result.df is not None else None,
            "columns": list(result.df.columns) if result.df is not None else None,
        })

    acc = passed / len(cases) if cases else 0.0
    print(f"\nExecution Accuracy ({model}): {passed}/{len(cases)} = {acc:.1%}")
    return {"passed": passed, "total": len(cases), "execution_accuracy": acc, "cases": records}


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _save(out: Path, model: str, started_at: str, runs: list[dict]) -> None:
    # Hash with LF line endings so the value matches across OSes (git autocrlf).
    benchmark_text = BENCHMARK.read_text(encoding="utf-8").replace("\r\n", "\n")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "model": model,
        "started_at": started_at,
        "saved_at": _now(),
        "benchmark": BENCHMARK.name,
        "benchmark_sha256": hashlib.sha256(benchmark_text.encode("utf-8")).hexdigest(),
        "temperature": TEMPERATURE,
        "schema_top_k": SCHEMA_TOP_K,
        "max_retries": MAX_RETRIES,
        "runs": runs,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved: {out}")


def _positive_int(value: str) -> int:
    n = int(value)
    if n < 1:
        raise argparse.ArgumentTypeError("must be 1 or more")
    return n


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--repeat", type=_positive_int, default=1,
                        help="run the benchmark N times (LLM output can vary between runs)")
    parser.add_argument("--out", type=Path, help="save per-question results of every run as JSON")
    args = parser.parse_args()

    started_at = _now()
    runs = []
    for _ in range(args.repeat):
        runs.append(evaluate(args.model))
        if args.out:  # save after every run so an API error later keeps the finished runs
            _save(args.out, args.model, started_at, runs)
