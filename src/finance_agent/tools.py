"""Deterministic finance tools the agent can call.

The LLM chooses which tool to call and with which arguments; all arithmetic happens here.
"""

import pandas as pd


def total_spent(df: pd.DataFrame, category: str | None = None, month: str | None = None) -> dict:
    """Total spent (as a positive number), optionally filtered by category and month (YYYY-MM)."""
    expenses = df[df["amount"] < 0]
    if category:
        expenses = expenses[expenses["category"] == category.lower()]
    if month:
        expenses = expenses[expenses["month"] == month]
    return {
        "category": category,
        "month": month,
        "total": round(float(-expenses["amount"].sum()), 2),
        "transactions": len(expenses),
    }


def spending_by_category(df: pd.DataFrame, month: str | None = None) -> dict:
    """Spending per category, largest first, optionally for one month (YYYY-MM)."""
    expenses = df[df["amount"] < 0]
    if month:
        expenses = expenses[expenses["month"] == month]
    totals = (-expenses.groupby("category")["amount"].sum()).sort_values(ascending=False)
    return {"month": month, "by_category": {k: round(v, 2) for k, v in totals.items()}}


def top_merchants(df: pd.DataFrame, limit: int = 5, month: str | None = None) -> dict:
    """Merchants with the highest total spending."""
    expenses = df[df["amount"] < 0]
    if month:
        expenses = expenses[expenses["month"] == month]
    totals = (-expenses.groupby("description")["amount"].sum()).sort_values(ascending=False)
    return {"month": month, "merchants": {k: round(v, 2) for k, v in totals.head(limit).items()}}


def recurring_charges(df: pd.DataFrame) -> dict:
    """Expenses that appear in every month of the statement with the same description."""
    expenses = df[df["amount"] < 0]
    months = df["month"].nunique()
    counts = expenses.groupby("description")["month"].nunique()
    recurring = counts[counts == months].index
    avg = -expenses[expenses["description"].isin(recurring)].groupby("description")["amount"].mean()
    return {"recurring": {k: round(v, 2) for k, v in avg.sort_values(ascending=False).items()}}


TOOLS = {
    "total_spent": total_spent,
    "spending_by_category": spending_by_category,
    "top_merchants": top_merchants,
    "recurring_charges": recurring_charges,
}

_month = {"type": "string", "description": "Month in YYYY-MM format", "pattern": r"^\d{4}-\d{2}$"}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "total_spent",
            "description": "Total amount spent, optionally filtered by category and/or month.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Spending category, e.g. food, groceries, transport",
                    },
                    "month": _month,
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spending_by_category",
            "description": "Breakdown of spending per category, largest first.",
            "parameters": {"type": "object", "properties": {"month": _month}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "top_merchants",
            "description": "Merchants or descriptions with the highest total spending.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                    "month": _month,
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recurring_charges",
            "description": "Expenses that repeat every month, such as rent and subscriptions.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]
