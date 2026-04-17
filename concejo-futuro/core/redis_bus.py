"""TavoDebate - Redis bus de eventos (Streams + Pub/Sub)."""

import json
import logging
import os
import uuid

import redis.asyncio as aioredis

from core.config import settings

logger = logging.getLogger(__name__)

INSTANCE_ID = os.getenv("HOSTNAME", uuid.uuid4().hex[:8])

# Canales que usan Streams (persistentes, con ACK)
STREAM_CHANNELS = {
    "telegram:incoming",
    "telegram:outgoing",
    "interaction:new",
    "ponencia:record",
}

# Canales que usan Pub/Sub (efímeros)
PUBSUB_CHANNELS = {
    "timer:update",
    "layout:change",
    "tweet:new",
    "leaderboard:update",
    "broadcast:sent",
    "bomb:sent",
    "fakenews:sent",
    "alert:sent",
    "position:changed",
    "vote:cast",
    "proposal:new",
    "briefing:new",
    "proposal:proactive",
    "pressure:sent",
    "gabinete:event",
    "ponencia:analyzed",
    "audio:transcribe",
    "audio:generate_tts",
    "simulation:control",
}


class RedisBus:
    def __init__(self):
        self.redis: aioredis.Redis | None = None
        self.instance_id = INSTANCE_ID

    async def connect(self):
        self.redis = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=50,
        )
        await self.redis.ping()
        logger.info(f"Redis connected (instance: {self.instance_id})")

    async def close(self):
        if self.redis:
            await self.redis.aclose()

    # --- Streams (persistent) ---

    async def stream_add(self, stream: str, data: dict):
        await self.redis.xadd(stream, {"data": json.dumps(data)})

    async def stream_read_group(
        self,
        stream: str,
        group: str,
        consumer: str | None = None,
        count: int = 10,
        block: int = 5000,
    ) -> list[tuple[str, dict]]:
        consumer = consumer or f"{group}_{self.instance_id}"
        try:
            await self.redis.xgroup_create(stream, group, id="0", mkstream=True)
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

        messages = await self.redis.xreadgroup(
            groupname=group,
            consumername=consumer,
            streams={stream: ">"},
            count=count,
            block=block,
        )

        results = []
        for _stream_name, entries in messages:
            for entry_id, fields in entries:
                data = json.loads(fields["data"])
                results.append((entry_id, data))
        return results

    async def stream_ack(self, stream: str, group: str, entry_id: str):
        await self.redis.xack(stream, group, entry_id)

    # --- Pub/Sub (ephemeral) ---

    async def publish(self, channel: str, data: dict):
        if channel in STREAM_CHANNELS:
            await self.stream_add(channel, data)
        else:
            await self.redis.publish(channel, json.dumps(data))

    def pubsub(self) -> aioredis.client.PubSub:
        return self.redis.pubsub()

    # --- Rate limiting ---

    async def check_rate_limit(
        self, user_id: int, max_per_min: int = 20
    ) -> bool:
        """20 msgs/min por usuario (≈1 cada 3s). Solo previene loops
        accidentales de botones o bots; la participación humana normal
        no lo roza. Los tokens no son la limitante — el circuit breaker
        al LLM y el pool de DB son las verdaderas líneas de defensa."""
        key = f"ratelimit:{user_id}"
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, 60)
        return count <= max_per_min

    # --- Health check ---

    async def ping_agent(self, agent_name: str) -> bool:
        await self.redis.publish(f"{agent_name}:ping", json.dumps({"from": "orchestrator"}))
        # The pong is handled asynchronously by subscribers
        return True

    # --- Raw Redis access ---

    async def get(self, key: str) -> str | None:
        return await self.redis.get(key)

    async def setex(self, key: str, ttl: int, value: str):
        await self.redis.setex(key, ttl, value)

    @property
    def raw(self) -> aioredis.Redis:
        return self.redis
