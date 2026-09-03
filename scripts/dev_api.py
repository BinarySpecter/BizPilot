"""Local development API server for the BizPilot Python endpoints.

Runs the same /api/*.py modules that Vercel serves, on http://127.0.0.1:8787.
Next.js proxies /api/* to this server during local development (see next.config.ts).

Usage:
    python3 scripts/dev_api.py            # listen on 127.0.0.1:8787
"""

from __future__ import annotations

import importlib.util
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_DIR = os.path.join(ROOT, "api")


def load_env_files() -> None:
    """Lightweight .env / .env.local loader (stdlib only).

    Next.js loads these files for the web server; this makes the same values
    available to the *separate* local Python API process so keys set in
    .env.local (e.g. LLM_API_KEY for Groq) work locally. Existing environment
    variables always win. The files are git-ignored and never tracked.
    """
    for name in (".env", ".env.local"):
        path = os.path.join(ROOT, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value
        except OSError:
            pass


load_env_files()

# Make the /api utility modules and the root `analytics` package importable.
for p in (API_DIR, ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)


def load_api_module(name: str):
    path = os.path.join(API_DIR, f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


MODULES = {name: load_api_module(name) for name in ("analyze", "chat", "simulate")}

SAMPLE_ROUTES = {"/api/analyze"}  # GET -> sample dataset
JSON_ROUTES = {"/api/analyze", "/api/chat", "/api/simulate"}


class Dispatcher(BaseHTTPRequestHandler):
    server_version = "BizPilotDevAPI/1.0"

    def log_message(self, fmt, *args):  # quieter logs
        sys.stderr.write("[api] " + fmt % args + "\n")

    def _send(self, status: int, payload: dict):
        import json

        data = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _dispatch(self):
        path = self.path.split("?")[0]
        if path == "/api/health":
            self._send(200, {"ok": True, "service": "bizpilot-local-api", "engine": "analytics"})
            return
        mod = MODULES.get(path.removeprefix("/api/"))
        if mod is None:
            self._send(404, {"ok": False, "error": "Not found.", "code": "not_found"})
            return
        if self.command == "GET" and path in SAMPLE_ROUTES:
            status, body = mod.handle({"sample": True})
            self._send(status, body)
            return
        if self.command != "POST" or path not in JSON_ROUTES:
            self._send(405, {"ok": False, "error": "Method not allowed.", "code": "method"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        import json

        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except json.JSONDecodeError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        status, body = mod.handle(payload)
        self._send(status, body)

    def do_GET(self):
        self._dispatch()

    def do_POST(self):
        self._dispatch()


def main() -> None:
    host, port = os.environ.get("PYTHON_API_HOST", "127.0.0.1"), int(
        os.environ.get("PYTHON_API_PORT", "8787")
    )
    httpd = ThreadingHTTPServer((host, port), Dispatcher)
    print(f"[api] BizPilot local API listening on http://{host}:{port}")
    print("[api] routes: /api/analyze (POST or GET for sample), /api/chat, /api/simulate, /api/health")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[api] shutting down")


if __name__ == "__main__":
    main()