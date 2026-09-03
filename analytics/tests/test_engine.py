"""Tests for KPIs, trends, forecast, anomalies, and recommendations."""

import pytest

from analytics.anomalies import detect_anomalies
from analytics.forecasting import forecast_series
from analytics.metrics import compute_metrics
from analytics.simulate import run_scenario


def test_kpis_sample(sample_analysis):
    k = sample_analysis["kpis"]
    assert k["total_revenue"] > 0
    assert k["total_units"] > 0
    assert k["recent_7d_units"] > 0
    assert k["days_covered"] >= 88
    # honesty: average record revenue must be consistent with totals
    assert k["avg_record_revenue"] == pytest.approx(k["total_revenue"] / k["revenue_rows"], rel=0.01)


def test_kpis_quantity_only_persists():
    csv = "date,product,units\n2026-01-01,A,5\n2026-01-02,B,7\n"
    from analytics.cleaning import load_dataset
    from analytics.metrics import compute_metrics

    ds = load_dataset(csv.encode(), "q.csv")
    m = compute_metrics(ds["sales"], None)
    assert m["kpis"]["total_revenue"] is None
    assert m["kpis"]["total_units"] == pytest.approx(12)


def test_forecast_availability_sample(sample_analysis):
    fc = sample_analysis["forecast"]
    assert fc["available"] is True
    assert len(fc["values"]) == fc["horizon"] == 7
    assert fc["method"] is not None
    assert fc["total"] > 0
    assert fc["low"] is not None and fc["high"] is not None
    assert fc["low"] <= fc["total"] <= fc["high"]


def test_forecast_insufficient_data():
    from analytics.cleaning import load_dataset

    csv = "date,product,quantity,revenue\n" + "\n".join(f"2026-01-{i:02d},A,10,100" for i in range(1, 4))
    ds = load_dataset(csv.encode(), "short.csv")
    fc = forecast_series(ds["sales"])
    assert fc["available"] is False
    assert "Not enough" in fc["reason"]
    assert fc["total"] is None


def test_forecast_never_negative():
    from analytics.cleaning import load_dataset

    csv = "date,product,quantity,revenue\n" + "\n".join(f"2026-01-{i:02d},A,2,20" for i in range(1, 20))
    ds = load_dataset(csv.encode(), "flat.csv")
    fc = forecast_series(ds["sales"], horizon=7)
    assert fc["available"] is True
    assert all(v["value"] >= 0 for v in fc["values"])


def test_products_table_demand_change(sample_analysis):
    products = sample_analysis["products"]
    assert len(products) >= 3
    for p in products:
        assert p["units_last_14d"] is not None
    # demand change should be consistent with the two windows
    speakers = next(p for p in products if p["name"] == "Bluetooth Speakers")
    assert speakers["demand_change_pct"] < 0


def test_anomaly_detection_deterministic(sample_analysis, ):
    anoms = sample_analysis["anomalies"]
    assert anoms  # sample data contains a strong spike
    peak = next(a for a in anoms if a["direction"] == "up" and a["product"] == "Bluetooth Speakers")
    assert peak["observed"] > peak["expected"]
    assert peak["z_score"] > 3
    assert peak["why"] and peak["what"]


def test_anomaly_insufficient_data():
    from analytics.cleaning import load_dataset

    csv = "date,product,quantity,revenue\n" + "\n".join(f"2026-01-{i:02d},A,10,100" for i in range(1, 9))
    ds = load_dataset(csv.encode(), "short.csv")
    res = detect_anomalies(ds["sales"])
    assert res["available"] is False
    assert res["anomalies"] == []


def test_anomaly_detects_injected_spike():
    from analytics.cleaning import load_dataset

    rows = ["date,product,quantity,revenue"]
    rows += [
        f"2026-01-{i:02d},A,20,200"
        for i in range(1, 31)
    ]
    rows[16] = "2026-01-16,A,80,800"  # injected spike
    csv = "\n".join(rows)
    ds = load_dataset(csv.encode(), "spike.csv")
    res = detect_anomalies(ds["sales"])
    assert res["available"] is True
    assert any(a["date"] == "2026-01-16" and a["observed"] >= 80 for a in res["anomalies"])


def test_recommendations_grounded_in_numbers(sample_analysis):
    recs = sample_analysis["recommendations"]
    assert recs
    stock_item = next(
        (r for r in recs if r["category"] == "inventory"),
        None,
    )
    assert stock_item is not None
    assert "forecast" in stock_item["evidence"].lower() or "stock" in stock_item["evidence"].lower()
    assert stock_item["reason"]


def test_signals_present(sample_analysis):
    sigs = sample_analysis["signals"]
    assert sigs
    assert any(s["key"] == "forecast" for s in sigs)


def test_simulate_demand_plus_twenty(sample_analysis):
    analysis = sample_analysis
    res = run_scenario(
        analysis,
        {"type": "demand", "adjustment_pct": 20, "product": "Wireless Earbuds"},
    )
    assert res["label"].startswith("Scenario")
    inp = res["inputs"]
    out = res["outputs"]
    assert out["adjusted_forecast_units"] == round(inp["baseline_forecast_units"] * 1.2)
    assert out["coverage_days"] is not None
    assert out["stock_risk"] is True  # earbuds stock is far below projected demand
    assert inp["baseline_forecast_units"] > 0


def test_simulate_inventory_increase(sample_analysis):
    res = run_scenario(
        sample_analysis,
        {"type": "inventory", "adjustment_pct": 30, "product": None},
    )
    out = res["outputs"]
    assert out["adjusted_stock_units"] == round(996 * 1.3)
    assert out["stock_risk"] is False


def test_simulate_unknown_type(sample_analysis):
    res = run_scenario(sample_analysis, {"type": "magic", "adjustment_pct": 10})
    assert res.get("error")