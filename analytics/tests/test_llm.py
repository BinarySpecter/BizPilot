"""Tests for the LLM reasoning layer — grounding, request contract and
honest failure handling. The analytics engine stays the numerical source of
truth; these tests pin down that the LLM only ever interprets computed facts.
"""

import pytest

from analytics import llm


def test_system_prompt_enforces_grounding_contract():
    p = llm.SYSTEM_PROMPT
    # Only supplied analytics may be used
    assert "Use only the supplied analytics" in p
    assert "Every quantitative claim" in p
    # Explicit prohibitions (numbers, products, events, percentages)
    assert "Never invent numbers" in p
    assert "Never invent metrics" in p
    assert "products" in p
    assert "events" in p
    assert "percentages" in p
    # No self-computed forecasts / scenario arithmetic
    assert "Never calculate new forecasts" in p
    assert "arithmetic" in p
    # Insufficient evidence -> say so
    assert "does not support an answer" in p
    assert "say so explicitly" in p


def test_system_prompt_forbids_calculating_new_metrics():
    """Regression: the model must not derive new quantities from supplied
    numbers (e.g. computing 45/182 days-of-cover); it must cite the verified
    metric the analytics engine already supplies (products[].coverage_days)."""
    p = llm.SYSTEM_PROMPT
    assert "Never perform arithmetic or derive new quantitative metrics" in p
    assert "ratios" in p.lower() or "coverage_days" in p
    assert "coverage_days" in p
    assert "cite that supplied value directly" in p
    assert "do not recompute it" in p
    assert "do not perform the arithmetic" in p


def test_not_configured_raises_unavailable(monkeypatch):
    monkeypatch.setattr(llm, "API_KEY", "")
    assert llm.is_configured() is False
    with pytest.raises(llm.LLMUnavailableError):
        llm.chat("Restock?", {"a": 1})


def test_context_facts_are_embedded_in_prompt(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["question"] = json["messages"][-1]["content"]

        class R:
            status_code = 200

            def json(self):
                return {"choices": [{"message": {"content": "grounded answer"}}]}

            @property
            def text(self):
                return ""

        return R()

    monkeypatch.setattr(llm, "API_KEY", "test-key")
    monkeypatch.setattr(llm.requests, "post", fake_post)

    ctx = {
        "kpis": {"total_units": 1234, "total_revenue": 98765.0},
        "forecast": {"total": 77, "low": 60, "high": 90},
        "products": [{"name": "Wireless Earbuds", "stock": 45, "forecast_7d": 182, "coverage_days": 1.7}],
        "anomalies": [{"product": "Bluetooth Speakers", "date": "2026-08-17"}],
    }
    llm.chat("How many units next week?", ctx)

    q = captured["question"]
    assert '"total_units": 1234' in q
    assert '"total_revenue": 98765.0' in q
    assert '"total": 77' in q
    assert "Wireless Earbuds" in q
    assert "Bluetooth Speakers" in q
    # the verified days-of-coverage metric is in the prompt, so the model can
    # cite it instead of computing 45/182 itself
    assert '"coverage_days": 1.7' in q


def test_request_uses_openai_compatible_format(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.update(url=url, headers=headers, json=json, timeout=timeout)

        class R:
            status_code = 200

            def json(self):
                return {"choices": [{"message": {"content": "ok"}}]}

            @property
            def text(self):
                return ""

        return R()

    monkeypatch.setattr(llm, "API_KEY", "sk-test-123")
    monkeypatch.setattr(llm, "BASE_URL", "https://llm.example/v1")
    monkeypatch.setattr(llm, "MODEL", "acme-model")
    monkeypatch.setattr(llm.requests, "post", fake_post)

    llm.chat("What changed?", {"kpis": {"total_units": 10}})

    assert captured["url"] == "https://llm.example/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer sk-test-123"
    assert captured["headers"]["Content-Type"] == "application/json"
    body = captured["json"]
    assert body["model"] == "acme-model"
    assert body["temperature"] == 0.2
    assert body["max_tokens"] == 700
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][-1]["role"] == "user"
    assert "What changed?" in body["messages"][-1]["content"]


def test_history_is_passed_through_last_8(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["messages"] = json["messages"]

        class R:
            status_code = 200

            def json(self):
                return {"choices": [{"message": {"content": "ok"}}]}

            @property
            def text(self):
                return ""

        return R()

    monkeypatch.setattr(llm, "API_KEY", "test-key")
    monkeypatch.setattr(llm.requests, "post", fake_post)

    history = [
        {"role": "user", "content": "first?"},
        {"role": "assistant", "content": "first answer"},
        {"role": "user", "content": "second?"},
        {"role": "assistant", "content": "second answer"},
    ]
    llm.chat("third?", {"a": 1}, history)

    roles = [m["role"] for m in captured["messages"]]
    assert roles == ["system", "user", "assistant", "user", "assistant", "user"]


def test_401_reported_as_llm_error(monkeypatch):
    class R:
        status_code = 401

        def json(self):
            return {}

        @property
        def text(self):
            return "unauthorized"

    monkeypatch.setattr(llm, "API_KEY", "test-key")
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: R())
    with pytest.raises(llm.LLMError, match="401"):
        llm.chat("hi", {})


def test_429_reported_as_rate_limit(monkeypatch):
    class R:
        status_code = 429

        def json(self):
            return {}

        @property
        def text(self):
            return "rate limited"

    monkeypatch.setattr(llm, "API_KEY", "test-key")
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: R())
    with pytest.raises(llm.LLMError, match="429"):
        llm.chat("hi", {})


def test_malformed_json_raises_llm_error(monkeypatch):
    class R:
        status_code = 200

        def json(self):
            raise ValueError("not json")

        @property
        def text(self):
            return ""

    monkeypatch.setattr(llm, "API_KEY", "test-key")
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: R())
    with pytest.raises(llm.LLMError):
        llm.chat("hi", {})


def test_empty_answer_raises_llm_error(monkeypatch):
    class R:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "   "}}]}

        @property
        def text(self):
            return ""

    monkeypatch.setattr(llm, "API_KEY", "test-key")
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: R())
    with pytest.raises(llm.LLMError, match="empty answer"):
        llm.chat("hi", {})