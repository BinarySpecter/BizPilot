"""Tests for CSV parsing, column normalization, and validation."""

import io

import pytest

from analytics.cleaning import (
    ValidationError,
    detect_kind,
    load_dataset,
    parse_csv,
    resolve_column,
)


def test_alias_resolution():
    cols = ["Order Date", "Product Name", "Qty", "Sales $", "INVENTORY"]
    assert resolve_column(cols, "date") == "Order Date"
    assert resolve_column(cols, "product") == "Product Name"
    assert resolve_column(cols, "quantity") == "Qty"
    assert resolve_column(cols, "revenue") == "Sales $"
    assert resolve_column(cols, "stock") == "INVENTORY"


def test_detect_kind():
    assert detect_kind(["date", "product", "quantity", "revenue"]) == "sales"
    assert detect_kind(["date", "product", "stock"]) == "inventory"
    assert detect_kind(["date", "product", "stock", "qty"]) == "sales"


SALES_CSV = """\
Date,Product,Units,Amount
2026-01-01,A,10,100.0
2026-01-02,A,12,120.0
2026-01-08,A,11,110.0
2026-01-09,A,9,90.0
"""


def test_parse_and_normalize():
    ds = load_dataset(SALES_CSV.encode(), "sales.csv")
    sales = ds["sales"]
    assert list(sales.columns) == ["date", "product", "quantity", "revenue"]
    assert len(sales) == 4
    assert sales["date"].is_monotonic_increasing
    assert sales["quantity"].sum() == pytest.approx(42)


def test_tolerates_bad_rows():
    bad = """\
date,product,quantity,revenue
2026-01-01,A,10,100
not-a-date,B,10,100
2026-01-02,A,abc,100
2026-01-03,A,10,xyz
2026-01-04,A,10,100
2026-01-05,A,10,100
"""
    ds = load_dataset(bad.encode(), "bad.csv")
    sales = ds["sales"]
    # bad date dropped; bad-quantity row kept as revenue-only; bad-revenue value tolerated
    assert len(sales) == 5
    q = ds["quality"]
    assert q["bad_dates"] >= 1
    assert q["bad_quantity"] >= 1
    assert q["bad_revenue"] >= 1


def test_empty_file_rejected():
    with pytest.raises(ValidationError) as e:
        parse_csv(b"", "empty.csv")
    assert e.value.code == "empty_file"


def test_missing_date_column_rejected():
    with pytest.raises(ValidationError) as e:
        load_dataset(b"product,quantity\nA,10\n", "n.csv")
    assert e.value.code == "missing_date"


def test_unrecognizable_file_rejected():
    with pytest.raises(ValidationError):
        load_dataset(b"hello world\nnothing here\n", "garbage.csv")


def test_inventory_parsing():
    inv = """\
date,product,stock
2026-01-01,A,50
2026-01-02,A,40
2026-01-01,B,200
"""
    ds = load_dataset(SALES_CSV.encode(), "sales.csv", inv.encode(), "inv.csv")
    assert ds["inventory"] is not None
    assert len(ds["inventory"]) == 3
    assert ds["quality"]["has_inventory"] is True


def test_quantity_only_csv():
    csv = "date,product,units\n2026-01-01,A,5\n2026-01-02,B,7\n"
    ds = load_dataset(csv.encode(), "q.csv")
    sales = ds["sales"]
    assert sales["quantity"].sum() == pytest.approx(12)
    assert sales["revenue"].isna().all()


def test_sort_chronological_after_duplicates():
    csv = "date,product,quantity,revenue\n2026-01-03,A,3,30\n2026-01-01,A,1,10\n2026-01-02,A,2,20\n"
    ds = load_dataset(csv.encode(), "s.csv")
    dates = ds["sales"]["date"].dt.date.tolist()
    assert dates == sorted(dates)