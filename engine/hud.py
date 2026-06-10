# deep/hud.py — FastAPI + WebSocket HUD (Bible Section 28)
"""Standalone HUD server for the DEEP science/tech engine.

Endpoints:
  GET  /            -> serves the neon HUD (index.html)
  GET  /status      -> hardware snapshot (system_monitor)
  POST /command     -> {text} -> routes through DEEP, returns {verbal, ...}
  WS   /ws          -> real-time command/response stream

Runs on config.FASTAPI_PORT (default 8000) — separate from the live DEEP
server on 7768, so the two never collide. Launch:  python -m engine.hud
"""
from __future__ import annotations

import os
import threading

try:
    from . import config
except Exception:  # pragma: no cover
    import config

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    FASTAPI = True
except Exception:  # pragma: no cover
    FASTAPI = False

_HTML_PATH = os.path.join(os.path.dirname(__file__), "hud_index.html")


def create_app(deep=None):
    if not FASTAPI:
        raise RuntimeError("FastAPI/uvicorn not installed")
    from .main import DEEP
    from . import system_monitor
    deep = deep or DEEP()

    app = FastAPI(title="DEEP HUD")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                       allow_headers=["*"])

    @app.get("/", response_class=HTMLResponse)
    async def root():
        if os.path.exists(_HTML_PATH):
            return open(_HTML_PATH, encoding="utf-8").read()
        return "<h1>DEEP HUD</h1><p>index.html missing.</p>"

    @app.get("/status")
    async def status():
        return JSONResponse(system_monitor.report(""))

    @app.post("/command")
    async def command(payload: dict):
        text = payload.get("text", "")
        out = deep.process_command(text)
        return JSONResponse(out)

    @app.websocket("/ws")
    async def ws(websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                text = await websocket.receive_text()
                out = deep.process_command(text)
                await websocket.send_json(out)
        except WebSocketDisconnect:
            pass

    return app


def run_hud(deep=None, host=None, port=None, background=False):
    host = host or config.FASTAPI_HOST
    port = port or config.FASTAPI_PORT
    app = create_app(deep)

    def _serve():
        uvicorn.run(app, host=host, port=port, log_level="warning")
    if background:
        t = threading.Thread(target=_serve, daemon=True); t.start()
        return t
    _serve()


def test() -> None:
    # app must construct without binding a socket
    if FASTAPI:
        app = create_app()
        routes = {r.path for r in app.routes}
        assert "/status" in routes and "/command" in routes
        print("hud: FastAPI app OK")
    else:
        print("hud: FastAPI unavailable (skipped)")


if __name__ == "__main__":
    print(f"DEEP HUD on http://localhost:{config.FASTAPI_PORT}")
    run_hud()
