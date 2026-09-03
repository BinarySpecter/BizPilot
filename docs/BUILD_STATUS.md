# BizPilot AI — Build Status

**Project:** BizPilot AI — AI-powered decision-intelligence copilot for small businesses.
**Team:** BITS-STREAM · CodeBuild CodeBuild 1.0, Round 2.
**Last updated:** 2026-09-03

This file tracks what is **actually implemented** versus what is **roadmap only**.

---

## CHECKPOINTS

| # | Checkpoint | Status |
|---|-----------|--------|
| 1 | Project boots (`npm run build` + `next start` + local Python API) | ✅ Done |
| 2 | Sample CSV upload / "Try sample data" works | ✅ Done |
| 3 | Python analytics returns real JSON | ✅ Done |
| 4 | Dashboard renders real analytics | ✅ Done |
| 5 | Forecast works (WMA + trend + weekly seasonality, honest heuristic range) | ✅ Done |
| 6 | Anomaly detection works (robust rolling median + MAD, z ≥ 3) | ✅ Done |
| 7 | AI chat reads analytics JSON (grounded, no invention; deterministic fallback when no LLM) | ✅ Done |
| 8 | Recommendations derived from computed analytics | ✅ Done |
| 9 | What-if simulation recomputes real values | ✅ Done |
| 10 | Production build succeeds | ✅ Done |
| 11 | Deployment configuration documented | ✅ Done |

## IMPLEMENTED (verified by tests + manual end-to-end)

- **CSV upload** — drag/drop, file picker, alias-tolerant column mapping
  (`date`/`order_date`, `product`/`item`, `quantity`/`units`, `revenue`/`amount`,
  `stock`/`inventory`).
- **Data cleaning & validation** — tolerant parsing, row-level drop with counts,
  quality summary (`rows kept / dropped / bad dates / bad values / duplicates`).
- **Dashboard** — data status, KPI grid, revenue & demand trend charts (30d),
  product table (7d units, 14d momentum, stock, coverage, risk), forecast panel.
- **Forecast** — 7-day horizon, *Weighted moving average + linear trend + weekly
  seasonality*, honest heuristic range, method always surfaced in the UI.
- **Anomaly detection** — deterministic robust z-score (rolling median + MAD),
  per-product and aggregate, with `what` / `why` explanations.
- **AI reasoning layer** — `/api/chat` sends the computed analytics JSON to an
  OpenAI-compatible endpoint with a strict no-invention system prompt. Without a
  key (or on provider failure) it falls back to deterministic, evidence-based
  answers from the analytics — never a fake answer, never a config leak.
- **Recommendations** — rule-based, every recommendation carries
  `title / evidence / reason / priority` grounded in computed numbers.
- **What-if simulation** — demand (e.g. +20%) and inventory (e.g. +30%)
  scenarios that actually recompute coverage, stock gaps, and risk.
- **Verification** — 80 python tests pass (analytics + LLM grounding contract +
  endpoint-level chat behavior); typecheck and production build pass; manual
  end-to-end demo path (sample → analyze → forecast → anomaly → chat → scenario)
  verified through the running stack.

## NOT YET IMPLEMENTED (proposed, not built)

- Authentication / multi-user accounts
- Database persistence (deliberately out of scope for this MVP; everything is
  in-memory/stateless per request)
- Advanced forecasting (holiday effects, multi-series ML models)
- Richer what-if scenarios (price elasticity, promotions)
- Integrations (POS, QuickBooks, e-commerce platforms)
- Advanced agentic actions / automated follow-up actions
- Revenue-specific forecasting (currently demand/units focused)

## ERROR / HONESTY CASES HANDLED

- Empty file, missing date column, unreadable CSV → clear validation error.
- Insufficient history for forecast / anomalies → explained in UI, no invented numbers.
- Missing inventory → coverage reads "no inventory data", inventory scenarios disabled.
- Missing LLM key → deterministic, evidence-based answers from computed analytics; dashboard unaffected.
- Provider errors (401/429/network) → surfaced as messages, never silent failures.