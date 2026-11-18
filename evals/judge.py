"""LLM-as-judge scoring with a written rubric.

Exact-number checks cover lookups, but not whether an answer is grounded, clear and in the
right language. The judge reads the question, the tool results the agent saw and the answer,
and returns a 1-5 score per criterion with a one-line reason.
"""

import json

import litellm

RUBRIC = """You grade answers from a personal finance assistant that must only use data
returned by its tools. Score each criterion from 1 (bad) to 5 (excellent):

- grounded: every number and fact in the answer appears in the tool results. If no tool was
  called, the answer must not contain statement figures. Invented numbers score 1.
- helpful: the answer addresses the question directly; refusing investment advice or saying
  the data is not in the statement counts as helpful when that is the right response.
- language: the answer is in the same language as the question and reads naturally.

Reply with JSON only:
{"grounded": n, "helpful": n, "language": n, "reason": "one sentence"}"""


def judge(question: str, tool_results: list, answer: str, model: str) -> dict:
    payload = json.dumps(
        {"question": question, "tool_results": tool_results, "answer": answer},
        ensure_ascii=False,
    )
    response = litellm.completion(
        model=model,
        messages=[{"role": "system", "content": RUBRIC}, {"role": "user", "content": payload}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    text = response.choices[0].message.content or "{}"
    scores = json.loads(text[text.find("{"): text.rfind("}") + 1])
    scores["mean"] = round(sum(scores[k] for k in ("grounded", "helpful", "language")) / 3, 2)
    return scores
