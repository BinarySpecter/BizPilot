"""Canonical schema definitions for BizPilot AI.

Every uploaded dataset is normalized into this predictable shape regardless of the
column names used in the source CSV.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Canonical field names (used internally, in the API JSON, and by the UI)
# ---------------------------------------------------------------------------
DATE = "date"
PRODUCT = "product"
QUANTITY = "quantity"
REVENUE = "revenue"
STOCK = "stock"

# ---------------------------------------------------------------------------
# Accepted column aliases. Keys are canonical names, values are accepted aliases.
# Matching is case-insensitive, trims whitespace, and ignores punctuation and
# whitespace/hyphen/underscore separators (see normalize_name).
# ---------------------------------------------------------------------------
DATE_ALIASES = {
    "date",
    "date2",
    "date please",
    "datetime",
    "date time",
    "date/time",
    "date_and_time",
    "day",
    "timestamp",
    "ts",
    "created",
    "created_at",
    "created_date",
    "creation_date",
    "create_time",
    "created_time",
    "record_date",
    "recorded_on",
    "order_date",
    "ord_date",
    "order datetime",
    "order_time",
    "sale_date",
    "sold on",
    "sold_on",
    "sold at",
    "sold_at",
    "sales_date",
    "sale datetime",
    "sale time",
    "transaction_date",
    "transaction datetime",
    "trans_date",
    "trans_date",
    "invoice_date",
    "invoice datetime",
    "receipt_date",
    "recv_date",
    "ship_date",
    "shipped_on",
    "posting_date",
    "bill_date",
    "billing_date",
    "entry_date",
    "document_date",
    "purchase_date",
    "purchased_on",
    "ordered_on",
    "ordered date",
    "delivery_date",
    "delivered_on",
    "opening_date",
    "closing_date",
    "period_date",
    "fiscal_date",
    "booking_date",
    "day_of_sale",
    "sales_day",
    "order_day",
    "created on",
    "created_on",
    "ds",
    "`date`",
}
PRODUCT_ALIASES = {
    "product",
    "productname",
    "productid2",
    "item",
    "sku",
    "name",
    "itemname",
    "goods",
    "category",
    "product name",
    "item name",
    "product_item",
    "product_code",
    "productcode",
    "variant",
    "product_sku",
}
QUANTITY_ALIASES = {
    "quantity",
    "qty",
    "units",
    "unit",
    "sold",
    "quantitysold",
    "unitsold",
    "count",
    "salescount",
    "demand",
    "pcs",
    "quantity_ordered",
    "qty_ordered",
    "units_sold",
    "lineitem_quantity",
    "line_item_quantity",
    "qty_sold",
}
REVENUE_ALIASES = {
    "revenue",
    "sales",
    "amount",
    "total",
    "totalamount",
    "amount2",
    "revenueamount",
    "saleamount",
    "salestotal",
    "price",
    "gross",
    "value",
    "totalrevenue",
    "sales2",
    "sales_amount",
    "total_sales",
    "order_total",
    "order_amount",
    "total_price",
    "line_total",
    "amount_paid",
    "net_total",
    "net_sales",
    "gross_sales",
    "grand_total",
}
STOCK_ALIASES = {
    "stock",
    "inventory",
    "stockquantity",
    "inventorylevel",
    "currentstock",
    "available",
    "onhand",
    "quantityonhand",
    "qtyonhand",
    "remaining",
    "unitsinhand",
    "stock_on_hand",
    "inventory_count",
    "stock_level",
    "units_available",
    "stock_available",
    "current_quantity",
}

ALIAS_MAP = {
    DATE: DATE_ALIASES,
    PRODUCT: PRODUCT_ALIASES,
    QUANTITY: QUANTITY_ALIASES,
    REVENUE: REVENUE_ALIASES,
    STOCK: STOCK_ALIASES,
}


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


# ---------------------------------------------------------------------------
# JSON-safe serialization helpers
# ---------------------------------------------------------------------------
def jsonable(value: Any) -> Any:
    """Recursively convert numpy / pandas / datetime values to JSON-safe types."""
    if value is None:
        return None
    # numpy scalar types
    try:
        import numpy as np

        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            f = float(value)
            return f if np.isfinite(f) else None
        if isinstance(value, np.bool_):
            return bool(value)
        if isinstance(value, np.ndarray):
            return [jsonable(v) for v in value.tolist()]
    except ImportError:  # pragma: no cover - numpy is always installed
        pass
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {jsonable(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, float):
        return value if value == value else None  # NaN -> None
    if isinstance(value, int):
        return value
    return value


def rnd(value: Any, ndigits: int = 2) -> Any:
    if value is None:
        return None
    try:
        f = float(value)
        if f != f:
            return None
        return round(f, ndigits)
    except (TypeError, ValueError):
        return value


def compact_products(products: List[str], cap: int = 12) -> List[str]:
    return products[:cap]