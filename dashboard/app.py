"""Streamlit app: ask the agent, explore the statement and compare eval runs.

Usage: uv run streamlit run dashboard/app.py
"""

import json
import os
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from finance_agent.agent import run_agent
from finance_agent.statement import load_statement

ROOT = Path(__file__).parent.parent
RESULTS_DIR = ROOT / "evals" / "results"
INK, MUTED, GRID, ACCENT, FAIL = "#16201c", "#5d6b65", "#e3e7e4", "#1f6f5c", "#c2410c"
KIND_ORDER = ["lookup", "ranking", "paraphrase", "unanswerable", "refusal"]
KIND_HELP = {
    "lookup": "Direct questions with a category and a month",
    "ranking": "Largest category, top merchants, recurring charges",
    "paraphrase": "Same intents in words the tools don't use",
    "unanswerable": "Data that is not in the statement; must not invent numbers",
    "refusal": "Investment advice; must refuse",
}

load_dotenv(ROOT / ".env")
st.set_page_config(page_title="Finance Agent Evals", page_icon="📒", layout="wide")


def style(chart: alt.Chart) -> alt.Chart:
    return (
        chart.configure_view(strokeWidth=0)
        .configure_axis(labelColor=MUTED, titleColor=MUTED, gridColor=GRID, domainColor=GRID,
                        tickColor=GRID, labelFontSize=12, titleFontSize=12)
        .configure(font="Inter, system-ui, sans-serif")
    )


@st.cache_data
def statement() -> pd.DataFrame:
    return load_statement(ROOT / os.getenv("STATEMENT_PATH", "data/sample_statement.csv"))


def load_runs() -> list[dict]:
    if not RESULTS_DIR.exists():
        return []
    runs = [json.loads(p.read_text()) | {"file": p.stem} for p in RESULTS_DIR.glob("*.json")]
    return sorted(runs, key=lambda r: r["summary"]["timestamp"], reverse=True)


def brl(value: float) -> str:
    return "R$ " + f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


st.title("Finance Agent")
st.caption(
    "An LLM agent that answers questions about a bank statement through deterministic tools, "
    "measured by an evaluation suite. All data here is synthetic."
)

ask_tab, statement_tab, evals_tab = st.tabs(["Ask the agent", "Statement", "Eval runs"])

# --- Ask -------------------------------------------------------------------------------------
with ask_tab:
    model = os.getenv("MODEL") or "baseline/rules"
    left, right = st.columns([1, 1], gap="large")
    with left:
        examples = [
            "Quanto gastei com comida em outubro de 2026?",
            "Which category did I spend the most on in September 2026?",
            "Quais são minhas despesas recorrentes?",
            "Should I invest my savings in bitcoin?",
        ]
        picked = st.pills("Try one", examples, key="example")
        question = st.text_input("Your question", value=picked or "",
                                 placeholder="How much did I spend on transport?")
        if question:
            with st.spinner("Thinking"):
                result = run_agent(question, statement(), model=model)
            st.markdown(f"#### {result.answer}")
            meta = f"`{model}` · {result.latency_s * 1000:.0f} ms"
            if result.input_tokens:
                meta += f" · {result.input_tokens + result.output_tokens} tokens"
            if result.cost_usd:
                meta += f" · US$ {result.cost_usd:.4f}"
            st.caption(meta)
    with right:
        if question:
            st.markdown("**How it got there**")
            if result.refused:
                st.info("Refused by the investment-advice guardrail before any model call.")
            elif not result.tool_calls:
                st.info("No tool fits this question, so the agent did not produce numbers.")
            for call in result.tool_calls:
                st.code(f"{call['name']}({json.dumps(call['arguments'], ensure_ascii=False)})",
                        language="python", wrap_lines=True)
        else:
            st.markdown(
                "The model never does arithmetic. It picks one of four tools (`total_spent`, "
                "`spending_by_category`, `top_merchants`, `recurring_charges`), the tool computes "
                "the number with pandas, and the model explains it."
            )

# --- Statement -------------------------------------------------------------------------------
with statement_tab:
    df = statement()
    expenses = df[df["amount"] < 0].assign(spent=lambda d: -d["amount"])
    months = sorted(df["month"].unique())
    cols = st.columns(len(months) + 1)
    for col, month in zip(cols, months, strict=False):
        income = df[(df["month"] == month) & (df["amount"] > 0)]["amount"].sum()
        spent = expenses[expenses["month"] == month]["spent"].sum()
        col.metric(f"Spent in {month}", brl(spent), help=f"Income {brl(income)}")
    cols[-1].metric("Transactions", len(df))

    by_cat = expenses.groupby(["category", "month"], as_index=False)["spent"].sum()
    order = by_cat.groupby("category")["spent"].sum().sort_values(ascending=False).index.tolist()
    month_colors = alt.Scale(domain=months, range=["#9cc9bb", ACCENT][-len(months):])
    chart = (
        alt.Chart(by_cat)
        .mark_bar(cornerRadiusEnd=4, height={"band": 0.8})
        .encode(
            y=alt.Y("category:N", sort=order, title=None),
            yOffset=alt.YOffset("month:N", sort=months),
            x=alt.X("spent:Q", title="Spent (R$)", axis=alt.Axis(format=",.0f", tickCount=6)),
            color=alt.Color("month:N", scale=month_colors,
                            legend=alt.Legend(title=None, orient="top")),
            tooltip=["category", "month", alt.Tooltip("spent:Q", format=",.2f", title="R$")],
        )
        .properties(height=420, title="Spending by category and month")
    )
    st.altair_chart(style(chart), width="stretch")
    with st.expander("Transactions"):
        st.dataframe(df.drop(columns=["month"]), hide_index=True, width="stretch")

# --- Evals -----------------------------------------------------------------------------------
with evals_tab:
    runs = load_runs()
    if not runs:
        st.info("No eval runs yet. Run `uv run python evals/run_evals.py --model baseline/rules`.")
        st.stop()

    labels = {f"{r['summary']['model']}  ({r['summary']['timestamp']})": r for r in runs}
    run = labels[st.selectbox("Run", list(labels))]
    s = run["summary"]
    c = st.columns(5)
    c[0].metric("Pass rate", f"{s.get('pass_rate', 0):.0%}")
    c[1].metric("Right tool", f"{s['tool_accuracy']:.0%}")
    c[2].metric("Right arguments", f"{s['args_accuracy']:.0%}")
    c[3].metric("Right number", f"{s['answer_accuracy']:.0%}" if s["answer_accuracy"] else "-")
    c[4].metric("Cost", f"US$ {s.get('total_cost_usd', 0):.4f}",
                help=f"{s['total_tokens']} tokens, avg latency {s['avg_latency_s']:.2f}s")

    rows = pd.DataFrame(run["rows"])
    kinds = (
        rows.groupby("kind")["passed"].agg(["mean", "count", "sum"]).reset_index()
        .rename(columns={"mean": "pass_rate", "sum": "passed"})
    )
    kinds["help"] = kinds["kind"].map(KIND_HELP)
    kinds["label"] = kinds.apply(lambda r: f"{r['passed']}/{r['count']}", axis=1)
    base = alt.Chart(kinds).encode(
        y=alt.Y("kind:N", sort=KIND_ORDER, title=None),
        x=alt.X("pass_rate:Q", title="Pass rate", scale=alt.Scale(domain=[0, 1]),
                axis=alt.Axis(format="%", tickCount=5)),
        tooltip=["kind", "help", alt.Tooltip("pass_rate:Q", format=".0%"), "label"],
    )
    bars = base.mark_bar(color=ACCENT, cornerRadiusEnd=4, height={"band": 0.62})
    text = base.mark_text(align="left", dx=6, color=INK).encode(text="label:N")
    st.altair_chart(style((bars + text).properties(height=230, title="Pass rate by kind of question")),
                    width="stretch")

    if len(runs) > 1:
        history = pd.DataFrame([r["summary"] for r in runs])
        history["run"] = history["model"] + " " + history["timestamp"].str[5:16]
        trend = (
            alt.Chart(history).mark_line(point=alt.OverlayMarkDef(size=70, filled=True), color=ACCENT)
            .encode(x=alt.X("timestamp:T", title=None),
                    y=alt.Y("pass_rate:Q", title="Pass rate", axis=alt.Axis(format="%")),
                    tooltip=["model", "timestamp", alt.Tooltip("pass_rate:Q", format=".0%")])
            .properties(height=220, title="Pass rate across runs")
        )
        st.altair_chart(style(trend), width="stretch")

    st.markdown("**Cases**")
    only_failures = st.toggle("Only failures", value=False)
    view = rows[~rows["passed"]] if only_failures else rows
    view = view.assign(tools=view["tool_calls"].map(lambda calls: ", ".join(c["name"] for c in calls)))
    st.dataframe(
        view[["passed", "kind", "id", "question", "answer", "tools", "latency_s"]],
        hide_index=True, width="stretch",
        column_config={"passed": st.column_config.CheckboxColumn("✓", width="small")},
    )
