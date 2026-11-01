"""Re-run q3 as it was before the fix, to check the projection-sensitivity finding.

Before commit 23cd4bb, q3 did not say which columns to return. Each model's
answer is judged with the same Execution Accuracy rule as run_eval.py, and we
also check whether a mismatching answer still names the same employee as the
gold SQL (i.e. the SQL is right and only the columns differ). Run:

    python eval/rerun_q3_before_fix.py --out eval/results/q3_before_fix.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import MAX_RETRIES, SCHEMA_TOP_K  # noqa: E402
from src.executor import connect, run_query  # noqa: E402
from src.self_correct import answer  # noqa: E402
from src.sql_generator import TEMPERATURE  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_eval import _normalize, _now  # noqa: E402

# q3 from eval/benchmark.jsonl at 23cd4bb^ (before the question and gold SQL were fixed).
OLD_Q3 = {
    "id": "q3",
    "question": "Which employee handled the most orders?",
    "gold_sql": (
        "SELECT e.first_name, e.last_name, COUNT(*) AS order_count FROM orders o "
        "JOIN employees e ON e.employee_id = o.employee_id "
        "GROUP BY e.first_name, e.last_name ORDER BY order_count DESC LIMIT 1"
    ),
}
MODELS = ["openai/gpt-4o-mini", "deepseek/deepseek-v4-flash", "google/gemini-2.5-flash-lite"]


def main(out: Path, repeat: int) -> None:
    con = connect()
    gold_df = run_query(con, OLD_Q3["gold_sql"])
    gold = _normalize(gold_df)
    gold_last_name = gold_df["last_name"].iloc[0]
    started_at = _now()

    runs = []
    for model in MODELS:
        for i in range(1, repeat + 1):
            result = answer(OLD_Q3["question"], con, model=model)
            df = result.df
            passed = result.ok and _normalize(df) == gold
            # Same employee if the gold last name appears in the single answer row.
            same = bool(result.ok and len(df) == 1
                        and any(gold_last_name in str(v) for v in df.iloc[0].tolist()))
            runs.append({
                "model": model,
                "run": i,
                "passed": bool(passed),
                "same_employee_as_gold": same,
                "columns": list(df.columns) if df is not None else None,
                "retries": len(result.attempts) - 1,
                "sql": result.sql,
                "error": result.error,
            })
            print(f"{model} run{i}: {'PASS' if passed else 'FAIL'} same_employee={same} columns={runs[-1]['columns']}")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "note": "q3 before commit 23cd4bb (output columns not specified), judged like run_eval.py",
        "started_at": started_at,
        "saved_at": _now(),
        "temperature": TEMPERATURE,
        "schema_top_k": SCHEMA_TOP_K,
        "max_retries": MAX_RETRIES,
        "question": OLD_Q3["question"],
        "gold_sql": OLD_Q3["gold_sql"],
        "gold_columns": list(gold_df.columns),
        "runs": runs,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved: {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "results" / "q3_before_fix.json")
    parser.add_argument("--repeat", type=int, default=3)
    args = parser.parse_args()
    main(args.out, args.repeat)
