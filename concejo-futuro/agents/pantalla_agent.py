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

# In-memory event history (persisted to Redis)
event_history: list[dict] = []

ALL_CHANNELS = [
    "broadcast:sent", "bomb:sent", "fakenews:sent",
    "alert:sent", "tweet:new", "position:changed",
    "vote:cast", "proposal:new", "timer:update",
    "gabinete:event", "pressure:sent", "ponencia:analyzed",
    "layout:change", "leaderboard:update",
    "pantalla:command", "interaction:live",
]

# Channels worth persisting for replay on page reload
PERSIST_CHANNELS = {
    "tweet:new", "broadcast:sent", "bomb:sent", "fakenews:sent",
    "alert:sent", "pressure:sent", "vote:cast", "proposal:new",
    "gabinete:event",
}

REDIS_HISTORY_KEY = "tavodebate:pantalla_history"
MAX_HISTORY = 200


class PantallaAgent(BaseAgent):
    name = "pantalla"

    async def start(self):
        app.state.bus = self.bus
        app.state.agent = self

        # Mount static files
        static_dir = Path(__file__).parent.parent / "web" / "static"
        static_dir.mkdir(parents=True, exist_ok=True)
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        # Mount geodashboard data
        geo_data_dir = Path(__file__).parent.parent / "geodashboard" / "data"
        if geo_data_dir.exists():
            app.mount("/geodashboard/data", StaticFiles(directory=str(geo_data_dir)), name="geodata")

        # Load event history from Redis
        await self._load_history()

        # Start Redis listener
        asyncio.create_task(self._redis_listener())

        # Run FastAPI
        config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    async def _load_history(self):
        """Load persisted event history from Redis on startup."""
        global event_history
        try:
            raw = await self.bus.redis.lrange(REDIS_HISTORY_KEY, 0, -1)
            event_history = [json.loads(r) for r in raw]
            logger.info(f"Loaded {len(event_history)} events from history")
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            event_history = []

    async def _save_event(self, event: dict):
        """Persist event to Redis list."""
        global event_history
        event_history.append(event)
        try:
            await self.bus.redis.rpush(REDIS_HISTORY_KEY, json.dumps(event))
            await self.bus.redis.ltrim(REDIS_HISTORY_KEY, -MAX_HISTORY, -1)
        except Exception as e:
            logger.error(f"Failed to save event: {e}")
        # Trim in-memory too
        if len(event_history) > MAX_HISTORY:
            event_history[:] = event_history[-MAX_HISTORY:]

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

                # Assign an ID to every tweet that doesn't have one yet and
                # keep a rolling list of the last 30 so they can be cited.
                if channel == "tweet:new" and not data.get("tweet_id"):
                    try:
                        tid = await self.bus.redis.incr("tavodebate:tweet_counter")
                        data["tweet_id"] = int(tid)
                        await self.bus.redis.lpush(
                            "tavodebate:recent_tweets", json.dumps(data)
                        )
                        await self.bus.redis.ltrim("tavodebate:recent_tweets", 0, 29)
                    except Exception as e:
                        logger.error(f"Failed to assign tweet_id: {e}")

                event = {"channel": channel, "data": data}

                # Persist important events
                if channel in PERSIST_CHANNELS:
                    await self._save_event(event)

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
        global ws_clients
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


@app.get("/geodashboard")
async def geodashboard_page():
    html_path = Path(__file__).parent.parent / "geodashboard" / "index.html"
    return FileResponse(str(html_path), media_type="text/html")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_clients.add(websocket)
    logger.info(f"WebSocket client connected ({len(ws_clients)} total)")

    # Send full event history to new client
    for event in event_history:
        try:
            await websocket.send_json(event)
        except Exception:
            break

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_clients.discard(websocket)
        logger.info(f"WebSocket client disconnected ({len(ws_clients)} total)")
