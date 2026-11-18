"""Rule-based baseline agent (MODEL=baseline/rules).

A deterministic keyword router that picks a tool and fills its arguments without any LLM.
It exists for two reasons:

1. It is the floor every model must beat. If an LLM agent scores below this baseline on
   the eval set, the prompt or the tool descriptions need work.
2. It makes the whole pipeline (agent, evals, dashboard, CI) runnable offline, with no API
   key and no cost.

It deliberately has no understanding of language beyond keywords, so it fails on
paraphrases, relative dates and compound questions. Those failures are visible in the evals.
"""

import re
import unicodedata

import pandas as pd

from finance_agent import guardrails, tools

MONTHS = {
    "01": ["janeiro", "january", "jan"], "02": ["fevereiro", "february", "feb"],
    "03": ["marco", "march"], "04": ["abril", "april"], "05": ["maio", "may"],
    "06": ["junho", "june"], "07": ["julho", "july"], "08": ["agosto", "august", "aug"],
    "09": ["setembro", "september", "sept", "sep"], "10": ["outubro", "october", "oct"],
    "11": ["novembro", "november", "nov"], "12": ["dezembro", "december", "dec"],
}

CATEGORIES = {
    "food": ["food", "comida", "ifood", "restaurante", "restaurant", "delivery", "eating out"],
    "groceries": ["groceries", "grocery", "supermercado", "mercado", "supermarket"],
    "transport": ["transport", "transporte", "uber", "taxi", "corrida"],
    "subscriptions": ["subscription", "subscriptions", "assinatura", "assinaturas", "streaming"],
    "housing": ["housing", "rent", "aluguel", "moradia"],
    "health": ["health", "saude", "farmacia", "pharmacy", "remedio"],
    "leisure": ["leisure", "lazer", "cinema", "entertainment"],
    "education": ["education", "educacao", "livro", "livros", "book", "books", "livraria"],
    "savings": ["savings", "caixinha", "poupanca", "guardei", "saved"],
}

RECURRING = ["recorrente", "recorrentes", "recurring", "every month", "todo mes", "fixas", "fixed"]
BY_CATEGORY = ["category", "categoria", "categorias", "categories", "breakdown"]
MERCHANTS = ["where", "onde", "merchant", "merchants", "loja", "lojas", "estabelecimento"]
TOTAL = ["how much", "quanto", "total", "spend", "spent", "gastei", "gasto", "gastos"]


def _plain(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _has(text: str, words: list[str]) -> bool:
    return any(re.search(rf"\b{re.escape(w)}\b", text) for w in words)


def _month(text: str, df: pd.DataFrame) -> str | None:
    if match := re.search(r"\b(20\d{2})-(\d{2})\b", text):
        return match.group(0)
    year_match = re.search(r"\b(20\d{2})\b", text)
    year = year_match.group(1) if year_match else str(df["date"].dt.year.max())
    for number, names in MONTHS.items():
        if _has(text, names):
            return f"{year}-{number}"
    return None


def _category(text: str) -> str | None:
    for category, words in CATEGORIES.items():
        if _has(text, words):
            return category
    return None


def _brl(value: float, lang: str = "en") -> str:
    text = f"{value:,.2f}"
    if lang == "pt":  # 1,234.56 -> 1.234,56
        text = text.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {text}"


def route(question: str, df: pd.DataFrame) -> tuple[str | None, dict]:
    """Pick (tool name, arguments) for a question, or (None, {}) if nothing fits."""
    text = _plain(question)
    month = _month(text, df)
    args = {"month": month} if month else {}
    if _has(text, RECURRING):
        return "recurring_charges", {}
    if _has(text, BY_CATEGORY):
        return "spending_by_category", args
    if _has(text, MERCHANTS):
        return "top_merchants", args
    category = _category(text)
    if _has(text, TOTAL) or category:
        return "total_spent", ({"category": category} if category else {}) | args
    return None, {}


def run_baseline(question: str, df: pd.DataFrame):
    from finance_agent.agent import AgentResult

    lang = guardrails.language(question)
    name, args = route(question, df)
    if name is None:
        answer = (
            "Não encontrei essa informação no extrato." if lang == "pt"
            else "I couldn't find that in your statement."
        )
        return AgentResult(answer=answer)

    output = tools.TOOLS[name](df, **args)
    period = f" ({args['month']})" if args.get("month") else ""
    if name == "total_spent":
        total, category = _brl(output["total"], lang), output["category"]
        if lang == "pt":
            answer = f"Você gastou {total} " + (f"com {category}" if category else "no total")
        else:
            answer = f"You spent {total} " + (f"on {category}" if category else "in total")
        answer += f"{period}."
    elif name == "spending_by_category":
        top, value = next(iter(output["by_category"].items()))
        answer = (f"A maior categoria{period} foi {top}, com {_brl(value, lang)}." if lang == "pt"
                  else f"Your largest category{period} was {top}, with {_brl(value)}.")
    elif name == "top_merchants":
        top, value = next(iter(output["merchants"].items()))
        answer = (f"Onde você mais gastou{period}: {top}, {_brl(value, lang)}." if lang == "pt"
                  else f"You spent the most at {top}{period}: {_brl(value)}.")
    else:
        items = ", ".join(f"{k} ({_brl(v, lang)})" for k, v in output["recurring"].items())
        answer = (f"Suas despesas recorrentes: {items}." if lang == "pt"
                  else f"Your recurring expenses: {items}.")
    return AgentResult(answer=answer, tool_calls=[{"name": name, "arguments": args}])
