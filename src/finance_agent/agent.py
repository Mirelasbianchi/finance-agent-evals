"""Tool-calling agent loop."""

import json
import os
import time
from dataclasses import dataclass, field

import litellm
import pandas as pd

from finance_agent.tools import TOOL_SCHEMAS, TOOLS

SYSTEM_PROMPT = """You are a personal finance assistant. You answer questions about the user's \
bank statement.

Rules:
- Always use the tools to get numbers. Never calculate or guess values yourself.
- Amounts are in Brazilian reais (R$). Months use the YYYY-MM format.
- If the statement does not contain the information, say so.
- Do not give investment advice.
- Answer in the same language as the question, in at most three sentences."""

MAX_STEPS = 5


@dataclass
class AgentResult:
    answer: str
    tool_calls: list[dict] = field(default_factory=list)
    latency_s: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0


def run_agent(question: str, df: pd.DataFrame, model: str | None = None) -> AgentResult:
    model = model or os.getenv("MODEL", "anthropic/claude-sonnet-4-5")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    result = AgentResult(answer="")
    start = time.perf_counter()

    for _ in range(MAX_STEPS):
        response = litellm.completion(model=model, messages=messages, tools=TOOL_SCHEMAS)
        result.input_tokens += response.usage.prompt_tokens
        result.output_tokens += response.usage.completion_tokens
        message = response.choices[0].message

        if not message.tool_calls:
            result.answer = message.content or ""
            break

        messages.append(message.model_dump())
        for call in message.tool_calls:
            args = json.loads(call.function.arguments or "{}")
            output = TOOLS[call.function.name](df, **args)
            result.tool_calls.append({"name": call.function.name, "arguments": args})
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": json.dumps(output)}
            )

    result.latency_s = round(time.perf_counter() - start, 3)
    return result
