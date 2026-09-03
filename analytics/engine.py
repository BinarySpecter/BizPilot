"""End-to-end analysis pipeline.

`analyze()` is the single entry point shared by the /api/analyze endpoint, the
simulation module, and the test suite. It produces one canonical JSON document
consumed by the dashboard, the recommendations engine, and the AI layer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

from . import __version__
from .anomalies import detect_anomalies
from .cleaning import load_dataset, summarize_quality, ValidationError  # noqa: F401
from .forecasting import forecast_series, product_forecasts
from .metrics import (
    attach_inventory_to_products,
    compute_metrics,
    compute_signals,
)
from .recommendations import build_recommendations
from .schemas import jsonable


def analyze(
    sales_raw: bytes,
    sales_filename: str,
    inventory_raw: Optional[bytes] = None,
    inventory_filename: Optional[str] = None,
) -> Dict:
    """Process uploaded CSVs and return the full structured analysis JSON.

    Raises ValidationError for unrecoverable problems.
    """
    ds = load_dataset(sales_raw, sales_filename, inventory_raw, inventory_filename)
    sales = ds["sales"]
    inventory = ds["inventory"]
    quality = summarize_quality(sales, ds["quality"])

    metrics = compute_metrics(sales, inventory)
    attach_inventory_to_products(metrics["products"], inventory)

    # ---------------- forecasting ----------------
    forecast = forecast_series(sales, horizon=7)
    if forecast["available"]:
        by_product = product_forecasts(sales, horizon=7)
        forecast["by_product"] = by_product
    else:
        forecast["by_product"] = {}

    for p in metrics["products"]:
        pf = forecast["by_product"].get(p["name"], {})
        p["forecast_7d"] = pf.get("total") if pf.get("available") else None
        if p.get("stock") is not None and p.get("forecast_7d"):
            fc = float(p["forecast_7d"])
            if fc > 0:
                p["coverage_days"] = round(float(p["stock"]) / (fc / 7.0), 1)

    # ---------------- anomalies ----------------
    anomaly_result = detect_anomalies(sales)
    anomalies = anomaly_result["anomalies"]

    # ---------------- signals + recommendations ----------------
    inventory_total = (
        float(metrics["inventory"].get("total_stock"))
        if metrics["inventory"].get("available")
        else None
    )
    signals = compute_signals(
        metrics["kpis"],
        metrics["products"],
        forecast_total=float(forecast.get("total") or 0),
        forecast_available=bool(forecast.get("available")),
        inventory_total=inventory_total,
        anomalies=anomalies,
        has_qty=bool(sales["quantity"].notna().any()),
    )
    recommendations = build_recommendations(
        metrics["products"],
        forecast_available=bool(forecast.get("available")),
        forecast_total=float(forecast.get("total") or 0),
        forecast_by_product=forecast["by_product"],
        inventory_total=inventory_total,
        anomalies=anomalies,
        data_quality=quality,
    )

    dataset = {
        "name": sales_filename,
        "rows": int(len(sales)),
        "date_min": quality["date_min"],
        "date_max": quality["date_max"],
        "n_products": quality["n_products"],
        "has_inventory": bool(metrics["inventory"].get("available")),
        "product_names": [p["name"] for p in metrics["products"]],
    }

    return {
        "dataset": dataset,
        "data_quality": quality,
        "kpis": metrics["kpis"],
        "inventory": metrics["inventory"],
        "trends": {
            "daily": metrics["daily"],
            "weekly": metrics["weekly"],
        },
        "forecast": forecast,
        "anomalies": anomalies,
        "products": metrics["products"],
        "signals": signals,
        "recommendations": recommendations,
        "meta": {
            "engine_version": __version__,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def to_response(obj: Dict) -> Dict:
    """Coerce any numpy/pandas values to plain JSON-safe Python types."""
    return jsonable(obj)