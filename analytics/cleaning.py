"""CSV parsing, column normalization and data validation.

Guarantees about the output of this module:
  * Every returned sales/inventory table has canonical columns:
      sales:      date, product, quantity, revenue
      inventory:  date, product, stock
  * `date` is a normalized datetime64[ns] (midnight).
  * Invalid / unparseable rows are dropped and *counted*, never fatal.
  * If the data cannot be processed at all, a ValidationError is raised with a
    human-readable message the UI can show.
"""

from __future__ import annotations

import io
import re
from typing import Dict, List, Optional

import pandas as pd

from .schemas import (
    ALIAS_MAP,
    DATE,
    PRODUCT,
    QUANTITY,
    REVENUE,
    STOCK,
    normalize_name,
)


class ValidationError(Exception):
    def __init__(self, message: str, code: str = "invalid_data"):
        super().__init__(message)
        self.message = message
        self.code = code


# Names that hint a column is a date, used as a deterministic preference
# when content-based detection finds several candidates.
_DATE_HINT = re.compile(r"date|day|time|created|order|sale|invoic|receipt|trans|ship|post|bill|timestamp", re.I)
_MONTH_WORDS = frozenset(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec"]
)
_YEAR_RE = re.compile(r"(19|20)\d\d")
_DATE_DELIM = re.compile(r"[-/]|^\d{1,2}[ .]|[a-z]{3,9}\.?\s+\d{1,2}|[a-z]{3,9}[-/]", re.I)


def resolve_column(columns: List[str], canonical: str) -> Optional[str]:
    """Find the actual CSV column matching a canonical name, or None.

    Deterministic and normalization-insensitive (case, spacing, hyphens,
    underscores and surrounding punctuation are all ignored). When several
    aliases would match, the most specific one (longest normalized token)
    wins — e.g. ``order_date`` is preferred over ``date``.
    """
    if len(columns) == 0:
        return None
    norm_set = {normalize_name(c): c for c in columns}
    aliases = {normalize_name(a) for a in ALIAS_MAP[canonical]}
    for key in sorted(aliases, key=lambda k: (-len(k), k)):
        if key in norm_set:
            return norm_set[key]
    return None


def _has_date_delimiters(values: pd.Series) -> bool:
    """True if any sampled value *looks* like a date token (has a date
    separator and/or a month word / 4-digit year). Guards against treating
    plain numbers (row ids, quantities) as dates."""
    for v in values.head(25):
        t = str(v).strip()
        if not t:
            continue
        if _DATE_DELIM.search(t):
            return True
        if any(w in _MONTH_WORDS for w in re.split(r"[^a-z]+", t.lower())):
            return True
    return False


def detect_date_column_by_content(df: pd.DataFrame, sample_size: int = 100) -> Optional[str]:
    """Safely detect a date column by *data content* when the header name is
    not a known alias. Conservative guards prevent false positives (row
    indexes, bare years, quantities)."""
    candidates: List[tuple] = []
    for col in df.columns:
        s = df[col].dropna().astype(str).str.strip()
        s = s[s.ne("")]
        if s.empty:
            continue
        if not _has_date_delimiters(s.head(100)):
            continue
        parsed = pd.to_datetime(s.head(sample_size), errors="coerce")
        valid = parsed.notna()
        frac = float(valid.mean())
        if frac < 0.6:
            continue
        years = parsed[valid].dt.year
        if years.empty or ((years < 1960) | (years > 2100)).any():
            continue  # epoch/phony values
        if parsed.nunique() < 2:
            continue  # single instant — not a time series date column
        score = frac + (0.15 if _DATE_HINT.search(str(col)) else 0.0)
        candidates.append((score, col))
    if not candidates:
        return None
    candidates.sort(key=lambda t: (-t[0], str(t[1])))
    return candidates[0][1]


def resolve_date_column(df: pd.DataFrame) -> Optional[str]:
    """Prefer an explicit name match; fall back to content-based detection."""
    return resolve_column(df.columns.tolist(), DATE) or detect_date_column_by_content(df)


def detect_kind(columns: List[str], df: Optional[pd.DataFrame] = None) -> str:
    """Decide whether an uploaded file is a sales file or an inventory file."""
    has_stock = resolve_column(columns, STOCK) is not None
    has_qty = resolve_column(columns, QUANTITY) is not None
    has_rev = resolve_column(columns, REVENUE) is not None
    has_date = resolve_column(columns, DATE) is not None
    if not has_date and df is not None:
        has_date = detect_date_column_by_content(df) is not None
    if has_date and has_stock and not has_qty and not has_rev:
        return "inventory"
    return "sales"


def parse_csv(raw: bytes, filename: str) -> pd.DataFrame:
    """Parse a raw CSV upload into a DataFrame, tolerating encoding quirks."""
    if not raw or not raw.strip():
        raise ValidationError("The uploaded file is empty.", code="empty_file")
    try:
        df = pd.read_csv(
            io.BytesIO(raw),
            encoding="utf-8",
            on_bad_lines="skip",
        )
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(
                io.BytesIO(raw),
                encoding="latin-1",
                on_bad_lines="skip",
            )
        except Exception as exc:  # pragma: no cover - defensive
            raise ValidationError(
                f"Could not read the file as a CSV. {exc}", code="unreadable"
            )
    except pd.errors.EmptyDataError:
        raise ValidationError("The uploaded file contains no data.", code="empty_file")
    except Exception as exc:
        raise ValidationError(f"Could not read the file as a CSV. {exc}", code="unreadable")

    if df is None or df.empty:
        raise ValidationError("The uploaded file contains no rows.", code="empty_file")
    if df.columns.tolist() == [None] or "Unnamed: 0" in str(df.columns[:1]):
        pass  # usually means malformed header; let resolve/validation catch it
    unknown = [c for c in df.columns if isinstance(c, float) and c != c]
    if unknown:
        raise ValidationError(
            "The CSV header could not be parsed. Check that the first row contains column names.",
            code="bad_header",
        )
    return df


def _to_float(df: pd.DataFrame, src_col: str) -> pd.Series:
    s = pd.to_numeric(df[src_col], errors="coerce")
    return s


def _normalize_sales(
    df: pd.DataFrame, quality: Dict, filename: str
) -> pd.DataFrame:
    n_source = len(df)
    date_col = resolve_date_column(df)
    quality["date_column"] = date_col

    if date_col is None:
        raise ValidationError(
            _missing_date_message(df),
            code="missing_date",
        )

    out = pd.DataFrame()
    out[DATE] = pd.to_datetime(df[date_col], errors="coerce")
    n_bad_dates = int(out[DATE].isna().sum())
    quality["bad_dates"] = n_bad_dates

    # Reject immediately when the detected date column holds no parseable dates
    # at all — clearer than a generic "no usable rows" message.
    if df[date_col].notna().any() and n_bad_dates == int(df[date_col].notna().sum()):
        raise ValidationError(
            f"The date column '{date_col}' was detected, but none of its values "
            "could be parsed as dates. Expected values like '2026-01-01' or "
            "'01/15/2026'.",
            code="unparseable_dates",
        )

    # product (optional -> "ALL")
    prod_col = resolve_column(df.columns, PRODUCT)
    if prod_col is None:
        out[PRODUCT] = "ALL"
        quality["product_column"] = "missing (single-product series)"
    else:
        out[PRODUCT] = df[prod_col].fillna("Unknown").astype(str).str.strip()
        out.loc[out[PRODUCT].isin(["", "nan", "None"]), PRODUCT] = "Unknown"

    # quantity (required)
    qty_col = resolve_column(df.columns, QUANTITY)
    if qty_col is not None:
        out[QUANTITY] = _to_float(df, qty_col)
        n_bad_qty = int(out[QUANTITY].isna().sum())
        quality["bad_quantity"] = n_bad_qty
        out.loc[out[QUANTITY] < 0, QUANTITY] = None
    else:
        out[QUANTITY] = None
        quality["bad_quantity"] = 0

    # revenue (optional)
    rev_col = resolve_column(df.columns, REVENUE)
    if rev_col is not None:
        out[REVENUE] = _to_float(df, rev_col)
        quality["bad_revenue"] = int(out[REVENUE].isna().sum())
        out.loc[out[REVENUE] < 0, REVENUE] = None
    else:
        out[REVENUE] = None
        quality["bad_revenue"] = 0
        quality["revenue_column"] = "missing (revenue KPIs unavailable)"

    # drop rows with no date or neither quantity nor revenue
    before = len(out)
    out = out.dropna(subset=[DATE])
    out = out.dropna(subset=[QUANTITY, REVENUE], how="all").copy()
    dropped = before - len(out)

    if out.empty:
        raise ValidationError(
            "No usable rows remained after parsing. Check that quantity/revenue columns "
            "contain numbers.",
            code="no_usable_rows",
        )
    if out[QUANTITY].notna().sum() == 0 and out[REVENUE].notna().sum() == 0:
        raise ValidationError(
            "No numeric quantity or revenue values were found in the file.",
            code="no_numeric_values",
        )

    quality["rows_dropped"] = quality.get("rows_dropped", 0) + dropped
    quality["rows_kept"] = int(len(out))

    # sort chronologically, drop exact duplicates
    n_dups = int(out.duplicated().sum())
    quality["duplicate_rows"] = n_dups
    out = out.drop_duplicates().sort_values([DATE, PRODUCT]).reset_index(drop=True)

    # fill missing revenue from quantity? NO — do not invent prices. Leave NaN.
    return out


def _normalize_inventory(
    df: pd.DataFrame, quality: Dict, filename: str
) -> pd.DataFrame:
    col_date = resolve_date_column(df)
    col_stock = resolve_column(df.columns, STOCK)
    col_prod = resolve_column(df.columns, PRODUCT)
    quality["inventory_date_column"] = col_date
    if col_date is None or col_stock is None:
        raise ValidationError(
            "Inventory file needs a date column and a stock column "
            "(e.g. 'date'/'inventory'/'stock'). "
            f"Detected columns: {_format_columns(df.columns)}.",
            code="invalid_inventory",
        )
    out = pd.DataFrame()
    out[DATE] = pd.to_datetime(df[col_date], errors="coerce")
    if col_prod is not None:
        out[PRODUCT] = df[col_prod].fillna("Unknown").astype(str).str.strip()
        out.loc[out[PRODUCT].isin(["", "nan", "None"]), PRODUCT] = "Unknown"
    else:
        out[PRODUCT] = "ALL"
    out[STOCK] = _to_float(df, col_stock)
    out.loc[out[STOCK] < 0, STOCK] = None
    out = out.dropna(subset=[DATE, STOCK]).drop_duplicates().reset_index(drop=True)
    if out.empty:
        raise ValidationError(
            "No usable inventory rows remained after parsing.", code="no_usable_rows"
        )
    quality["inventory_rows"] = len(out)
    quality["has_inventory"] = True
    return out


def _format_columns(columns) -> str:
    cols = [str(c) for c in columns]
    shown = ", ".join(f"'{c}'" for c in cols[:12])
    if len(cols) > 12:
        shown += ", …"
    return f"[{shown}]"


def _missing_date_message(df: pd.DataFrame) -> str:
    """Explain what was detected and what schema is expected — far more useful
    than a bare 'No date column found'."""
    return (
        "No date column was detected in this file. "
        f"Detected columns: {_format_columns(df.columns)}. "
        "Expected a date column such as 'date', 'order_date', 'sale date', "
        "'transaction_date', 'invoice date', 'timestamp' or 'created_at'.\n"
        "Example accepted schema:\n"
        "  date, product, quantity, revenue\n"
        "  2026-01-01, Wireless Earbuds, 10, 299.90"
    )


def load_dataset(
    sales_raw: bytes,
    sales_filename: str,
    inventory_raw: Optional[bytes] = None,
    inventory_filename: Optional[str] = None,
) -> Dict:
    """Full cleaning pipeline -> returns dict with normalized tables + quality summary.

    Raises ValidationError for unrecoverable problems.
    """
    quality: Dict = {
        "has_inventory": False,
        "rows_dropped": 0,
        "bad_dates": 0,
        "bad_quantity": 0,
        "bad_revenue": 0,
        "duplicate_rows": 0,
    }

    raw = parse_csv(sales_raw, sales_filename)
    sales = _normalize_sales(raw, quality, sales_filename)

    inventory = None
    if inventory_raw is not None and len(inventory_raw.strip()) > 0:
        try:
            raw_inv = parse_csv(inventory_raw, inventory_filename or "inventory.csv")
            if detect_kind(raw_inv.columns.tolist(), raw_inv) == "inventory":
                inventory = _normalize_inventory(raw_inv, quality, inventory_filename or "inventory.csv")
            else:
                quality["inventory_warning"] = (
                    "Uploaded second file did not look like inventory data (no stock column). "
                    "It was ignored."
                )
        except ValidationError as exc:
            quality["inventory_warning"] = f"Inventory file skipped: {exc.message}"

    quality["rows_in_source"] = len(raw)
    return {
        "sales": sales,
        "inventory": inventory,
        "quality": quality,
    }


def summarize_quality(sales: pd.DataFrame, quality: Dict) -> Dict:
    """Produce the user-facing data quality summary."""
    date_min = sales[DATE].min()
    date_max = sales[DATE].max()
    total_bad = (
        quality.get("bad_dates", 0)
        + quality.get("bad_quantity", 0)
        + quality.get("bad_revenue", 0)
        + quality.get("rows_dropped", 0)
    )
    n_rows = len(sales)
    dropped_pct = round(100.0 * total_bad / max(1, quality.get("rows_in_source", n_rows)), 1)
    return {
        "rows_in_source": quality.get("rows_in_source", 0),
        "rows_kept": quality.get("rows_kept", n_rows),
        "bad_dates": quality.get("bad_dates", 0),
        "bad_quantity": quality.get("bad_quantity", 0),
        "bad_revenue": quality.get("bad_revenue", 0),
        "duplicate_rows": quality.get("duplicate_rows", 0),
        "dropped_rows": quality.get("rows_dropped", 0),
        "dropped_pct": dropped_pct,
        "date_min": date_min.strftime("%Y-%m-%d") if date_min is not None else None,
        "date_max": date_max.strftime("%Y-%m-%d") if date_max is not None else None,
        "n_products": int(sales[PRODUCT].nunique()),
        "missing_revenue": bool("revenue_column" in quality),
        "inventory_warning": quality.get("inventory_warning"),
        "date_column": quality.get("date_column"),
        "inventory_date_column": quality.get("inventory_date_column"),
    }