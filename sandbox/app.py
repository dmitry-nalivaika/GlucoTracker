"""FastAPI application for the GlucoTrack sandbox.

Routes:
  GET  /           → serve static/index.html
  WS   /ws         → real-time bidirectional event channel
  GET  /api/status → current configuration snapshot
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse

logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="GlucoTrack Sandbox", docs_url=None, redoc_url=None)

# Active WebSocket connections (at most one concurrent run is allowed)
_active_ws: WebSocket | None = None
_run_lock = asyncio.Lock()


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html", media_type="text/html")


@app.get("/api/status")
async def status() -> JSONResponse:
    """Return environment credential availability for each component."""
    from sandbox.workflow import _load_dotenv

    _load_dotenv()
    return JSONResponse(
        {
            "ai_credentials_available": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "miro_credentials_available": bool(
                os.environ.get("MIRO_ACCESS_TOKEN") and os.environ.get("MIRO_BOARD_ID")
            ),
        }
    )


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    global _active_ws
    await ws.accept()
    _active_ws = ws
    logger.info("Sandbox WebSocket connected")

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg: dict[str, Any] = json.loads(raw)
            except json.JSONDecodeError:
                await _send(ws, {"type": "error", "message": "Invalid JSON"})
                continue

            action = msg.get("action")
            if action == "run":
                await _handle_run(ws, msg.get("config", {}))
            elif action == "ping":
                await _send(ws, {"type": "pong"})
            else:
                await _send(ws, {"type": "error", "message": f"Unknown action: {action}"})

    except WebSocketDisconnect:
        logger.info("Sandbox WebSocket disconnected")
    finally:
        _active_ws = None


async def _handle_run(ws: WebSocket, config: dict[str, Any]) -> None:
    """Execute the workflow and stream events over ``ws``."""
    if _run_lock.locked():
        await _send(
            ws,
            {
                "type": "error",
                "message": "A workflow run is already in progress. Please wait.",
            },
        )
        return

    async with _run_lock:
        from sandbox.workflow import SandboxWorkflow

        ai_mode = config.get("ai_mode", "mock")
        miro_mode = config.get("miro_mode", "mock")

        await _send(
            ws,
            {
                "type": "run_started",
                "config": {"ai_mode": ai_mode, "miro_mode": miro_mode},
            },
        )

        async def emit(event: dict[str, Any]) -> None:
            await _send(ws, event)

        workflow = SandboxWorkflow(
            callback=emit,
            ai_mode=ai_mode,
            miro_mode=miro_mode,
        )
        await workflow.run()

        await _send(ws, {"type": "run_complete"})


async def _send(ws: WebSocket, data: dict[str, Any]) -> None:
    try:
        await ws.send_json(data)
    except Exception:
        pass
