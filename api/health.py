"""GET /api/health — liveness probe.

Same JSON shape as the local development server's health endpoint
(see scripts/dev_api.py), so /api/health behaves identically locally and on
the Vercel deployment.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler

from api import _common  # noqa: F401


def handle() -> tuple[int, dict]:
    return 200, {"ok": True, "service": "bizpilot-api", "engine": "analytics"}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        _common.respond(self, handle())
        return
        # vercel:handler