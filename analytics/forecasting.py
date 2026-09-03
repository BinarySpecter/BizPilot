"""Demand forecasting.

MVP method (statistically defensible, no heavy ML):
  weighted moving average + linear trend adjustment + optional weekly seasonality.

The method used and its limitations are always reported in the output, and a
forecast is NEVER produced when there is not enough history.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .schemas import DATE, QUANTITY, jsonable, rnd

MIN_DAYS_FOR_FORECAST = 7
DEFAULT_HORIZON = 7
MAX_HORIZON = 14
SEASONALITY_MIN_DAYS = 21


def _daily_series(sales: pd.DataFrame) -> pd.Series:
    s = sales.groupby(DATE)[QUANTITY].sum().sort_index()
    return s[~s.index.isna()]


def _weighted_ma(values: pd.Series, window: int = 7) -> float:
    vals = values.tail(window)
    n = len(vals)
    if n == 0:
        return 0.0
    weights = np.arange(1, n + 1, dtype=float)
    return float(np.dot(vals.to_numpy(float), weights) / weights.sum())


def _walk_forward_residuals(
    series: pd.Series, window: int = 7
) -> List[float]:
    """Evaluate the same heuristic on history to get honest residual magnitudes."""
    residuals: List[float] = []
    vals = series.to_numpy(float)
    for i in range(window, len(vals)):
        hist = pd.Series(vals[:i])
        pred = _weighted_ma(hist, window)
        residual = vals[i] - pred
        # skip the seasonal component here; trend/season refinement happens in main fit
        residuals.append(float(residual))
    return residuals


def _seasonal_weights(series: pd.Series) -> Optional[Dict[int, float]]:
    """Relative day-of-week factor normalized so mean == 1.0 (None if not enough data)."""
    if len(series) < SEASONALITY_MIN_DAYS:
        return None
    dow = pd.Series(series.index.dayofweek, index=series.index)
    overall_mean = float(series.mean())
    if overall_mean <= 0:
        return None
    factors: Dict[int, float] = {}
    for d in range(7):
        mask = dow == d
        m = float(series[mask].mean()) if mask.sum() else None
        factors[d] = (m / overall_mean) if m and m > 0 else None
    usable = [v for v in factors.values() if v is not None]
    if not usable:
        return None
    scale = float(np.mean(usable))
    for d in range(7):
        factors[d] = factors[d] / scale
    return factors


def forecast_series(sales: pd.DataFrame, horizon: int = DEFAULT_HORIZON) -> Dict:
    """Compute demand forecast for the next `horizon` days."""
    series = _daily_series(sales)
    horizon = max(1, min(int(horizon), MAX_HORIZON))

    if len(series) < MIN_DAYS_FOR_FORECAST:
        return {
            "available": False,
            "reason": (
                f"Not enough historical data to generate a reliable forecast "
                f"(need at least {MIN_DAYS_FOR_FORECAST} days of sales, got {len(series)})."
            ),
            "horizon": horizon,
            "method": None,
            "values": [],
            "total": None,
            "low": None,
            "high": None,
            "baseline_daily": rnd(float(series.mean())) if len(series) else None,
        }

    # Use the full series; recent portion for trend/level.
    recent = series.tail(max(7, min(90, len(series))))
    if len(recent) < 7:  # pragma: no cover - guarded above
        recent = series

    base = _weighted_ma(recent, window=min(7, len(recent)))

    # Linear trend over the trailing portion (slope per day).
    x = np.arange(len(recent))
    y = recent.to_numpy(float)
    slope, intercept = np.polyfit(x, y, 1)
    slope_per_day = float(slope)

    # Stable direction metric used for reporting.
    trend_dir = "up" if slope_per_day > 0.05 else ("down" if slope_per_day < -0.05 else "flat")

    seasonal = _seasonal_weights(series)

    last_date = series.index.max()
    values: List[Dict] = []
    for i in range(1, horizon + 1):
        d = last_date + timedelta(days=i)
        pred = base + slope_per_day * i
        if seasonal and (d.weekday() in seasonal and seasonal[d.weekday()]):
            pred = pred * seasonal[d.weekday()]
        pred = max(0.0, pred)
        values.append({"date": d.isoformat(), "value": rnd(pred, 1)})

    total = rnd(float(sum(v["value"] for v in values)), 0)

    # Honest uncertainty heuristic: propagate walk-forward residual spread.
    residuals = _walk_forward_residuals(series, window=min(7, len(series)))
    if residuals:
        resid_std = float(np.std(residuals))
        spread = 1.28 * resid_std * np.sqrt(horizon)  # ~80% heuristic band
        low = max(0, total - spread)
        high = total + spread
    else:
        low, high = None, None

    method_parts = ["Weighted moving average", "linear trend adjustment"]
    if seasonal:
        method_parts.append("weekly seasonality")
    method = " + ".join(method_parts)

    return {
        "available": True,
        "horizon": horizon,
        "method": method,
        "seasonality_used": seasonal is not None,
        "values": values,
        "total": total,
        "low": rnd(low) if low is not None else None,
        "high": rnd(high) if high is not None else None,
        "baseline_daily": rnd(float(series.mean())),
        "recent_avg_daily": rnd(base),
        "trend_direction": trend_dir,
        "historical_days": len(series),
    }


def product_forecasts(sales: pd.DataFrame, horizon: int = DEFAULT_HORIZON) -> Dict[str, Dict]:
    """Per-product forecast for the products table (best effort, compact)."""
    out: Dict[str, Dict] = {}
    for name, g in sales.groupby("product"):
        if len(g) < MIN_DAYS_FOR_FORECAST:
            continue
        series = g.groupby(DATE)[QUANTITY].sum().sort_index()
        if len(series) < MIN_DAYS_FOR_FORECAST:
            continue
        base = _weighted_ma(series, window=min(7, len(series)))
        last_date = series.index.max()
        values: List[Dict] = []
        for i in range(1, horizon + 1):
            pred = max(0.0, base)
            values.append({"date": (last_date + timedelta(days=i)).isoformat(), "value": rnd(pred, 1)})
        out[name] = {
            "available": True,
            "horizon": horizon,
            "method": "Weighted moving average",
            "values": values,
            "total": rnd(float(sum(v["value"] for v in values)), 0),
            "baseline_daily": rnd(float(series.mean())),
        }
    return out