"""CLI: python -m finance_agent "your question"."""

import os
import sys

from dotenv import load_dotenv

from finance_agent.agent import run_agent
from finance_agent.statement import load_statement


def main() -> None:
    load_dotenv()
    question = " ".join(sys.argv[1:]) or "How much did I spend in total?"
    df = load_statement(os.getenv("STATEMENT_PATH", "data/sample_statement.csv"))
    result = run_agent(question, df)
    print(result.answer)
    print(f"\n[tools: {[c['name'] for c in result.tool_calls]} | {result.latency_s}s]")


if __name__ == "__main__":
    main()
