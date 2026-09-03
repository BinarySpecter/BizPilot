"""POST /api/analyze — full analytics pipeline.

Accepts JSON:
  {
    "sales_csv": "...csv text...",        // required (unless using sample)
    "sales_filename": "sales.csv",
    "inventory_csv": "...csv text...",    // optional
    "inventory_filename": "inventory.csv" // optional
  }

GET /api/analyze runs the analysis on the bundled demo dataset
(data/sample/), which powers the "Try sample data" flow.
"""

from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler

from api import _common  # noqa: F401
from analytics.cleaning import ValidationError
from analytics.engine import analyze as run_analysis
from analytics.engine import to_response

SAMPLE_DIR = os.path.join(_common.PROJECT_ROOT, "data", "sample")
SAMPLE_SALES = os.path.join(SAMPLE_DIR, "sales.csv")
SAMPLE_INVENTORY = os.path.join(SAMPLE_DIR, "inventory.csv")


def _read_sample() -> tuple[bytes, str, bytes | None, str | None]:
    with open(SAMPLE_SALES, "rb") as f:
        sales = f.read()
    if os.path.exists(SAMPLE_INVENTORY):
        with open(SAMPLE_INVENTORY, "rb") as f:
            inv = f.read()
        return sales, "sample_sales.csv", inv, "sample_inventory.csv"
    return sales, "sample_sales.csv", None, None


def handle(payload: dict) -> tuple[int, dict]:
    try:
        if payload.get("sample") or not payload.get("sales_csv"):
            sales_raw, sales_name, inv_raw, inv_name = _read_sample()
            analysis = run_analysis(sales_raw, sales_name, inv_raw, inv_name)
            return 200, {"ok": True, "analysis": to_response(analysis), "source": "sample"}
        sales_csv = payload["sales_csv"]
        sales_name = payload.get("sales_filename") or "uploaded.csv"
        inv_csv = payload.get("inventory_csv")
        inv_name = payload.get("inventory_filename")
        analysis = run_analysis(
            sales_csv.encode("utf-8"),
            sales_name,
            inv_csv.encode("utf-8") if inv_csv else None,
            inv_name,
        )
        return 200, {"ok": True, "analysis": to_response(analysis), "source": "upload"}
    except ValidationError as exc:
        return 400, {"ok": False, "error": exc.message, "code": exc.code}
    except Exception as exc:  # defensive; never leak raw internals to the client
        return 500, {"ok": False, "error": f"Analysis failed: {exc}", "code": "engine_error"}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        _common.respond(self, handle({"sample": True}))
        return
        # vercel:handler

    def do_POST(self):
        payload = _common.read_json_body(self)
        _common.respond(self, handle(payload))
        return
        # vercel:handler