"""POST /api/simulate — what-if scenario recalculation.

Takes the current analysis JSON + a scenario and actually recomputes coverage /
stock-risk values. Results are always labeled as a scenario, not a prediction.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler

from api import _common  # noqa: F401
from analytics.simulate import run_scenario


def handle(payload: dict) -> tuple[int, dict]:
    analysis = payload.get("analysis")
    scenario = payload.get("scenario")
    if not analysis:
        return 400, {
            "ok": False,
            "error": "Missing analytics context. Run the analysis first.",
            "code": "missing_analysis",
        }
    if not scenario or not isinstance(scenario, dict):
        return 400, {"ok": False, "error": "Missing scenario parameters.", "code": "missing_scenario"}
    try:
        result = run_scenario(analysis, scenario)
        return 200, {"ok": True, "result": result}
    except Exception as exc:
        return 500, {"ok": False, "error": f"Simulation failed: {exc}", "code": "simulate_error"}


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        payload = _common.read_json_body(self)
        _common.respond(self, handle(payload))
        return
        # vercel:handler