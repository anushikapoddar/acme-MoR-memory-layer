"""Zero-dependency HTTP server for the dashboard.

Standard library only: no pip install, no build step, no lockfile. The whole
demo is `python3 -m riskmemory.server` on any machine with Python 3.11+.
"""
from __future__ import annotations

import json
import mimetypes
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .app import App
from .explain import load_dotenv, llm_status

load_dotenv()

mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/svg+xml", ".svg")

WEB = Path(__file__).resolve().parent.parent / "web"
STATE = None
LOCK = threading.Lock()
READY = threading.Event()

WARMING_HTML = b"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="3">
<title>Acme MoR \xe2\x80\x94 starting</title>
<style>
  html,body{height:100%;margin:0;background:#0B0E0C;color:#F4F6F5;
    font-family:Inter,system-ui,sans-serif}
  body{display:grid;place-items:center}
  .box{max-width:28rem;padding:2rem;text-align:center}
  .mark{width:40px;height:40px;border-radius:50%;background:#1A4A38;
    color:#F4F1E6;display:grid;place-items:center;font-weight:800;margin:0 auto 1rem}
  h1{font-size:1.25rem;margin:0 0 .5rem}
  p{color:#8B938E;line-height:1.5}
</style>
</head>
<body>
  <div class="box">
    <div class="mark">A</div>
    <h1>Acme MoR</h1>
    <p>Building the merchant corpus. This takes about a minute the first time &mdash; the page will open on its own.</p>
  </div>
</body>
</html>
"""


def _build_state() -> None:
    global STATE
    app = App()
    with LOCK:
        STATE = app
        READY.set()
    p = app.portfolio()
    print("\n  Merchant Risk Memory")
    print(f"  {p['approved']:,} active merchants  |  {p['queue_size']} in the review queue"
          f"  |  {p['alert_total']} open alerts")
    print(f"  graph: {p['graph']['nodes']:,} nodes, {p['graph']['edges']:,} edges"
          f"  |  memory: {p['memory']['active']} active records")
    print(f"  llm: {llm_status()}\n")


class Handler(BaseHTTPRequestHandler):
    server_version = "MerchantRiskMemory/1.0"

    def log_message(self, fmt, *args):        # keep the console readable
        pass

    # -- helpers ------------------------------------------------------------
    def _json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _warming(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(WARMING_HTML)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(WARMING_HTML)

    def _static(self, path: str) -> None:
        rel = "index.html" if path in ("/", "") else path.lstrip("/")
        target = (WEB / rel).resolve()
        if not str(target).startswith(str(WEB.resolve())) or not target.is_file():
            self.send_error(404, "Not found")
            return
        body = target.read_bytes()
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            return {}

    def _app(self):
        if not READY.is_set():
            self._json({"error": "starting", "ready": False}, 503)
            return None
        return STATE

    # -- routes -------------------------------------------------------------
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            return self._json({"ok": True, "ready": READY.is_set()})
        if not path.startswith("/api/"):
            if path in ("/", "") and not READY.is_set():
                return self._warming()
            return self._static(path)

        app = self._app()
        if app is None:
            return
        with LOCK:
            if path == "/api/overview":
                return self._json(app.overview())
            if path == "/api/directory":
                qs = parse_qs(urlparse(self.path).query)
                return self._json(app.directory(
                    q=(qs.get("q") or [""])[0], band=(qs.get("band") or [""])[0],
                    limit=int((qs.get("limit") or ["40"])[0]),
                    offset=int((qs.get("offset") or ["0"])[0])))
            if path == "/api/dashboard":
                return self._json(app.dashboard())
            if path == "/api/summary":
                return self._json(app.summary())
            if path == "/api/portfolio":
                return self._json(app.portfolio())
            if path == "/api/queue":
                return self._json(app.queue())
            if path.startswith("/api/brief/"):
                brief = app.brief(path.rsplit("/", 1)[-1])
                return self._json(brief or {"error": "not found"},
                                  200 if brief else 404)
            if path == "/api/alerts":
                return self._json([a.to_dict() for a in app.alerts()])
            if path == "/api/drift":
                return self._json(app.drift())
            if path == "/api/memory":
                return self._json(app.memory_list())
            if path == "/api/assessments":
                return self._json(app.assessments())
            if path == "/api/gate-history":
                return self._json(app.gate_history)
            if path == "/api/incidents":
                out = [{
                    "id": m.id, "name": m.name,
                    "category": m.truth_category, "note": m.truth_note,
                    "status": m.status, "scenario": bool(m.scenario),
                } for m in app.merchants
                    if m.truth_bad and m.status in ("approved", "terminated")]
                # Named narrative cases first: they carry a real incident note,
                # so the dropdown opens on something worth demonstrating rather
                # than an anonymous row from the background population.
                out.sort(key=lambda d: (not d["scenario"], d["category"] or ""))
                return self._json(out[:40])
            if path == "/api/applications":
                return self._json(app.applications())
            if path.startswith("/api/applications/"):
                row = app.application(path.rsplit("/", 1)[-1])
                return self._json(row or {"error": "not found"},
                                  200 if row else 404)
        self.send_error(404, "Unknown endpoint")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        payload = self._body()
        app = self._app()
        if app is None:
            return
        if path == "/api/assess":
            with LOCK:
                out = app.assess(payload)
            if not out.get("error") and payload.get("explain"):
                from .explain import explain_assessment
                out["explanation"] = explain_assessment(out)
                log = app.assessment_log
                if log and log[0].get("merchant_id") == out.get("merchant_id"):
                    log[0]["brief"] = out
            return self._json(out, 400 if out.get("error") else 200)
        with LOCK:
            if path == "/api/decide":
                return self._json(app.record_decision(
                    payload.get("merchant_id", ""), payload.get("action", ""),
                    payload.get("rationale", "")))
            if path == "/api/ingest":
                return self._json(app.ingest_incident(payload.get("merchant_id", "")))
            if path == "/api/replay":
                return self._json(app.replay_now())
            if path == "/api/reset":
                app.reset()
                return self._json({"ok": True})
        self.send_error(404, "Unknown endpoint")


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    threading.Thread(target=_build_state, daemon=True).start()
    httpd = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}/"
    print(f"\n  -> {url}")
    print("  building corpus in the background\n")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped\n")
        httpd.shutdown()


if __name__ == "__main__":
    import argparse
    hosted = "PORT" in os.environ
    default_port = int(os.environ.get("PORT", "8765"))
    default_host = os.environ.get("HOST", "0.0.0.0" if hosted else "127.0.0.1")
    ap = argparse.ArgumentParser(description="Merchant Risk Memory demo server")
    ap.add_argument("--port", type=int, default=default_port)
    ap.add_argument("--host", default=default_host)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    open_browser = not a.no_browser and not hosted and a.host in ("127.0.0.1", "localhost")
    serve(a.host, a.port, open_browser)
