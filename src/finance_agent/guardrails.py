"""Guardrails that run before and around the model.

- Investment advice is refused deterministically, before any model call: the agent only
  reports what is in the statement.
- Transaction descriptions come from third parties (merchants, people sending Pix), so they
  are untrusted. Instruction-like text inside them is neutralised before it reaches the model.
"""

import re
import unicodedata

INVESTMENT_REFUSAL = {
    "en": "I can only answer questions about your statement, so I can't recommend "
          "investments. A licensed financial advisor can help with that.",
    "pt": "Eu só respondo perguntas sobre o seu extrato, então não posso recomendar "
          "investimentos. Um assessor financeiro certificado pode ajudar com isso.",
}

_INVEST = re.compile(
    r"\b(invest\w*|bitcoin|crypto\w*|cripto\w*|acoes|stocks?|cdb|tesouro direto|"
    r"renda fixa|fundo imobiliario|fii|etf|day ?trade)\b"
)
_ADVICE = re.compile(r"\b(should|devo|deveria|vale a pena|worth|recomenda\w*|recommend\w*|melhor|best)\b")

_INJECTION = re.compile(
    r"(ignore|disregard|forget|ignor[ae]|esque[cç]a)\b.{0,40}\b(instruc|instruç|previous|anterior|rules|regras)"
    r"|\b(system prompt|you are now|voce agora e|act as|aja como)\b",
    re.IGNORECASE,
)


def _plain(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def language(text: str) -> str:
    """Rough language guess, enough to answer refusals in the question's language."""
    pt_markers = {"quanto", "quais", "qual", "gastei", "meu", "minha", "devo", "onde", "em", "com"}
    return "pt" if pt_markers & set(_plain(text).split()) else "en"


def asks_for_investment_advice(question: str) -> bool:
    plain = _plain(question)
    return bool(_INVEST.search(plain) and _ADVICE.search(plain))


def looks_like_injection(text: str) -> bool:
    return bool(_INJECTION.search(text))


def sanitize_description(text: str) -> str:
    """Keep descriptions as short opaque data; flag ones that try to instruct the model."""
    text = " ".join(str(text).split())[:80]
    return "[suspicious description removed]" if looks_like_injection(text) else text
