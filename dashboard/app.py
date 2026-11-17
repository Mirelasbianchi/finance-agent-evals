"""Streamlit dashboard comparing eval runs.

Usage: uv run streamlit run dashboard/app.py
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

RESULTS_DIR = Path(__file__).parent.parent / "evals" / "results"

st.set_page_config(page_title="Finance Agent Evals", layout="wide")
st.title("Finance Agent Evals")

runs = sorted(RESULTS_DIR.glob("*.json"), reverse=True) if RESULTS_DIR.exists() else []
if not runs:
    st.info("No eval runs yet. Run `uv run python evals/run_evals.py` first.")
    st.stop()

summaries = pd.DataFrame([json.loads(p.read_text())["summary"] for p in runs])
st.subheader("Runs over time")
st.dataframe(summaries, use_container_width=True)
st.line_chart(
    summaries.sort_values("timestamp").set_index("timestamp")[
        ["tool_accuracy", "args_accuracy", "answer_accuracy"]
    ]
)

selected = st.selectbox("Inspect run", runs, format_func=lambda p: p.stem)
detail = json.loads(selected.read_text())
cols = st.columns(4)
s = detail["summary"]
cols[0].metric("Tool accuracy", f"{s['tool_accuracy']:.0%}")
cols[1].metric("Args accuracy", f"{s['args_accuracy']:.0%}")
cols[2].metric("Answer accuracy", f"{s['answer_accuracy']:.0%}" if s["answer_accuracy"] else "-")
cols[3].metric("Avg latency", f"{s['avg_latency_s']:.2f}s")

st.subheader("Cases")
st.dataframe(pd.DataFrame(detail["rows"]), use_container_width=True)
