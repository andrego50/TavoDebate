"""TavoDebate - Clase base para todos los agentes."""

import asyncio
import json
import logging

from core.config import settings
from core.redis_bus import RedisBus


class BaseAgent:
    """Clase base con funcionalidad compartida entre agentes."""

    name: str = "base"

    def __init__(self):
        self.bus = RedisBus()
        self.logger = logging.getLogger(f"agent.{self.name}")
        self._running = True

    async def setup(self):
        """Inicialización: conectar Redis, DB, etc."""
        await self.bus.connect()
        self.logger.info(f"Agent {self.name} initialized")

    async def run(self):
        """Punto de entrada principal."""
        await self.setup()
        try:
            # Start health responder
            asyncio.create_task(self._health_responder())
            await self.start()
        except Exception as e:
            self.logger.error(f"Agent {self.name} crashed: {e}", exc_info=True)
            raise
        finally:
            await self.shutdown()

    async def start(self):
        """Override en cada agente."""
        raise NotImplementedError

    async def shutdown(self):
        """Limpieza al apagar."""
        self._running = False
        await self.bus.close()
        self.logger.info(f"Agent {self.name} shut down")

    async def _health_responder(self):
        """Responde a pings del orquestador."""
        pubsub = self.bus.pubsub()
        await pubsub.subscribe(f"{self.name}:ping")
        async for message in pubsub.listen():
            if message["type"] == "message":
                await self.bus.publish(f"{self.name}:pong", {
                    "agent": self.name,
                    "instance": self.bus.instance_id,
                    "status": "ok",
                })
