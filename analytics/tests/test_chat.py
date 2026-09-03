"""Endpoint-level tests for POST /api/chat.

These exercise api/chat.handle() — the request path the frontend actually
uses — and prove:

- AI failure / missing key falls back to deterministic analytics answers
- simulation questions are answered by the deterministic simulator, not the LLM
- normal business questions can use the LLM
- the five core demo questions are grounded in the current analytics output

All tests are hermetic: they never hit a real provider.
"""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
API_DIR = os.path.join(ROOT, "api")
for _p in (ROOT, API_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analytics import llm as llm_mod  # noqa: E402
from analytics.simulate import run_scenario  # noqa: E402
from api import chat as chat_mod  # noqa: E402

QUESTIONS = [
    "What should I restock first?",
    "Why did sales fall last week?",
    "Which products are slowing down?",
    "Are there any unusual sales patterns?",
    "What happens if demand rises 20%?",
]


@pytest.fixture(autouse=True)
def _hermetic(monkeypatch):
    """No ambient API key leaks into tests; every LLM usage is mocked."""
    monkeypatch.setattr(llm_mod, "API_KEY", "")


def _enable_llm(monkeypatch, key="sk-test"):
    monkeypatch.setattr(llm_mod, "API_KEY", key)


# --------------------------------------------------------------------------
# input validation
# ---------------------------------------------------------------------------


def test_missing_question_returns_400():
    status, payload = chat_mod.handle({"analysis": {"kpis": {}}})
    assert status == 400
    assert payload["code"] == "missing_question"


def test_missing_analysis_returns_400():
    status, payload = chat_mod.handle({"question": "hi"})
    assert status == 400
    assert payload["code"] == "missing_analysis"


# --------------------------------------------------------------------------
# fallback behavior
# ---------------------------------------------------------------------------


def test_missing_api_key_falls_back_cleanly(sample_analysis):
    status, payload = chat_mod.handle(
        {"analysis": sample_analysis, "question": "What should I restock first?", "history": []}
    )
    assert status == 200
    assert payload["ok"] is True
    assert payload["mode"] == "deterministic"
    assert payload["related_view"] == "actions"
    assert payload["answer"]
    # Never leak configuration details to the user.
    assert "LLM_API_KEY" not in str(payload)


def test_provider_failure_falls_back_cleanly(monkeypatch, sample_analysis):
    _enable_llm(monkeypatch)

    def boom(question, analysis, history):
        raise chat_mod.LLMError("provider unreachable")

    monkeypatch.setattr(chat_mod, "llm_chat", boom)

    status, payload = chat_mod.handle(
        {"analysis": sample_analysis, "question": "Are there any unusual sales patterns?", "history": []}
    )
    assert status == 200
    assert payload["ok"] is True
    assert payload["mode"] == "deterministic"
    assert payload["related_view"] == "signals"
    assert payload["answer"]


def test_llm_success_uses_llm_mode(monkeypatch, sample_analysis):
    _enable_llm(monkeypatch)
    monkeypatch.setattr(chat_mod, "llm_chat", lambda q, a, h: "LLM explanation.")

    status, payload = chat_mod.handle(
        {"analysis": sample_analysis, "question": "Which products are slowing down?", "history": []}
    )
    assert status == 200
    assert payload["ok"] is True
    assert payload["available"] is True
    assert payload["mode"] == "llm"
    assert payload["answer"] == "LLM explanation."


def test_llm_receives_full_analytics_context(monkeypatch, sample_analysis):
    _enable_llm(monkeypatch)
    captured = {}

    def spy(question, analysis, history):
        captured["analysis"] = analysis
        captured["question"] = question
        return "LLM explanation."

    monkeypatch.setattr(chat_mod, "llm_chat", spy)

    chat_mod.handle(
        {"analysis": sample_analysis, "question": "What should I restock first?", "history": []}
    )
    assert captured["analysis"] is sample_analysis
    assert "kpis" in captured["analysis"]
    assert "forecast" in captured["analysis"]
    assert "anomalies" in captured["analysis"]
    assert "recommendations" in captured["analysis"]


def test_analytics_expose_verified_coverage_metric(sample_analysis):
    """Regression: the analytics the LLM receives include the verified
    per-product `coverage_days` metric, so the model never needs to derive
    days-of-cover (e.g. stock / forecast) itself."""
    products = sample_analysis.get("products", [])
    assert products, "expected products in analysis"
    for p in products:
        assert p.get("coverage_days") is not None
    assert any(isinstance(p.get("coverage_days"), (int, float)) and p["coverage_days"] >= 0 for p in products)


# --------------------------------------------------------------------------
# simulation questions must never reach the LLM
# ---------------------------------------------------------------------------


def test_whatif_uses_deterministic_simulator_not_llm(monkeypatch, sample_analysis):
    _enable_llm(monkeypatch)

    def unexpected(question, analysis, history):
        raise AssertionError("LLM must NOT be called for simulation questions")

    monkeypatch.setattr(chat_mod, "llm_chat", unexpected)

    base, adj = _whatif_numbers(sample_analysis)

    status, payload = chat_mod.handle(
        {"analysis": sample_analysis, "question": "What happens if demand rises 20%?", "history": []}
    )
    assert status == 200
    assert payload["ok"] is True
    assert payload["mode"] == "deterministic"
    assert payload["related_view"] == "simulate"
    answer = payload["answer"]
    assert f"{base:,}" in answer
    assert f"{adj:,}" in answer


# --------------------------------------------------------------------------
# grounding of the five core demo questions
# ---------------------------------------------------------------------------


def _product_names(analysis):
    return [p["name"] for p in analysis.get("products", [])]


def _top_inventory_rec_product(analysis):
    products = {p["name"]: p for p in analysis.get("products", [])}
    for r in analysis.get("recommendations", []):
        if r.get("category") == "inventory":
            for name in products:
                if name in r["title"]:
                    return name
    return None


def _slowest_product(analysis):
    decl = [
        p
        for p in analysis.get("products", [])
        if p.get("demand_change_pct") is not None and p["demand_change_pct"] < 0
    ]
    if not decl:
        return None
    return min(decl, key=lambda p: p["demand_change_pct"])["name"]


def _top_anomaly_product(analysis):
    anoms = sorted(analysis.get("anomalies", []), key=lambda a: -abs(a.get("z_score") or 0))
    return anoms[0]["product"] if anoms else None


def _whatif_numbers(analysis):
    res = run_scenario(analysis, {"type": "demand", "adjustment_pct": 20, "product": None})
    return (
        round(res["inputs"]["baseline_forecast_units"]),
        round(res["outputs"]["adjusted_forecast_units"]),
    )


@pytest.mark.parametrize(
    "question,related_view,token_fn",
    [
        ("What should I restock first?", "actions", _top_inventory_rec_product),
        ("Which products are slowing down?", "insights", _slowest_product),
        ("Are there any unusual sales patterns?", "signals", _top_anomaly_product),
        ("What happens if demand rises 20%?", "simulate", lambda a: max(_whatif_numbers(a))),
    ],
)
def test_question_is_grounded_in_analytics(sample_analysis, question, related_view, token_fn):
    token = token_fn(sample_analysis)
    assert token is not None, "fixture corruption: expected a derived token"

    status, payload = chat_mod.handle(
        {"analysis": sample_analysis, "question": question, "history": []}
    )
    assert status == 200
    assert payload["ok"] is True
    assert payload["mode"] == "deterministic"
    assert payload["related_view"] == related_view
    answer = payload["answer"]
    assert answer
    assert str(token) in answer, f"answer not grounded in analytics: {answer!r}"


def test_why_did_sales_fall_is_grounded_in_revenue_analytics(sample_analysis):
    status, payload = chat_mod.handle(
        {"analysis": sample_analysis, "question": "Why did sales fall last week?", "history": []}
    )
    assert status == 200
    assert payload["ok"] is True
    assert payload["related_view"] == "insights"
    answer = payload["answer"]
    assert answer
    assert "Revenue" in answer
    assert "$" in answer  # cites the computed money figures
    assert "couldn't produce" not in answer.lower()


def test_all_five_demo_questions_respond(sample_analysis):
    for q in QUESTIONS:
        status, payload = chat_mod.handle(
            {"analysis": sample_analysis, "question": q, "history": []}
        )
        assert status == 200, q
        assert payload["ok"] is True, q
        assert payload["answer"], q
        assert payload["mode"] in ("llm", "deterministic"), q