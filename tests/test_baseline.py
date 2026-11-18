from pathlib import Path

import pytest

from finance_agent.agent import run_agent
from finance_agent.baseline import route
from finance_agent.statement import load_statement

SAMPLE = Path(__file__).parent.parent / "data" / "sample_statement.csv"


@pytest.fixture(scope="module")
def df():
    return load_statement(SAMPLE)


@pytest.mark.parametrize(("question", "tool", "args"), [
    ("Quanto gastei com supermercado em setembro?", "total_spent",
     {"category": "groceries", "month": "2026-09"}),
    ("Which category did I spend the most on in October 2026?", "spending_by_category",
     {"month": "2026-10"}),
    ("Quais são minhas despesas recorrentes?", "recurring_charges", {}),
    ("Where do I spend the most money?", "top_merchants", {}),
    ("What is my credit card limit?", None, {}),
])
def test_route(df, question, tool, args):
    assert route(question, df) == (tool, args)


def test_baseline_answers_in_question_language(df):
    result = run_agent("Quanto gastei com comida em outubro de 2026?", df, model="baseline/rules")
    assert result.answer == "Você gastou R$ 234,40 com food (2026-10)."


def test_investment_question_is_refused_without_tools(df):
    result = run_agent("Should I invest in bitcoin?", df, model="baseline/rules")
    assert result.refused and not result.tool_calls
