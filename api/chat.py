"""POST /api/chat — Ask Your Business.

The frontend sends the already-computed analytics JSON plus the user's question.
The LLM reasons ONLY over that verified context (see analytics/llm.py).

Architecture:
  USER QUESTION
      -> EXISTING COMPUTED ANALYTICS
      -> STRUCTURED BUSINESS CONTEXT
      -> LLM  (or deterministic rules engine when no LLM is available)
      -> NATURAL LANGUAGE EXPLANATION

Python/deterministic analytics remain the source of truth. The LLM never
calculates business numbers itself; it only explains the computed facts.

The rules engine (built on the same analytics the dashboard shows) also
intercepts simulation questions ("what happens if demand rises 20%?") and
answers them with the deterministic simulator rather than LLM arithmetic.
"""

from __future__ import annotations

import re
from http.server import BaseHTTPRequestHandler

from api import _common  # noqa: F401
from analytics.llm import (
    LLMError,
    LLMUnavailableError,
    chat as llm_chat,
    is_configured,
)
from analytics.simulate import run_scenario

# --------------------------------------------------------------------------
# formatting helpers
# ---------------------------------------------------------------------------


def _num(value) -> str:
    if value is None:
        return "—"
    try:
        return f"{round(float(value)):,}"
    except (TypeError, ValueError):
        return "—"


def _pct(value) -> str:
    if value is None:
        return "—"
    try:
        v = round(float(value))
        return f"{v:+,}%"
    except (TypeError, ValueError):
        return "—"


def _money(value) -> str:
    if value is None:
        return "—"
    try:
        v = float(value)
        if abs(v) >= 1_000_000:
            return f"${v / 1_000_000:.2f}M"
        if abs(v) >= 1_000:
            return f"${v / 1_000:.1f}K"
        return f"${v:,.0f}"
    except (TypeError, ValueError):
        return "—"


def _product_map(analysis) -> dict:
    return {p.get("name"): p for p in analysis.get("products", []) if p.get("name")}


def _recent_revenue_delta(analysis) -> dict | None:
    """last-7 vs prior-7 revenue change computed from the daily series."""
    daily = analysis.get("trends", {}).get("daily", [])
    vals = [d.get("revenue") for d in daily if d.get("revenue") is not None]
    if len(vals) < 14:
        return None
    last7, prev7 = sum(vals[-7:]), sum(vals[-14:-7])
    if not prev7:
        return None
    return {"last7": last7, "prev7": prev7, "pct": (last7 - prev7) / prev7 * 100}


def _coverage_days(analysis) -> float | None:
    inv = analysis.get("inventory", {})
    fc = analysis.get("forecast", {})
    if not inv.get("available"):
        return None
    stock = inv.get("total_stock") or 0
    total = fc.get("total")
    if not total:
        return None
    return stock / (float(total) / 7.0)


# --------------------------------------------------------------------------
# deterministic answers (one per supported intent)
# ---------------------------------------------------------------------------


def _answer_summary(analysis) -> tuple[str, str]:
    kpis = analysis.get("kpis", {})
    fc = analysis.get("forecast", {})
    recs = analysis.get("recommendations", [])
    anoms = analysis.get("anomalies", [])
    parts = ["Here is the current state of the business:\n"]
    parts.append(
        f"- Revenue **{_money(kpis.get('total_revenue'))}** · **{_num(kpis.get('total_units'))} units** sold"
    )
    if fc.get("available") and fc.get("total") is not None:
        parts.append(
            f"- Next 7 days: **{_num(fc.get('total'))} units** expected demand "
            f"(range {_num(fc.get('low'))}–{_num(fc.get('high'))})"
        )
    if recs:
        parts.append(f"- Top action: **{recs[0].get('title')}** — {recs[0].get('evidence')}")
    if anoms:
        a = anoms[0]
        parts.append(
            f"- Attention: **{a.get('product')}** {_num(a.get('observed'))} units "
            f"vs baseline {_num(a.get('expected'))}"
        )
    return "\n".join(parts), "overview"


def _answer_restock(analysis) -> tuple[str, str]:
    products = _product_map(analysis)
    inv_recs = [r for r in analysis.get("recommendations", []) if r.get("category") == "inventory"]
    risky = sorted(
        (
            p
            for p in products.values()
            if p.get("stock") is not None
            and p.get("forecast_7d")
            and float(p["forecast_7d"] or 0) > float(p["stock"] or 0)
        ),
        key=lambda p: float(p["forecast_7d"]) / float(p["stock"]),
        reverse=True,
    )

    target = None
    if inv_recs:
        for r in inv_recs:
            for name, p in products.items():
                if name and name in r.get("title", ""):
                    target = p
                    break
            if target:
                break
    if target is None and risky:
        target = risky[0]

    if target:
        fc = target.get("forecast_7d")
        stock = target.get("stock")
        return (
            f"**{target['name']}** should be restocked first.\n\n"
            f"The 7-day forecast is **{_num(fc)} units** against **{_num(stock)} units** "
            f"on hand — the largest current stock-out risk.\n\n"
            f"- Recommended action: review replenishment for **{target['name']}**.",
            "actions",
        )

    if inv_recs:
        r = inv_recs[0]
        return (
            f"Start with the top replenishment action: **{r.get('title')}**.\n\n"
            f"Its evidence: {r.get('evidence')}.",
            "actions",
        )

    return "No product currently has forecast demand above on-hand stock — inventory looks adequate for the next week.", "actions"


def _answer_slowing(analysis) -> tuple[str, str]:
    products = analysis.get("products", [])
    decl = [p for p in products if p.get("demand_change_pct") is not None and p["demand_change_pct"] < 0]
    decl.sort(key=lambda p: p["demand_change_pct"])
    top = decl[:3]
    if not top:
        return "No products are currently slowing down — demand is steady or rising across the range.", "insights"
    bullets = "\n".join(
        f"- **{p['name']}** — {_pct(p['demand_change_pct'])} vs prior 14 days "
        f"({_num(p.get('units_last_14d'))} units in last 14d)"
        for p in top
    )
    return f"These products are losing momentum:\n\n{bullets}\n\nRanked by 14-day demand change from the computed analytics.", "insights"


def _answer_anomaly(analysis) -> tuple[str, str]:
    anoms = sorted(analysis.get("anomalies", []), key=lambda a: -abs(a.get("z_score") or 0))[:3]
    if not anoms:
        return "No unusual sales patterns found within the anomaly threshold (robust baseline, z ≥ 3).", "signals"
    bullets = "\n".join(
        f"- **{a.get('product')}** · {_num(a.get('observed'))} units vs baseline {_num(a.get('expected'))} "
        f"(z = {a.get('z_score', 0):.1f})"
        for a in anoms
    )
    return f"These patterns stand out:\n\n{bullets}\n\nDetected against the rolling baseline, largest deviations first.", "signals"


def _answer_forecast(analysis) -> tuple[str, str]:
    fc = analysis.get("forecast", {})
    if not fc.get("available"):
        return f"Forecast unavailable: {fc.get('reason') or 'not enough history to estimate the next 7 days.'}", "insights"
    line = f"**{_num(fc.get('total'))} units** are expected over the next **{fc.get('horizon', 7)} days**"
    if fc.get("low") is not None and fc.get("high") is not None:
        line += f" (range {_num(fc.get('low'))}–{_num(fc.get('high'))})"
    line += ". This is a statistical estimate, not a guarantee."
    by_product = fc.get("by_product") or {}
    top = sorted(
        ((name, b) for name, b in by_product.items() if b.get("available") and b.get("total")),
        key=lambda item: -item[1]["total"],
    )[:3]
    if top:
        line += "\n\nLargest contributors:\n" + "\n".join(
            f"- **{name}** — {_num(b['total'])} units" for name, b in top
        )
    return line, "insights"


def _answer_coverage(analysis) -> tuple[str, str]:
    inv = analysis.get("inventory", {})
    if not inv.get("available"):
        return "No inventory file attached — upload an inventory.csv to see stock coverage.", "insights"
    days = _coverage_days(analysis)
    stock = inv.get("total_stock")
    fc_total = analysis.get("forecast", {}).get("total")
    line = f"On-hand stock of **{_num(stock)} units** covers "
    if days is not None:
        line += f"about **~{days:.1f} days** of projected demand (**{_num(fc_total)} units** over 7 days)."
    else:
        line += f"against **{_num(fc_total)} units** of projected 7-day demand."
    risky = sorted(
        (
            p
            for p in analysis.get("products", [])
            if p.get("coverage_days") is not None and p["coverage_days"] < 7
        ),
        key=lambda p: p["coverage_days"],
    )[:3]
    if risky:
        line += "\n\nLowest cover:\n" + "\n".join(
            f"- **{p['name']}** — ~{p['coverage_days']:.1f} days" for p in risky
        )
    return line, "insights"


def _answer_whatif(analysis, question: str) -> tuple[str, str]:
    match = re.search(r"(\d{1,3})\s*(?:%|percent|pct)", question, re.I)
    pct = int(match.group(1)) if match else 20
    positive_words = ("rise", "increase", "grow", "up", "raise", "gain", "+", "higher")
    negative_words = ("fall", "drop", "decrease", "down", "reduce", "lower", "-", "decline")
    positive = not any(w in question.lower() for w in negative_words)
    if any(w in question.lower() for w in positive_words):
        positive = True
    applied = pct if positive else -pct

    result = run_scenario(analysis, {"type": "demand", "adjustment_pct": applied, "product": None})
    inputs = result.get("inputs", {})
    outputs = result.get("outputs", {})
    base = inputs.get("baseline_forecast_units")
    adj = outputs.get("adjusted_forecast_units")
    change = outputs.get("forecast_change_units")
    cov = outputs.get("coverage_days")
    risk = outputs.get("stock_risk")

    direction = "rises" if positive else "falls"
    line = f"If demand {direction} by **{pct}%**, projected demand moves from **{_num(base)} units** to **{_num(adj)} units**"
    if change is not None:
        line += f" (**{'+' if change > 0 else ''}{_num(change)} units** vs baseline)"
    line += "."
    if cov is not None:
        line += f"\n\nStock coverage would be **~{cov:.1f} days**"
        if risk:
            line += " — under 7 days, a stock-out window within the forecast horizon."
        else:
            line += ", which still covers projected demand."
    line += "\n\nScenario — not a prediction. Explore the numbers in the simulator."
    return line, "simulate"


def _answer_revenue(analysis) -> tuple[str, str]:
    delta = _recent_revenue_delta(analysis)
    products = analysis.get("products", [])
    decl = sorted(
        [p for p in products if p.get("demand_change_pct") is not None and p["demand_change_pct"] < 0],
        key=lambda p: p["demand_change_pct"],
    )
    anoms = analysis.get("anomalies", [])

    if delta is None:
        line = "Revenue information is available from the trend series, but there is not enough history to compare last week against the prior one."
    elif abs(delta["pct"]) >= 0.5:
        line = (
            f"Revenue is **{_pct(delta['pct'])}** over the last 7 days "
            f"({_money(delta['last7'])} vs {_money(delta['prev7'])} the week before)."
        )
    else:
        line = (
            f"Revenue over the last 7 days (**{_money(delta['last7'])}**) is broadly flat "
            f"vs the prior week (**{_money(delta['prev7'])}**)."
        )

    if decl and decl[0]["demand_change_pct"] <= -1:
        p = decl[0]
        line += f"\n\nThe clearest product-level decline: **{p['name']}** at {_pct(p['demand_change_pct'])} over 14 days."
    else:
        anoms_sorted = sorted(anoms, key=lambda a: -abs(a.get("z_score") or 0))
        if anoms_sorted:
            a = anoms_sorted[0]
            line += (
                f"\n\nFlagged pattern: **{a.get('product')}** {_num(a.get('observed'))} units "
                f"vs baseline {_num(a.get('expected'))}."
            )
    line += "\n\nAll figures computed from your uploaded data."
    return line, "insights"


# --------------------------------------------------------------------------
# intent detection
# ---------------------------------------------------------------------------

INTENTS = (
    (
        "whatif",
        ("what if", "happens if", "would happen", "scenario", "simulate", "if demand", "if i", "rises by", "drops by", "increase demand", "decrease demand"),
    ),
    ("restock", ("restock", "reorder", "replenish", "order first", "stock first", "what to order", "buy first", "inventory first", "run out")),
    ("anomaly", ("anomal", "unusual", "pattern", "spike", "odd", "abnormal", "weird", "outlier", "alert")),
    ("revenue", ("why did", "why has", "sales fall", "sales drop", "revenue", "what changed", "went down")),
    ("slowing", ("slow", "declin", "momentum", "sluggish", "cooling", "falling")),
    ("coverage", ("cover", "out of stock", "how long", "stock last", "inventory days", "days of stock")),
    ("forecast", ("forecast", "next week", "expected to sell", "sell next", "demand next", "projection")),
)


def _detect_intent(question: str) -> str | None:
    q = question.lower()
    for intent, keywords in INTENTS:
        if any(k in q for k in keywords):
            return intent
    # "Why did revenue rise 20%?" — a numeric change over demand/stock/sales is
    # treated as a scenario, not a what-happened question.
    if re.search(r"\d{1,3}\s*(%|percent|pct)", q) and any(k in q for k in ("demand", "stock", "sales", "inventory")):
        return "whatif"
    return None


def _rules_answer(analysis, question: str) -> tuple[str, str] | None:
    """Return a grounded (answer, suggested_view) pair, or None if the
    analytics can't support the question."""
    intent = _detect_intent(question)
    handlers = {
        "summary": _answer_summary,
        "restock": _answer_restock,
        "anomaly": _answer_anomaly,
        "revenue": _answer_revenue,
        "slowing": _answer_slowing,
        "coverage": _answer_coverage,
        "forecast": _answer_forecast,
    }
    try:
        if intent == "whatif":
            return _answer_whatif(analysis, question)
        handler = handlers.get(intent or "summary")
        return handler(analysis)
    except Exception:
        return None


# --------------------------------------------------------------------------
# endpoint
# ---------------------------------------------------------------------------


def handle(payload: dict) -> tuple[int, dict]:
    question = (payload.get("question") or "").strip()
    analysis = payload.get("analysis")
    history = payload.get("history") or []

    if not question:
        return 400, {"ok": False, "error": "Missing question.", "code": "missing_question"}
    if not analysis:
        return 400, {
            "ok": False,
            "error": "Missing analytics context. Run the analysis first.",
            "code": "missing_analysis",
        }

    # Simulation questions are answered by the deterministic simulator —
    # never by LLM arithmetic. The LLM explains; analytics calculate.
    if _detect_intent(question) == "whatif":
        answer = _rules_answer(analysis, question)
        if answer:
            text, view = answer
            return 200, {"ok": True, "available": False, "answer": text, "mode": "deterministic", "related_view": view}

    if is_configured():
        try:
            answer = llm_chat(question, analysis, history)
            return 200, {"ok": True, "available": True, "answer": answer, "mode": "llm"}
        except (LLMUnavailableError, LLMError):
            pass  # fall through to the evidence-based rules engine

    # No LLM (or LLM failure) — answer from the computed analytics directly.
    answer = _rules_answer(analysis, question)
    if answer:
        text, view = answer
        return 200, {"ok": True, "available": False, "answer": text, "mode": "deterministic", "related_view": view}

    return 200, {
        "ok": False,
        "available": False,
        "message": "We couldn't produce an answer for that question right now — try one of the suggested questions.",
    }


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        payload = _common.read_json_body(self)
        _common.respond(self, handle(payload))
        return
        # vercel:handler