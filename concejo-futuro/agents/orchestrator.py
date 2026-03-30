"""TavoDebate - Orquestador central (FastAPI + webhook + health)."""

import asyncio
import json
import logging

import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from agents.base_agent import BaseAgent
from core.config import settings
from core.redis_bus import RedisBus
from db.database import init_db, close_db

logger = logging.getLogger("orchestrator")

app = FastAPI(title="TavoDebate Orchestrator")


class Orchestrator(BaseAgent):
    name = "orchestrator"

    def __init__(self):
        super().__init__()
        self.current_phase = None
        self.autonomy_level = "aprobar"
        self.agents_health = {}

    async def setup(self):
        await super().setup()
        await init_db()

        # Attach bus to app state for route access
        app.state.bus = self.bus
        app.state.orchestrator = self

    async def start(self):
        # Start health checker loop
        asyncio.create_task(self._health_check_loop())
        asyncio.create_task(self._outgoing_message_loop())
        asyncio.create_task(self._backup_loop())

        # Run FastAPI
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
        )
        server = uvicorn.Server(config)
        await server.serve()

    async def shutdown(self):
        await close_db()
        await super().shutdown()

    async def handle_admin_command(self, command: str, args: dict):
        """Enruta comandos admin al agente correcto."""
        routing = {
            "fase": ("simulation", "phase_change"),
            "broadcast": ("control", "broadcast"),
            "bomba": ("control", "bomb"),
            "fakenews": ("control", "fakenews"),
            "presion": ("control", "pressure"),
            "gabinete": ("control", "gabinete"),
            "alerta": ("control", "alert"),
            "grabar": ("audio", "ponencia_record"),
            "briefing": ("intel", "force_briefing"),
            "pantalla": ("pantalla", "layout_change"),
            "ronda": ("simulation", "start_timer"),
            "tweet": ("pantalla", "add_tweet"),
            "llm": ("orchestrator", "llm_switch"),
        }

        target = routing.get(command)
        if not target:
            return False

        agent, action = target
        if agent == "orchestrator":
            await self._handle_own_command(action, args)
        else:
            await self.bus.publish(f"{agent}:command", {
                "action": action,
                "args": args,
            })
        return True

    async def _handle_own_command(self, action: str, args: dict):
        if action == "llm_switch":
            provider = args.get("provider", "deepseek")
            logger.info(f"Switching LLM to {provider}")

    async def _health_check_loop(self):
        while self._running:
            await asyncio.sleep(30)
            for agent_name in ["chat", "intel", "control", "pantalla", "audio", "simulation"]:
                try:
                    await self.bus.publish(f"{agent_name}:ping", {"from": "orchestrator"})
                except Exception as e:
                    self.agents_health[agent_name] = "error"
                    logger.warning(f"Health ping failed for {agent_name}: {e}")

    async def _outgoing_message_loop(self):
        """Lee telegram:outgoing y envía mensajes via bot API."""
        import httpx
        bot_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}"

        async with httpx.AsyncClient() as client:
            while self._running:
                try:
                    messages = await self.bus.stream_read_group(
                        "telegram:outgoing", "orchestrator", count=20, block=3000
                    )
                    for entry_id, data in messages:
                        try:
                            payload = {
                                "chat_id": data["chat_id"],
                                "text": data["text"],
                                "parse_mode": data.get("parse_mode", "Markdown"),
                            }
                            if "reply_markup" in data:
                                payload["reply_markup"] = data["reply_markup"]
                            resp = await client.post(
                                f"{bot_url}/sendMessage", json=payload,
                            )
                            if resp.status_code != 200:
                                resp_data = resp.json()
                                if resp_data.get("description", "").find("parse") >= 0:
                                    # Markdown parse error — retry without parse_mode
                                    payload.pop("parse_mode", None)
                                    await client.post(
                                        f"{bot_url}/sendMessage", json=payload,
                                    )
                                else:
                                    logger.error(f"Telegram API error: {resp_data}")
                        except Exception as e:
                            logger.error(f"Failed to send Telegram message: {e}")
                        await self.bus.stream_ack("telegram:outgoing", "orchestrator", entry_id)
                except Exception as e:
                    logger.error(f"Outgoing loop error: {e}")
                    await asyncio.sleep(2)

    async def _backup_loop(self):
        """Backup PostgreSQL cada 15 min."""
        import os
        while self._running:
            await asyncio.sleep(900)
            try:
                os.system(
                    "pg_dump -h postgres -U concejo concejo_futuro "
                    "> /app/backups/backup_$(date +%H%M).sql 2>/dev/null"
                )
                logger.info("Database backup completed")
            except Exception as e:
                logger.error(f"Backup failed: {e}")


# --- FastAPI routes ---

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Recibe updates de Telegram y los enruta al Chat Agent vía Redis."""
    update = await request.json()
    bus: RedisBus = request.app.state.bus
    await bus.stream_add("telegram:incoming", update)
    return {"ok": True}


@app.get("/health")
async def health_check(request: Request):
    orch: Orchestrator = request.app.state.orchestrator
    return JSONResponse({
        "status": "ok",
        "agents": orch.agents_health,
        "phase": orch.current_phase,
    })


@app.post("/admin/command")
async def admin_command(request: Request):
    """Endpoint para comandos admin desde el dashboard."""
    body = await request.json()
    orch: Orchestrator = request.app.state.orchestrator
    success = await orch.handle_admin_command(body["command"], body.get("args", {}))
    return {"ok": success}


@app.get("/api/status")
async def api_status(request: Request):
    orch: Orchestrator = request.app.state.orchestrator
    return {
        "phase": orch.current_phase,
        "autonomy": orch.autonomy_level,
        "agents": orch.agents_health,
    }
