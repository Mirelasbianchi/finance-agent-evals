"""Load and normalize bank statements."""

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {"date", "description", "amount", "category"}


def load_statement(path: str | Path) -> pd.DataFrame:
    """Read a CSV statement with columns date, description, amount, category.

    Negative amounts are expenses and positive amounts are income.
    """
    df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Statement is missing columns: {sorted(missing)}")
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = df["amount"].astype(float)
    df["category"] = df["category"].str.lower().str.strip()
    df["month"] = df["date"].dt.strftime("%Y-%m")
    return df.sort_values("date").reset_index(drop=True)
