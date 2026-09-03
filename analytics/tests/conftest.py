"""Shared fixtures for analytics tests."""

import pandas as pd
import pytest

SAMPLE_SALES = "data/sample/sales.csv"
SAMPLE_INVENTORY = "data/sample/inventory.csv"


@pytest.fixture(scope="session")
def sample_analysis():
    from analytics.engine import analyze, to_response

    with open(SAMPLE_SALES, "rb") as f:
        sales = f.read()
    with open(SAMPLE_INVENTORY, "rb") as f:
        inv = f.read()
    return to_response(analyze(sales, "sales.csv", inv, "inv.csv"))


def make_sales_df(days=30, n_products=1, seed=1, base=20.0, spike_at=None, spike=40.0):
    rng = __import__("numpy").random.default_rng(seed)
    import pandas as _pd

    rows = []
    start = _pd.Timestamp("2026-01-01")
    for i in range(days):
        d = start + _pd.Timedelta(days=i)
        for p in range(n_products):
            qty = base + int(rng.normal(0, 2))
            if spike_at == i:
                qty = spike
            rows.append(
                {"date": d.date().isoformat(), "product": f"P{p + 1}", "quantity": qty, "revenue": qty * 10.0}
            )
    return _pd.DataFrame(rows)