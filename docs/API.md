# BizPilot AI — API Reference

All endpoints are Python serverless functions (Vercel) or served by the local
dev API (`scripts/dev_api.py`, port 8787). Bodies are JSON. Responses always
include `ok`, and errors include a human-readable `error` plus a machine `code`.

> **Grounding rule:** the AI layer only ever consumes the analytics document
> produced by `/api/analyze`. It never reads raw CSVs directly.

---

## `POST /api/analyze`

Process an uploaded dataset and return the full structured analytics document.

**Request**

```json
{
  "sales_csv": "date,product,quantity,revenue\n2026-01-01,A,10,199.90\n...",
  "sales_filename": "sales.csv",
  "inventory_csv": "date,product,stock\n2026-01-10,A,80\n...",
  "inventory_filename": "inventory.csv"
}
```

- `inventory_csv` / `inventory_filename` are optional.
- `GET /api/analyze` (or `POST` with `{"sample": true}`) analyzes the bundled
  demo dataset — this powers the **"Try sample data"** button.

**Response (`200`)**

```json
{
  "ok": true,
  "source": "sample" | "upload",
  "analysis": {
    "dataset": { "name", "rows", "date_min", "date_max", "n_products", "has_inventory", "product_names" },
    "data_quality": { "rows_in_source", "rows_kept", "dropped_rows", "dropped_pct", "bad_dates", "...", "date_column", "inventory_warning" },
    "kpis": { "total_revenue", "total_units", "avg_record_revenue", "recent_7d_revenue", "recent_7d_units", "recent_30d_revenue", "recent_30d_units", "days_covered", "date_range" },
    "inventory": { "available", "total_stock", "as_of", "products": [{"name","stock"}] },
    "trends": { "daily": [{"date","demand","revenue"}], "weekly": [{"week","demand","revenue"}] },
    "products": [ { "name","units","revenue","units_7d","units_last_14d","units_prior_14d","demand_change_pct","stock","forecast_7d","coverage_days","revenue_share_pct"} ],
    "forecast": { "available","horizon","method","values":[{"date","value"}],"total","low","high","baseline_daily","trend_direction","historical_days","seasonality_used","by_product" },
    "anomalies": [ { "date","product","observed","expected","direction","z_score","multiplier","scale","what","why" } ],
    "signals": [ { "key","label","phrase","direction","change_pct","period" } ],
    "recommendations": [ { "title","evidence","reason","priority","category" } ],
    "meta": { "engine_version", "generated_at" }
  }
}
```

When a value cannot be computed honestly, the engine returns `null` or an
explicit reason (e.g. `forecast.available=false`, `reason="Not enough historical
data..."`) — it never invents numbers.

**Column detection:** the cleaning layer recognizes a wide range of date/quantity/
revenue/stock headers (case- and separator-insensitive — `"Order Date"`,
`order_date`, `"sale date"`, `transaction_date`, `invoice_date`, `timestamp`,
`created_at`, …). If the header is unknown but the values look like dates, the
date column is detected by data content (`date_column` in `data_quality` reports
the original header that was used).

**Errors (`400`)** — `empty_file`, `missing_date`, `no_usable_rows`,
`no_numeric_values`, `bad_header`, `unreadable`, `invalid_inventory`.
Server failures return `500` `engine_error`.

---

## `POST /api/chat`

"Ask Your Business" — grounded AI reasoning over the analytics document.

**Request**

```json
{
  "question": "What should I restock first?",
  "analysis": { "...same document returned by /api/analyze..." },
  "history": [ { "role": "user" | "assistant", "content": "..." } ]
}
```

The frontend sends the *already-computed* analytics JSON (the exact numbers the
dashboard displays), so the model can only cite verified values.

**Response**

- `200` `{ "ok": true, "available": true, "answer": "..." }`
- `200` `{ "ok": false, "available": false, "message": "AI is not configured. Set LLM_API_KEY..." }`
  when no API key is set — surfaced as an explicit "AI unavailable" state.
- `200` `{ "ok": true, "available": true, "error": "<provider error>" }` for
  provider failures (401 / 429 / network).

---

## `POST /api/simulate`

What-if scenario recalculation.

**Request**

```json
{
  "analysis": { "...analytics document..." },
  "scenario": { "type": "demand" | "inventory", "adjustment_pct": 20, "product": "Wireless Earbuds" }
}
```

`product` optional — omit/`null` for all products.

**Response (`200`)**

```json
{
  "ok": true,
  "result": {
    "label": "Scenario — not a prediction",
    "type": "demand",
    "adjustment_pct": 20.0,
    "product": "Wireless Earbuds",
    "inputs": { "baseline_forecast_units": 182, "current_stock_units": 45 },
    "outputs": {
      "adjusted_forecast_units": 218, "forecast_change_units": 36,
      "coverage_days": 1.4, "baseline_coverage_days": 1.7,
      "stock_risk": true, "stock_gap_units": 173, "alert": "..."
    }
  }
}
```

---

## `GET /api/health`

`200` `{ "ok": true, "service": "..." }` — used to verify the Python process is up.