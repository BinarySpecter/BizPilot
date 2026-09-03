"""Anomaly detection — deterministic, explainable.

Uses a robust rolling baseline: (value - rolling median) / (1.4826 * rolling MAD),
flagging days whose robust z-score exceeds a threshold. A reason string explains
WHAT happened and WHY it matters. Works on both the aggregate series and per-product
series.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from .schemas import DATE, PRODUCT, QUANTITY, rnd

LOOKBACK = 7
Z_THRESHOLD = 3.0
MIN_DAYS = 14
MAX_ANOMALIES = 8


def _robust_z(series: pd.Series) -> pd.DataFrame:
    vals = series
    median = vals.rolling(LOOKBACK, min_periods=LOOKBACK).median().shift(1)
    mad_raw = (
        (vals - vals.rolling(LOOKBACK, min_periods=LOOKBACK).median())
        .abs()
        .rolling(LOOKBACK, min_periods=LOOKBACK)
        .median()
        .shift(1)
    )
    mad = 1.4826 * mad_raw
    # When MAD is 0 (very stable series) use a small floor derived from the series
    # scale, otherwise real deviations would never be flagged. NaN stays NaN (leading rows).
    typical = float(mad.quantile(0.5)) if mad.notna().any() else 0.0
    floor = max(1.0, typical * 0.5)
    denom = mad.replace(0.0, floor)
    z = (vals - median) / denom
    out = pd.DataFrame({"value": vals, "expected": median, "mad": mad, "z": z})
    return out


def _series_anomalies(
    series: pd.Series, name: str = "All products"
) -> List[Dict]:
    if len(series) < MIN_DAYS:
        return []
    df = _robust_z(series)
    flags = df[df["z"].abs() >= Z_THRESHOLD]
    flags = flags[flags["expected"].notna() & flags["mad"].notna()]

    anomalies: List[Dict] = []
    for idx, row in flags.iterrows():
        direction = "up" if row["z"] > 0 else "down"
        mult = abs(float(row["value"])) / abs(float(row["expected"])) if float(row["expected"]) else None
        if mult is None or mult == 0:
            mult = abs(float(row["z"])) * 0.5 + 1 if abs(float(row["z"])) > 0 else 1.0
        anomalies.append(
            {
                "date": idx.strftime("%Y-%m-%d"),
                "product": name,
                "observed": rnd(float(row["value"]), 0),
                "expected": rnd(float(row["expected"]), 0),
                "direction": direction,
                "z_score": rnd(float(row["z"]), 2),
                "multiplier": rnd(mult, 1),
                "scale": "product" if name != "All products" else "total",
            }
        )
    anomalies.sort(key=lambda a: -abs(a.get("z_score") or 0))
    return anomalies


def detect_anomalies(sales: pd.DataFrame) -> Dict:
    """Detect anomalies on the aggregate series and per-product, dedupe, cap."""
    result: Dict = {"available": False, "reason": None, "anomalies": []}

    daily_total = sales.groupby(DATE)[QUANTITY].sum().sort_index()
    daily_total = daily_total[daily_total.index.notna()]

    if len(daily_total) < MIN_DAYS:
        result["reason"] = (
            f"Not enough daily history to detect anomalies reliably "
            f"(need at least {MIN_DAYS} days, got {len(daily_total)})."
        )
        return result

    result["available"] = True
    all_anomalies_dict: Dict[tuple, Dict] = {}

    for a in _series_anomalies(daily_total, "All products"):
        all_anomalies_dict[(a["date"], a["product"])] = a

    # per-product detection for products with enough own history
    for name, g in sales.groupby(PRODUCT):
        s = g.groupby(DATE)[QUANTITY].sum().sort_index()
        if len(s) >= MIN_DAYS:
            for a in _series_anomalies(s, name):
                # product anomaly supersedes aggregate anomaly for the same day if stronger
                key = (a["date"], a["product"])
                clip_key = (a["date"], "All products")
                if a["product"] == name:
                    existing = all_anomalies_dict.get(clip_key)
                    if existing and existing["scale"] == "total" and abs(a["z_score"] or 0) >= abs(existing["z_score"] or 0):
                        all_anomalies_dict[clip_key] = a
                        all_anomalies_dict[clip_key]["scale"] = "product"
                    elif existing is None:
                        all_anomalies_dict[clip_key] = a
                        all_anomalies_dict[clip_key]["scale"] = "product"

    anomalies = list(all_anomalies_dict.values())
    anomalies.sort(key=lambda a: -abs(a.get("z_score") or 0))
    anomalies = anomalies[:MAX_ANOMALIES]

    # attach explainers
    for a in anomalies:
        what = (
            f"{a['observed']:.0f} units sold on {a['date']}"
            if a["scale"] == "product"
            else f"{a['observed']:.0f} units sold across all products on {a['date']}"
        )
        if a["direction"] == "up":
            if a["multiplier"] and a["multiplier"] >= 1.5:
                why = (
                    f"{what} is about {a['multiplier']:.1f}x the recent baseline of "
                    f"{a['expected']:.0f} units — a demand spike worth investigating."
                )
            else:
                why = f"{what} is well above the recent baseline of {a['expected']:.0f} units."
        else:
            why = (
                f"{what} is far below the recent baseline of {a['expected']:.0f} units — "
                "a demand dip worth investigating."
            )
        a["what"] = what
        a["why"] = why

    result["anomalies"] = anomalies
    return result