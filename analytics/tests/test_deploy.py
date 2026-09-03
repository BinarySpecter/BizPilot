"""Deployment-contract tests for the Vercel Python functions.

Vercel's Python runtime executes each function via `BaseHTTPRequestHandler`
and requires the `# vercel:handler` marker comment inside do_GET/do_POST.
These tests pin that contract so a deployment regression is caught locally.
"""

import io
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
API_DIR = os.path.join(ROOT, "api")
for _p in (ROOT, API_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from api import _common  # noqa: E402
from api import analyze, chat, health, simulate  # noqa: E402

FILES = ("analyze.py", "chat.py", "simulate.py", "health.py")


def _source(name: str) -> str:
    with open(os.path.join(API_DIR, name), encoding="utf-8") as fh:
        return fh.read()


@pytest.mark.parametrize("name", FILES)
def test_each_handler_has_vercel_marker(name):
    src = _source(name)
    assert "class handler(BaseHTTPRequestHandler)" in src, name
    assert "vercel:handler" in src, f"{name} is missing the Vercel handler marker"


def test_analyze_exposes_get_and_post():
    src = _source("analyze.py")
    assert "def do_GET" in src
    assert "def do_POST" in src


def test_json_endpoints_are_post_handler():
    for name in ("chat.py", "simulate.py", "health.py"):
        src = _source(name)
        assert "def do_POST" in src or "def do_GET" in src, name


def test_health_handle_shape():
    status, payload = health.handle()
    assert status == 200
    assert payload["ok"] is True
    assert payload["service"] == "bizpilot-api"
    assert payload["engine"] == "analytics"


def test_common_reads_json_body():
    payload = b'{"a":1}'

    class FakeReq:
        headers = {"Content-Length": str(len(payload))}
        rfile = io.BytesIO(payload)

    assert _common.read_json_body(FakeReq()) == {"a": 1}

    class Empty:
        headers = {}
        rfile = io.BytesIO(b"")

    assert _common.read_json_body(Empty()) == {}


def test_common_writes_http_response():
    class FakeResp:
        def __init__(self):
            self.buf = io.BytesIO()

        def send_response(self, code):
            self.buf.write(f"HTTP/1.0 {code} OK\r\n".encode())

        def send_header(self, key, value):
            self.buf.write(f"{key}: {value}\r\n".encode())

        def end_headers(self):
            self.buf.write(b"\r\n")

        @property
        def wfile(self):
            return self.buf

    resp = FakeResp()
    _common.send_json(resp, 200, {"ok": True})
    out = resp.buf.getvalue().decode()
    assert out.startswith("HTTP/1.0 200 OK")
    assert '"ok": true' in out