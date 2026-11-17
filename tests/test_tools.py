from pathlib import Path

import pytest

from finance_agent import tools
from finance_agent.statement import load_statement

SAMPLE = Path(__file__).parent.parent / "data" / "sample_statement.csv"


@pytest.fixture(scope="module")
def df():
    return load_statement(SAMPLE)


def test_total_spent_by_category_and_month(df):
    assert tools.total_spent(df, category="food", month="2026-10")["total"] == 234.40


def test_total_spent_ignores_income(df):
    assert tools.total_spent(df, category="income")["total"] == 0


def test_spending_by_category_is_sorted(df):
    values = list(tools.spending_by_category(df, month="2026-10")["by_category"].values())
    assert values == sorted(values, reverse=True)


def test_recurring_charges(df):
    recurring = tools.recurring_charges(df)["recurring"]
    assert {"Aluguel", "Spotify", "Netflix"} <= set(recurring)


def test_every_tool_has_a_schema():
    names = {s["function"]["name"] for s in tools.TOOL_SCHEMAS}
    assert names == set(tools.TOOLS)
