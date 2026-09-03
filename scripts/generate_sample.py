"""Generate the demo datasets for BizPilot AI.

Creates data/sample/sales.csv (90 days, 4 products) and data/sample/inventory.csv.
The data tells a coherent story:
  - Wireless Earbuds: rising demand, thin inventory  -> stock-out risk
  - Phone Cases / Charging Cables: stable baseline
  - Bluetooth Speakers: a promo spike anomaly mid-series

Rerun anytime:  python3 scripts/generate_sample.py
"""

from __future__ import annotations

import csv
import os
from datetime import date, timedelta

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_DIR = os.path.join(ROOT, "data", "sample")

DAYS = 90
END = date(2026, 8, 31)
START = END - timedelta(days=DAYS - 1)

rng = np.random.default_rng(seed=42)

# name: (base, slope_per_day, amp(promo spike day offset), promo_amount, price)
PRODUCTS = {
    "Wireless Earbuds": dict(base=18.0, slope=0.09, spike_day=88, spike=0, price=29.99),
    "Phone Cases": dict(base=30.0, slope=0.0, spike_day=None, spike=0, price=14.99),
    "Charging Cables": dict(base=40.0, slope=-0.02, spike_day=None, spike=0, price=9.99),
    "Bluetooth Speakers": dict(base=8.0, slope=-0.02, spike_day=75, spike=38.0, price=49.99),
}


def weekday_factor(d: date, strength: float = 0.14) -> float:
    """Weekend demand bump (Fri/Sat/Sun) so weekly seasonality exists."""
    wd = d.weekday()
    if wd >= 4:
        return 1.0 + strength
    return 1.0 - strength * 0.5


def main() -> None:
    os.makedirs(SAMPLE_DIR, exist_ok=True)

    sales_path = os.path.join(SAMPLE_DIR, "sales.csv")
    with open(sales_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "product", "quantity", "revenue"])
        for i in range(DAYS):
            d = START + timedelta(days=i)
            for name, cfg in PRODUCTS.items():
                noise = rng.lognormal(0.0, 0.10)
                qty = cfg["base"] + cfg["slope"] * i
                if cfg["spike_day"] == i:
                    qty += cfg["spike"]
                qty *= weekday_factor(d)
                qty *= noise
                qty = max(1, round(qty))
                rev = round(qty * cfg["price"], 2)
                writer.writerow([d.isoformat(), name, qty, rev])
    print(f"[gen] wrote {sales_path} ({DAYS * len(PRODUCTS)} rows)")

    inv_path = os.path.join(SAMPLE_DIR, "inventory.csv")
    stocks = {
        "Wireless Earbuds": 46,   # thin -> stock-out risk under forecast
        "Phone Cases": 320,
        "Charging Cables": 500,
        "Bluetooth Speakers": 130,
    }
    with open(inv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "product", "stock"])
        # 14 days of stock snapshots per product
        for i in range(14):
            d = END - timedelta(days=13 - i)
            for name, level in stocks.items():
                jitter = int(rng.normal(0, 1.5))
                writer.writerow([d.isoformat(), name, max(1, level + jitter)])
    print(f"[gen] wrote {inv_path} ({14 * len(stocks)} rows)")


if __name__ == "__main__":
    main()