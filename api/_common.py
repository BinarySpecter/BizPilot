"""Shared helpers for Vercel Python functions in /api.

Files prefixed with `_` are treated as utility modules by Vercel — they are NOT
exposed as routes but remain importable by /api functions.
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler

# ---------------------------------------------------------------------------
# Ensure the project root is importable (so `analytics` can be imported from
# anywhere, including inside Vercel functions).
# ---------------------------------------------------------------------------
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

CONTENT_TYPE = "application/json; charset=utf-8"


def read_json_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(length) if length else b""
    if not raw:
        return {}
    try:
        body = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}
    if not isinstance(body, dict):
        return {}
    return body


def send_json(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    data = json.dumps(payload, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", CONTENT_TYPE)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def respond(handler: BaseHTTPRequestHandler, result) -> None:
    """`result` is a (status_code, payload_dict) tuple produced by endpoint `handle`."""
    status, payload = result
    send_json(handler, status, payload)