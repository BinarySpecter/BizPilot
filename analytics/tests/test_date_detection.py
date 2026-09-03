"""Regression tests for date-column detection and CSV ingestion robustness.

Covers the reported bug: realistic CSVs whose date column is not literally the
alias 'date' being rejected with "No date column found".
"""

import pytest

from analytics.cleaning import (
    ValidationError,
    detect_date_column_by_content,
    detect_kind,
    load_dataset,
    resolve_column,
)

BODY = "\n".join(
    f"2026-0{i},Wireless Earbuds,{10+i},{round((10+i) * 29.99, 2)}"
    for i in range(1, 9)
)


@pytest.mark.parametrize(
    "header",
    [
        "date",
        "Date",
        "DATE",
        "  Date  ",  # surrounding whitespace
        "order_date",
        "order date",
        "sale_date",
        "sale date",
        "transaction_date",
        "transaction date",
        "invoice_date",
        "invoice date",
        "receipt date",
        "posting date",
        "bill date",
        "datetime",
        "date/time",
        "timestamp",
        "created_at",
        "created on",
        "sold on",
    ],
)
def test_common_date_column_headers_accepted(header):
    csv = f"{header},product,quantity,revenue\n" + BODY + "\n"
    ds = load_dataset(csv.encode(), "t.csv")
    sales = ds["sales"]
    assert len(sales) == 8
    assert list(sales.columns) == ["date", "product", "quantity", "revenue"]
    # the detected column name is reported back
    assert ds["quality"]["date_column"] == header


def test_detected_column_is_reported_for_sample():
    with open("data/sample/sales.csv", "rb") as f:
        ds = load_dataset(f.read(), "sales.csv")
    assert ds["quality"]["date_column"] == "date"
    assert len(ds["sales"]) > 0


@pytest.mark.parametrize(
    "csv",
    [
        # timestamp-style value (date + time)
        "When,product,quantity,revenue\n2026-01-01 08:00:00,A,10,100\n2026-01-02 09:30:00,A,12,120\n",

        # content-based detection with a totally un-standard header name
        "Datum,product,quantity,revenue\n2026-01-01,A,10,100\n2026-01-02,A,12,120\n"

        # month-name dates, unknown header
        "Fyrir,product,quantity,revenue\nJan 15, 2026,A,10,100\nFeb 20, 2026,A,12,120\n",
    ],
)
def test_content_based_date_detection(csv):
    ds = load_dataset(csv.encode(), "t.csv")
    assert len(ds["sales"]) == 2


def test_content_detection_finds_real_date_not_row_numbers():
    df = __import__("pandas").read_csv(
        __import__("io").StringIO(
            "n,date,product,quantity,revenue\n"
            "1,2026-01-01,A,10,100\n"
            "2,2026-01-02,A,12,120\n"
            "3,2026-01-03,A,11,110\n"
        )
    )
    assert detect_date_column_by_content(df) == "date"


def test_no_false_positive_on_numeric_columns():
    # quantities happen to look like years (2000, 2001, ...) but carry no date
    # separator — they must NOT be detected as a date column, so the file is
    # (correctly) rejected as having no usable date field.
    csv = "name,units\nWidget,2000\nWidget,2001\nWidget,2002\nWidget,2003\n"
    with pytest.raises(ValidationError) as e:
        load_dataset(csv.encode(), "t.csv")
    assert e.value.code == "missing_date"


def test_no_date_field_raises_helpful_error():
    with pytest.raises(ValidationError) as e:
        load_dataset(b"product,quantity\nA,10\n", "n.csv")
    assert e.value.code == "missing_date"
    assert "Detected columns" in e.value.message
    assert "'product'" in e.value.message
    assert "'date'" in e.value.message  # schema hint present
    assert "revenue" in e.value.message


def test_unparseable_dates_raises_clear_error():
    csv = "date,product,quantity,revenue\nsoon,A,10,100\nlater,A,12,120\nwhenever,A,11,110\n"
    with pytest.raises(ValidationError) as e:
        load_dataset(csv.encode(), "bad_dates.csv")
    assert e.value.code == "unparseable_dates"
    assert "could be parsed as dates" in e.value.message
    assert "'date'" in e.value.message


def test_partially_bad_dates_are_dropped_not_fatal():
    csv = (
        "date,product,quantity,revenue\n"
        "2026-01-01,A,10,100\n"
        "not-a-date,A,12,120\n"
        "2026-01-03,A,11,110\n"
    )
    ds = load_dataset(csv.encode(), "mixed.csv")
    assert len(ds["sales"]) == 2
    assert ds["quality"]["bad_dates"] == 1


def test_inventory_with_unstandard_date_header():
    inv = "As of,product,stock\n2026-01-01,A,50\n2026-01-02,A,40\n"
    sales = "sale date,product,quantity,revenue\n2026-01-01,A,10,100\n"
    ds = load_dataset(sales.encode(), "s.csv", inv.encode(), "i.csv")
    assert ds["quality"]["has_inventory"] is True
    assert ds["inventory"] is not None


def test_detect_kind_uses_content_fallback():
    df = __import__("pandas").read_csv(
        __import__("io").StringIO(
            "As of,product,stock\n2026-01-01,A,50\n2026-01-02,A,40\n"
        )
    )
    assert detect_kind(df.columns.tolist(), df) == "inventory"


def test_resolve_column_is_deterministic_specific_first():
    cols = ["Date", "Order Date"]
    # order_date (more specific) wins deterministically
    assert resolve_column(cols, "date") == "Order Date"