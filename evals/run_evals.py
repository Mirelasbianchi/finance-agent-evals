"""Run the agent over the eval dataset and save metrics.

Usage: uv run python evals/run_evals.py [--model anthropic/claude-sonnet-4-5]
"""

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from finance_agent.agent import run_agent
from finance_agent.statement import load_statement

EVALS_DIR = Path(__file__).parent
RESULTS_DIR = EVALS_DIR / "results"


def numbers_in(text: str) -> list[float]:
    """Extract numbers from an answer, accepting 1.234,56 (pt-BR) and 1,234.56 (en)."""
    values = []
    for raw in re.findall(r"\d[\d.,]*", text):
        raw = raw.rstrip(".,")  # sentence punctuation right after a number
        if re.search(r",\d{2}$", raw):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
        try:
            values.append(float(raw))
        except ValueError:
            continue
    return values


def score(case: dict, result) -> dict:
    called = [c["name"] for c in result.tool_calls]
    expected_tool = case["expected_tool"]
    tool_ok = (not called) if expected_tool is None else expected_tool in called
    args_ok = any(
        c["name"] == expected_tool
        and all(c["arguments"].get(k) == v for k, v in case["expected_args"].items())
        for c in result.tool_calls
    ) if expected_tool else tool_ok

    expected_value = case["expected_value"]
    value_ok = (
        None
        if expected_value is None
        else any(abs(v - expected_value) < 0.01 for v in numbers_in(result.answer))
    )
    return {"tool_ok": tool_ok, "args_ok": args_ok, "value_ok": value_ok}


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=os.getenv("MODEL"))
    args = parser.parse_args()

    df = load_statement(os.getenv("STATEMENT_PATH", "data/sample_statement.csv"))
    cases = [json.loads(line) for line in (EVALS_DIR / "dataset.jsonl").read_text().splitlines()]

    rows = []
    for case in cases:
        result = run_agent(case["question"], df, model=args.model)
        rows.append({
            "id": case["id"],
            "question": case["question"],
            "answer": result.answer,
            "tool_calls": result.tool_calls,
            "latency_s": result.latency_s,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            **score(case, result),
        })
        print(f"{case['id']:<22} tool={rows[-1]['tool_ok']!s:<5} value={rows[-1]['value_ok']}")

    valued = [r for r in rows if r["value_ok"] is not None]
    summary = {
        "model": args.model,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "cases": len(rows),
        "tool_accuracy": sum(r["tool_ok"] for r in rows) / len(rows),
        "args_accuracy": sum(r["args_ok"] for r in rows) / len(rows),
        "answer_accuracy": sum(r["value_ok"] for r in valued) / len(valued) if valued else None,
        "avg_latency_s": sum(r["latency_s"] for r in rows) / len(rows),
        "total_tokens": sum(r["input_tokens"] + r["output_tokens"] for r in rows),
    }

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"{datetime.now():%Y%m%d-%H%M%S}.json"
    out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2, ensure_ascii=False))
    print(json.dumps(summary, indent=2))
    print(f"Saved to {out}")


if __name__ == "__main__":
    main()
