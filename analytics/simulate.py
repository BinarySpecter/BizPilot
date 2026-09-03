"""What-if simulation — real recalculation over computed analytics.

Given the already-computed analysis JSON and a scenario definition
(demand or inventory adjustment), recompute inventory coverage and stock risk.
Always labeled as a scenario, never a prediction.
"""

from __future__ import annotations

from typing import Dict, List

from .schemas import rnd


def _products_lookup(analysis: Dict) -> Dict[str, Dict]:
    return {p.get("name"): p for p in analysis.get("products", []) if p.get("name")}


def _baseline_forecast(analysis: Dict, product_name: str | None) -> float:
    per_product = analysis.get("forecast", {}).get("by_product", {})
    if product_name and product_name in per_product:
        return float(per_product[product_name].get("total") or 0)
    if not product_name:
        total = analysis.get("forecast", {}).get("total")
        if total is not None:
            return float(total)
    return 0.0


def _stock_for(analysis: Dict, product_name: str | None) -> float:
    products = _products_lookup(analysis)
    if product_name and product_name in products:
        return float(products[product_name].get("stock") or 0)
    inv = analysis.get("inventory", {})
    if inv.get("available"):
        if product_name:
            for p in inv.get("products", []):
                if p.get("name") == product_name:
                    return float(p.get("stock") or 0)
        else:
            return float(inv.get("total_stock") or 0)
    return 0.0


def run_scenario(analysis: Dict, scenario: Dict) -> Dict:
    scenario_type = scenario.get("type")  # "demand" | "inventory"
    adjustment_pct = float(scenario.get("adjustment_pct") or 0) / 100.0
    product_name = scenario.get("product") or None

    result: Dict = {
        "label": "Scenario — not a prediction",
        "type": scenario_type,
        "adjustment_pct": round(adjustment_pct * 100, 1),
        "product": product_name,
        "inputs": {
            "baseline_forecast_units": rnd(_baseline_forecast(analysis, product_name), 0),
            "current_stock_units": rnd(_stock_for(analysis, product_name), 0),
        },
    }

    base_fc = result["inputs"]["baseline_forecast_units"] or 0
    stock = result["inputs"]["current_stock_units"] or 0

    if scenario_type == "demand":
        adjusted = base_fc * (1 + adjustment_pct)
        result["outputs"] = {
            "adjusted_forecast_units": rnd(adjusted, 0),
            "forecast_change_units": rnd(adjusted - base_fc, 0),
        }
    elif scenario_type == "inventory":
        adjusted_stock = stock * (1 + adjustment_pct)
        result["outputs"] = {
            "adjusted_stock_units": rnd(adjusted_stock, 0),
            "stock_change_units": rnd(adjusted_stock - stock, 0),
        }
    else:
        return {
            "label": "Scenario — not a prediction",
            "error": f"Unknown scenario type '{scenario_type}'. Use 'demand' or 'inventory'.",
        }

    # coverage recalculation under the scenario
    if adjusted := (result["outputs"].get("adjusted_forecast_units")):
        result["outputs"]["coverage_days"] = rnd(stock / (adjusted / 7.0), 1)
        result["outputs"]["stock_risk"] = bool(stock < adjusted)
        result["outputs"]["stock_gap_units"] = rnd(max(0.0, adjusted - stock), 0)
        if stock and base_fc:
            result["outputs"]["baseline_coverage_days"] = rnd(stock / (base_fc / 7.0), 1)

    if scenario_type == "inventory":
        adj_stock = result["outputs"]["adjusted_stock_units"]
        result["outputs"]["coverage_days"] = rnd(adj_stock / (base_fc / 7.0), 1) if base_fc else None
        result["outputs"]["stock_risk"] = bool(adj_stock < base_fc)
        result["outputs"]["stock_gap_units"] = rnd(max(0.0, base_fc - adj_stock), 0)
        if stock and base_fc:
            result["outputs"]["baseline_coverage_days"] = rnd(stock / (base_fc / 7.0), 1)

    if result["outputs"].get("coverage_days") is not None and result["outputs"]["coverage_days"] < 7:
        result["outputs"]["alert"] = (
            "Stock would cover under 7 days of projected demand under this scenario."
        )

    return result


def scenario_products(analysis: Dict) -> List[Dict]:
    """Valid product targets + the overall (None) option available for simulation."""
    products = analysis.get("products", [])
    options = [{"name": "All products", "value": ""}]
    for p in products:
        options.append({"name": p["name"], "value": p["name"]})
    return options