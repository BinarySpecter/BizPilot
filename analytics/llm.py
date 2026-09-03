"""OpenAI-compatible LLM client for the AI reasoning layer.

The LLM only ever receives the *computed analytics JSON* as numerical context.
It is instructed — via the system prompt — to never invent quantitative claims.
"""

from __future__ import annotations

import os
from typing import Dict, List

import requests

# Provider-agnostic OpenAI-compatible configuration.
BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
API_KEY = os.environ.get("LLM_API_KEY", "").strip()
MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = (
    "You are BizPilot AI, a decision-intelligence copilot for a small business. "
    "You interpret business analytics that were computed by the analytics engine and supplied "
    "to you below. You do not compute business numbers yourself.\n\n"
    "RULES:\n"
    "1. Use only the supplied analytics. Every quantitative claim you make (forecast, revenue, "
    "units, inventory, percentages, anomalies, rankings) must be present in the supplied "
    "analytics JSON.\n"
    "2. Never invent numbers, products, customers, events, dates, or percentages. Never invent "
    "metrics or results that are not in the JSON.\n"
    "3. Never perform arithmetic or derive new quantitative metrics from the supplied numbers. "
    "Never calculate new forecasts, growth rates, prices, percentages, differences, ratios, or "
    "scenario outcomes yourself. If an equivalent metric already exists in the analytics (for "
    "example inventory `coverage_days`, demand-change percentages, revenue shares, or daily "
    "averages), cite that supplied value directly — do not recompute it. If a computation is "
    "needed (for example, a what-if scenario), state that the scenario must be computed by the "
    "analytics/simulation layer — do not perform the arithmetic.\n"
    "4. If the supplied data does not support an answer, say so explicitly rather than guessing "
    "or filling gaps.\n"
    "5. When you make a claim, cite the supporting computed fact naturally, e.g. 'Product A has a "
    "7-day forecast of 184 units' — only if 184 appears in the data.\n"
    "6. Keep answers concise, business-focused and actionable.\n"
    "7. Distinguish facts computed from data vs. general business judgment; label judgment as such."
)


class LLMUnavailableError(Exception):
    pass


class LLMError(Exception):
    pass


def is_configured() -> bool:
    return bool(API_KEY)


def chat(question: str, analytics_context: Dict, history: List[Dict] | None = None) -> str:
    if not API_KEY:
        raise LLMUnavailableError(
            "AI is not configured. Set LLM_API_KEY (and, if needed, LLM_BASE_URL / LLM_MODEL) "
            "as environment variables."
        )

    import json as _json
    from datetime import datetime, timezone

    context_block = _json.dumps(analytics_context, default=str)[:60000]
    user_content = (
        f"CURRENT DATE: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n\n"
        f"USER QUESTION: {question}\n\n"
        f"VERIFIED ANALYTICS CONTEXT (the only permitted source of numbers):\n"
        f"{context_block}"
    )

    messages: List[Dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        for msg in history[-8:]:
            role = msg.get("role")
            content = msg.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_content})

    try:
        resp = requests.post(
            f"{BASE_URL.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 700,
            },
            timeout=45,
        )
    except requests.exceptions.RequestException as exc:
        raise LLMError(f"Could not reach the AI provider: {exc}")

    if resp.status_code == 401:
        raise LLMError("AI provider rejected the API key (401). Check LLM_API_KEY.")
    if resp.status_code == 429:
        raise LLMError("AI provider rate limit reached (429). Try again shortly.")
    if resp.status_code != 200:
        raise LLMError(f"AI provider error {resp.status_code}: {resp.text[:300]}")

    try:
        data = resp.json()
    except ValueError as exc:
        raise LLMError(f"AI provider returned an invalid response body: {exc}")

    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise LLMError("AI provider returned an unexpected response shape.")
    if not isinstance(text, str) or not text.strip():
        raise LLMError("AI provider returned an empty answer.")
    return text.strip()