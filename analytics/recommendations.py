"""Recommendations derived purely from computed analytics.

Every recommendation includes:
  title      action to take
  evidence   the actual computed numbers behind it
  reason     why it matters
"""

from __future__ import annotations

from typing import Dict, List


def build_recommendations(
    products: List[Dict],
    forecast_available: bool,
    forecast_total: float,
    forecast_by_product: Dict[str, Dict],
    inventory_total,
    anomalies: List[Dict],
    data_quality: Dict,
) -> List[Dict]:
    recs: List[Dict] = []

    def add(title, evidence, reason, priority, category):
        recs.append(
            {
                "title": title,
                "evidence": evidence,
                "reason": reason,
                "priority": priority,
                "category": category,
            }
        )

    # ---- Inventory risk: projected demand vs stock -------------------------
    inventory_products = [p for p in products if p.get("stock") is not None]
    if inventory_products and forecast_available:
        stock_by_name = {p["name"]: p["stock"] for p in inventory_products}
        for name, f in forecast_by_product.items():
            stock = stock_by_name.get(name)
            if stock is None or not f.get("available"):
                continue
            f7 = f.get("total") or 0
            if f7 <= 0:
                continue
            coverage_days = stock / (f7 / 7.0)
            if f7 > stock * 1.2:
                add(
                    f"Review replenishment for {name}",
                    f"7-day forecast: {f7:.0f} units | Stock: {stock:.0f} units",
                    f"Projected 7-day demand ({f7:.0f} units) exceeds available inventory "
                    f"({stock:.0f} units) — stock-out risk within the week.",
                    "high",
                    "inventory",
                )
            elif f7 > stock:
                add(
                    f"Monitor stock coverage for {name}",
                    f"7-day forecast: {f7:.0f} units | Stock: {stock:.0f} units | "
                    f"Coverage: ~{coverage_days:.1f} days",
                    "Projected demand roughly matches current stock; cover is tight "
                    "(under the 7-day window).",
                    "medium",
                    "inventory",
                )

    # ---- Demand trend changes ------------------------------------------------
    for p in products:
        chg = p.get("demand_change_pct")
        if chg is None:
            continue
        name = p["name"]
        last = p.get("units_last_14d") or 0
        prior = p.get("units_prior_14d") or 0
        if chg <= -25 and prior > 0:
            add(
                f"Review performance of {name}",
                f"Last 14d: {last:.0f} units | Prior 14d: {prior:.0f} units | "
                f"Change: {chg:.0f}%",
                f"Demand for {name} dropped {abs(chg):.0f}% versus the previous two weeks.",
                "medium",
                "product",
            )
        elif chg >= 25 and prior > 0:
            stock = p.get("stock")
            if stock is not None:
                add(
                    f"Increase supply attention for {name}",
                    f"Last 14d: {last:.0f} units | Prior 14d: {prior:.0f} units | "
                    f"Change: +{chg:.0f}% | Stock: {stock:.0f} units",
                    f"Demand for {name} rose {chg:.0f}% over two weeks; keep inventory aligned.",
                    "medium",
                    "product",
                )
            else:
                add(
                    f"Demand is rising for {name}",
                    f"Last 14d: {last:.0f} units | Prior 14d: {prior:.0f} units | Change: +{chg:.0f}%",
                    "Sustained growth in demand; consider supply planning.",
                    "low",
                    "signal",
                )

    # ---- Anomaly investigations ---------------------------------------------
    for a in anomalies[:2]:
        add(
            f"Investigate unusual activity on {a['date']}",
            f"Observed: {a['observed']:.0f} units | Baseline: {a['expected']:.0f} units | "
            f"{'High' if a['direction'] == 'up' else 'Low'} anomaly",
            a.get("why", "An unusual sales day was detected by the analytics engine."),
            "medium",
            "anomaly",
        )

    # ---- Data quality --------------------------------------------------------
    dropped_pct = (data_quality or {}).get("dropped_pct") or 0
    if dropped_pct > 5:
        add(
            "Review source data quality",
            f"{dropped_pct:.1f}% of rows were dropped during cleaning "
            f"({(data_quality or {}).get('dropped_rows', 0)} rows)",
            "A material share of the file could not be parsed; results are based on the "
            "remaining clean rows.",
            "low",
            "data",
        )

    order = {"high": 0, "medium": 1, "low": 2}
    recs.sort(key=lambda r: (order.get(r["priority"], 9), r["title"]))
    return recs[:6]