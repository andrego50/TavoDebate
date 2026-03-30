"""TavoDebate - Agente Control (brazo ejecutor de Andrés)."""

import asyncio
import json
import logging
from datetime import datetime

from agents.base_agent import BaseAgent
from core.config import settings
from db.database import get_session

logger = logging.getLogger("agent.control")


class ControlAgent(BaseAgent):
    name = "control"

    async def start(self):
        """Escucha comandos, briefings y propuestas."""
        pubsub = self.bus.pubsub()
        await pubsub.subscribe(
            "control:command",
            "briefing:new",
            "proposal:proactive",
        )

        logger.info("Control agent listening for commands")
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                channel = message["channel"]
                if isinstance(channel, bytes):
                    channel = channel.decode()
                data = json.loads(message["data"])

                if channel == "briefing:new":
                    await self._forward_briefing(data)
                elif channel == "proposal:proactive":
                    await self._handle_proposals(data)
                elif channel == "control:command":
                    await self._execute_command(data)
            except Exception as e:
                logger.error(f"Control agent error: {e}", exc_info=True)

    async def _forward_briefing(self, data: dict):
        """Envía briefing a Andrés por Telegram."""
        await self.bus.stream_add("telegram:outgoing", {
            "chat_id": settings.admin_chat_id,
            "text": data["text"],
            "parse_mode": "Markdown",
        })

    async def _handle_proposals(self, data: dict):
        """Envía propuestas proactivas a Andrés para aprobación."""
        proposals = data.get("proposals", [])
        for i, proposal in enumerate(proposals):
            text = (
                f"💡 *Propuesta #{i+1}*\n"
                f"Tipo: {proposal.get('type', '?')}\n"
                f"Target: {proposal.get('target', 'all')}\n"
                f"Mensaje: {proposal.get('message', '')}\n"
                f"Razón: {proposal.get('reason', '')}\n\n"
                f"¿Aprobar? /aprobar_{i} o /rechazar_{i}"
            )
            await self.bus.stream_add("telegram:outgoing", {
                "chat_id": settings.admin_chat_id,
                "text": text,
                "parse_mode": "Markdown",
            })

    async def _execute_command(self, data: dict):
        """Ejecuta un comando del orquestador."""
        action = data.get("action")
        args = data.get("args", {})

        handlers = {
            "broadcast": self._execute_broadcast,
            "bomb": self._execute_bomb,
            "fakenews": self._execute_fakenews,
            "pressure": self._execute_pressure,
            "gabinete": self._execute_gabinete,
            "alert": self._execute_alert,
        }

        handler = handlers.get(action)
        if handler:
            await handler(args)
        else:
            logger.warning(f"Unknown control action: {action}")

    async def _execute_broadcast(self, args: dict):
        """Envía broadcast a concejales."""
        message = args.get("message", "")
        target = args.get("target", "all")
        with_audio = args.get("with_audio", False)

        users = await self._get_target_users(target)

        for user in users:
            await self.bus.stream_add("telegram:outgoing", {
                "chat_id": str(user["telegram_id"]),
                "text": f"📢 *COMUNICADO*\n\n{message}",
                "parse_mode": "Markdown",
            })

        if with_audio:
            await self.bus.publish("audio:generate_tts", {
                "text": message,
                "voice": "broadcast",
                "send_to": [u["telegram_id"] for u in users],
            })

        await self.bus.publish("broadcast:sent", {
            "message": message,
            "target": target,
            "reach": len(users),
            "timestamp": datetime.now().isoformat(),
        })

        # Log admin action
        async with get_session() as session:
            from sqlalchemy import text as sql_text
            await session.execute(
                sql_text(
                    "INSERT INTO admin_actions (action_type, parameters, executed_by) "
                    "VALUES ('broadcast', :params, :admin)"
                ),
                {"params": json.dumps(args), "admin": "admin"},
            )

        logger.info(f"Broadcast sent to {len(users)} users (target: {target})")

    async def _execute_bomb(self, args: dict):
        """Envía dato bomba."""
        bomb_id = args.get("bomb_id", 1)
        target = args.get("target", "all")

        from core.bombs import BOMBS
        bomb = BOMBS.get(bomb_id)
        if not bomb:
            logger.warning(f"Bomb {bomb_id} not found")
            return

        users = await self._get_target_users(target)
        for user in users:
            await self.bus.stream_add("telegram:outgoing", {
                "chat_id": str(user["telegram_id"]),
                "text": f"🔴 *DATO BOMBA*\n\n{bomb['text']}",
                "parse_mode": "Markdown",
            })

        await self.bus.publish("bomb:sent", {
            "bomb_id": bomb_id,
            "text": bomb["text"],
            "target": target,
            "reach": len(users),
            "timestamp": datetime.now().isoformat(),
        })

        # Auto-publish reaction tweets
        from core.tweets import BOMB_TWEETS
        for tweet in BOMB_TWEETS.get(bomb_id, []):
            await asyncio.sleep(2)
            await self.bus.publish("tweet:new", {
                "author": tweet["author"],
                "text": tweet["text"],
                "is_reaction": True,
            })

    async def _execute_fakenews(self, args: dict):
        """Envía fake news."""
        news_id = args.get("news_id", 1)
        target = args.get("target", "all")

        from core.fakenews import FAKE_NEWS
        news = FAKE_NEWS.get(news_id)
        if not news:
            return

        users = await self._get_target_users(target)
        for user in users:
            await self.bus.stream_add("telegram:outgoing", {
                "chat_id": str(user["telegram_id"]),
                "text": f"📰 *ÚLTIMA HORA*\n\n{news['text']}",
                "parse_mode": "Markdown",
            })

        await self.bus.publish("fakenews:sent", {
            "news_id": news_id,
            "text": news["text"],
            "target": target,
            "reach": len(users),
            "is_fake": news.get("is_fake", True),
            "timestamp": datetime.now().isoformat(),
        })

        # Auto-publish reaction tweets
        from core.tweets import FAKENEWS_TWEETS
        for tweet in FAKENEWS_TWEETS.get(news_id, []):
            await asyncio.sleep(2)
            await self.bus.publish("tweet:new", {
                "author": tweet["author"],
                "text": tweet["text"],
                "is_reaction": True,
            })

    async def _execute_pressure(self, args: dict):
        """Ejecuta presión estructurada."""
        pressure_type = args.get("type", "tema_msg")
        target = args.get("target", "all")
        message = args.get("message", "")

        users = await self._get_target_users(target)
        for user in users:
            await self.bus.stream_add("telegram:outgoing", {
                "chat_id": str(user["telegram_id"]),
                "text": f"⚠️ *PRESIÓN*\n\n{message}",
                "parse_mode": "Markdown",
            })

        await self.bus.publish("pressure:sent", {
            "type": pressure_type,
            "message": message,
            "target": target,
            "reach": len(users),
            "timestamp": datetime.now().isoformat(),
        })

    async def _execute_gabinete(self, args: dict):
        """Maneja eventos del gabinete."""
        action = args.get("gabinete_action", "")
        await self.bus.publish("gabinete:event", {
            "action": action,
            "details": args,
            "timestamp": datetime.now().isoformat(),
        })

    async def _execute_alert(self, args: dict):
        """Genera y envía alerta visual."""
        alert_type = args.get("alert_type", "defensoria")
        message = args.get("message", "")

        await self.bus.publish("alert:sent", {
            "type": alert_type,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        })

    async def _get_target_users(self, target: str) -> list[dict]:
        """Obtiene lista de usuarios según el target."""
        async with get_session() as session:
            from sqlalchemy import text as sql_text
            if target == "all":
                result = await session.execute(
                    sql_text("SELECT telegram_id FROM users WHERE onboarding_complete = true")
                )
            elif target.startswith("bancada_"):
                bancada_id = int(target.replace("bancada_", ""))
                result = await session.execute(
                    sql_text(
                        "SELECT telegram_id FROM users "
                        "WHERE bancada_id = :bid AND onboarding_complete = true"
                    ),
                    {"bid": bancada_id},
                )
            else:
                result = await session.execute(
                    sql_text("SELECT telegram_id FROM users WHERE onboarding_complete = true")
                )
            return [dict(r) for r in result.mappings()]
