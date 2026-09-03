"""KPI and trend computation. Only actual computed values live here — no AI, no invention."""

from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

from .schemas import DATE, PRODUCT, QUANTITY, REVENUE, STOCK, jsonable, rnd


def compute_metrics(sales: pd.DataFrame, inventory: Optional[pd.DataFrame]) -> Dict:
    result: Dict = {}

    # --------------------------- KPIs -------------------------------------
    has_revenue = bool(sales[REVENUE].notna().any())
    has_qty = bool(sales[QUANTITY].notna().any())

    kpis: Dict = {}
    if has_revenue:
        total_revenue = float(sales[REVENUE].sum())
        rev_rows = int(sales[REVENUE].notna().sum())
        kpis["total_revenue"] = rnd(total_revenue)
        kpis["revenue_rows"] = rev_rows
        kpis["avg_record_revenue"] = rnd(total_revenue / rev_rows) if rev_rows else None
    else:
        kpis["total_revenue"] = None
        kpis["revenue_rows"] = 0
        kpis["avg_record_revenue"] = None

    if has_qty:
        kpis["total_units"] = rnd(float(sales[QUANTITY].sum()), 0)
    else:
        kpis["total_units"] = None

    # recent periods
    date_max = sales[DATE].max()
    days = 7
    recent7 = sales[sales[DATE] > date_max - pd.Timedelta(days=days)]
    recent30 = sales[sales[DATE] > date_max - pd.Timedelta(days=30)]
    kpis["recent_7d_revenue"] = (
        rnd(float(recent7[REVENUE].sum())) if has_revenue else None
    )
    kpis["recent_7d_units"] = rnd(float(recent7[QUANTITY].sum()), 0) if has_qty else None
    kpis["recent_30d_revenue"] = (
        rnd(float(recent30[REVENUE].sum())) if has_revenue else None
    )
    kpis["recent_30d_units"] = rnd(float(recent30[QUANTITY].sum()), 0) if has_qty else None

    kpis["days_covered"] = int((sales[DATE].max() - sales[DATE].min()).days) + 1
    kpis["date_range"] = {
        "min": sales[DATE].min().strftime("%Y-%m-%d"),
        "max": sales[DATE].max().strftime("%Y-%m-%d"),
    }
    result["kpis"] = kpis

    # ------------------------- Top products --------------------------------
    products: List[Dict] = []
    if has_qty or has_revenue:
        grp = sales.groupby(PRODUCT)
        for name, g in grp:
            row: Dict = {"name": name, "rows": int(len(g))}
            if has_revenue:
                rev = float(g[REVENUE].sum())
                row["revenue"] = rnd(rev)
            else:
                row["revenue"] = None
            if has_qty:
                units = float(g[QUANTITY].sum())
                row["units"] = rnd(units, 0)
            else:
                row["units"] = None

            # last 14d vs prior 14d
            dmax = g[DATE].max()
            last14 = g[g[DATE] > dmax - pd.Timedelta(days=14)]
            prior14 = g[
                (g[DATE] <= dmax - pd.Timedelta(days=14))
                & (g[DATE] > dmax - pd.Timedelta(days=28))
            ]
            if has_qty and len(last14) and len(prior14):
                l = float(last14[QUANTITY].sum())
                p = float(prior14[QUANTITY].sum())
                row["units_last_14d"] = rnd(l, 0)
                row["units_prior_14d"] = rnd(p, 0)
                row["demand_change_pct"] = rnd(100.0 * (l - p) / p) if p > 0 else None
            else:
                row["units_last_14d"] = rnd(float(last14[QUANTITY].sum()), 0) if has_qty else None
                row["units_prior_14d"] = None
                row["demand_change_pct"] = None

            # recent 7d
            last7 = g[g[DATE] > dmax - pd.Timedelta(days=7)]
            row["units_7d"] = rnd(float(last7[QUANTITY].sum()), 0) if has_qty else None
            row["revenue_7d"] = rnd(float(last7[REVENUE].sum())) if has_revenue else None

            # forecast share placeholder (filled by forecasting stage)
            row["forecast_7d"] = None
            row["coverage_days"] = None
            row["stock"] = None
            products.append(row)
        total = sum(r["revenue"] or 0 for r in products)
        total_units_all = sum(r["units"] or 0 for r in products)
        for r in products:
            r["revenue_share_pct"] = rnd(100.0 * (r["revenue"] or 0) / total) if total else None
            r["units_share_pct"] = rnd(100.0 * (r["units"] or 0) / total_units_all) if total_units_all else None
        products.sort(key=lambda r: (r["units"] if r["units"] is not None else -1), reverse=True)
        result["products"] = products

    # --------------------------- Trends -----------------------------------
    daily = sales.groupby(sales[DATE].dt.date).agg(
        demand=(QUANTITY, "sum"), revenue=(REVENUE, "sum")
    ).sort_index()
    daily_rows = []
    for d, row in daily.iterrows():
        item = {"date": d.isoformat()}
        item["demand"] = rnd(float(row["demand"]), 0) if pd.notna(row["demand"]) else None
        item["revenue"] = rnd(float(row["revenue"])) if pd.notna(row["revenue"]) else None
        daily_rows.append(item)

    result["daily"] = daily_rows

    # weekly aggregation
    wk = sales.copy()
    wk["week"] = wk[DATE].dt.isocalendar().week.astype(int)
    wk["year"] = wk[DATE].dt.isocalendar().year.astype(int)
    weekly = wk.groupby(["year", "week"]).agg(
        demand=(QUANTITY, "sum"), revenue=(REVENUE, "sum")
    ).reset_index()
    weekly_rows = []
    for _, row in weekly.iterrows():
        weekly_rows.append(
            {
                "week": f"{int(row['year'])}-W{int(row['week']):02d}",
                "demand": rnd(float(row["demand"]), 0),
                "revenue": rnd(float(row["revenue"])),
            }
        )
    result["weekly"] = weekly_rows

    # ------------------------- Inventory ---------------------------------
    inv_status: Dict = {"available": False, "products": []}
    if inventory is not None and len(inventory):
        latest = inventory.sort_values(DATE)
        latest_by_prod = latest.groupby(PRODUCT).tail(1)
        total_stock = float(latest_by_prod[STOCK].sum())
        inv_status["available"] = True
        inv_status["total_stock"] = rnd(total_stock, 0)
        inv_status["as_of"] = latest[DATE].max().isoformat()
        for _, row in latest_by_prod.iterrows():
            inv_status["products"].append(
                {"name": row[PRODUCT], "stock": rnd(float(row[STOCK]), 0)}
            )
    result["inventory"] = inv_status

    return result


def attach_inventory_to_products(products: List[Dict], inventory: pd.DataFrame | None) -> None:
    """Merge current stock into the products table (stock level, coverage later)."""
    if inventory is None or not len(inventory):
        return
    latest = inventory.sort_values(DATE).groupby(PRODUCT).tail(1)
    stock_by_name = dict(zip(latest[PRODUCT], latest[STOCK]))
    for p in products:
        stock = stock_by_name.get(p["name"])
        if stock is not None:
            p["stock"] = rnd(float(stock), 0)


def compute_signals(
    kpis: Dict,
    products: List[Dict],
    forecast_total: float,
    forecast_available: bool,
    inventory_total: Optional[float],
    anomalies: List[Dict],
    has_qty: bool,
) -> List[Dict]:
    signals: List[Dict] = []

    # overall demand direction (sum of last14 vs prior14 across products)
    if products:
        last = sum(p.get("units_last_14d") or 0 for p in products)
        prior = sum(p.get("units_prior_14d") or 0 for p in products)
        if prior and has_qty:
            chg = 100.0 * (last - prior) / prior
            dirn = "up" if chg > 5 else ("down" if chg < -5 else "flat")
            signals.append(
                {
                    "key": "overall_demand_trend",
                    "label": "Overall demand",
                    "phrase": f"{'Rising' if dirn == 'up' else 'Falling' if dirn == 'down' else 'Flat'} over last 14 days",
                    "direction": dirn,
                    "change_pct": rnd(chg),
                    "period": "last 14 days vs prior 14 days",
                }
            )

    # revenue trend
    if kpis.get("recent_30d_revenue") and kpis.get("recent_7d_revenue"):
        pass  # skip absolute compare; direction covered by demand signal

    # forecast pressure
    if forecast_available:
        signal = {
            "key": "forecast",
            "label": "Next 7 day demand",
            "phrase": f"Forecast ~{rnd(forecast_total, 0)} units",
            "direction": "flat",
            "change_pct": None,
            "period": "next 7 days",
            "value_units": rnd(forecast_total, 0),
        }
        if inventory_total is not None and inventory_total > 0:
            coverage = forecast_total / inventory_total
            if coverage > 1:
                signal["phrase"] = (
                    f"Projected demand ({rnd(forecast_total,0)} units) exceeds current "
                    f"stock ({rnd(inventory_total,0)} units)"
                )
                signal["direction"] = "up"
            else:
                signal["phrase"] = (
                    f"Projected demand ({rnd(forecast_total,0)} units) within current "
                    f"stock ({rnd(inventory_total,0)} units)"
                )
        signals.append(signal)
        signals.append(
            {
                "key": "stock_coverage",
                "label": "Stock coverage window",
                "phrase": (
                    f"Stock covers ~{rnd(inventory_total / (forecast_total / 7.0), 1)} days of "
                    f"projected demand"
                    if inventory_total and forecast_available and forecast_total > 0
                    else "Insufficient stock data to estimate coverage"
                ),
                "direction": "flat",
                "change_pct": None,
                "period": "based on forecast",
            }
        )

    # anomalies
    if anomalies:
        signals.append(
            {
                "key": "anomalies",
                "label": "Anomaly alerts",
                "phrase": f"{len(anomalies)} unusual pattern(s) detected",
                "direction": "flat",
                "change_pct": None,
                "period": "recent",
            }
        )
    if not signals:
        signals.append(
            {
                "key": "none",
                "label": "No signals",
                "phrase": "Not enough data to derive signals.",
                "direction": "flat",
            }
        )
    return signals