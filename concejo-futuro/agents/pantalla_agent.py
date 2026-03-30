"""TavoDebate - Agente Pantalla (WebSocket + página del proyector)."""

import asyncio
import json
import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from agents.base_agent import BaseAgent

logger = logging.getLogger("agent.pantalla")

app = FastAPI(title="TavoDebate Pantalla")

# WebSocket clients set
ws_clients: set[WebSocket] = set()

ALL_CHANNELS = [
    "broadcast:sent", "bomb:sent", "fakenews:sent",
    "alert:sent", "tweet:new", "position:changed",
    "vote:cast", "proposal:new", "timer:update",
    "gabinete:event", "pressure:sent", "ponencia:analyzed",
    "layout:change", "leaderboard:update",
    "pantalla:command",
]


class PantallaAgent(BaseAgent):
    name = "pantalla"

    async def start(self):
        app.state.bus = self.bus
        app.state.agent = self

        # Mount static files
        static_dir = Path(__file__).parent.parent / "web" / "static"
        static_dir.mkdir(parents=True, exist_ok=True)
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        # Start Redis listener
        asyncio.create_task(self._redis_listener())

        # Run FastAPI
        config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    async def _redis_listener(self):
        """Escucha TODOS los canales y reenvía por WebSocket."""
        pubsub = self.bus.pubsub()
        await pubsub.subscribe(*ALL_CHANNELS)

        logger.info(f"Pantalla listening on {len(ALL_CHANNELS)} channels")
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                channel = message["channel"]
                if isinstance(channel, bytes):
                    channel = channel.decode()
                data_str = message["data"]
                if isinstance(data_str, bytes):
                    data_str = data_str.decode()
                data = json.loads(data_str)

                # Handle pantalla commands
                if channel == "pantalla:command":
                    await self._handle_command(data)
                    continue

                event = {"channel": channel, "data": data}
                await self._broadcast_ws(event)
            except Exception as e:
                logger.error(f"Redis listener error: {e}")

    async def _handle_command(self, data: dict):
        action = data.get("action")
        if action == "layout_change":
            await self._broadcast_ws({
                "channel": "layout:change",
                "data": data.get("args", {}),
            })

    async def _broadcast_ws(self, event: dict):
        """Envía evento a todos los WebSocket clients."""
        dead = set()
        for ws in ws_clients:
            try:
                await ws.send_json(event)
            except Exception:
                dead.add(ws)
        ws_clients -= dead


# --- FastAPI routes ---

@app.get("/pantalla")
async def pantalla_page():
    html_path = Path(__file__).parent.parent / "web" / "pantalla.html"
    return FileResponse(str(html_path), media_type="text/html")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_clients.add(websocket)
    logger.info(f"WebSocket client connected ({len(ws_clients)} total)")
    try:
        while True:
            # Keep connection alive, receive pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_clients.discard(websocket)
        logger.info(f"WebSocket client disconnected ({len(ws_clients)} total)")
