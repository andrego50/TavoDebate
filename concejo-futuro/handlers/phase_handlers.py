"""TavoDebate - Handlers de fase y estado."""

import json
import logging

from core.config import BANCADAS
from db.database import get_session

logger = logging.getLogger("handlers.phase")


async def handle_estado(agent, user_id: int, chat_id: int):
    """Muestra el estado personal del concejal."""
    async with get_session() as session:
        from sqlalchemy import text as sql_text

        result = await session.execute(
            sql_text("SELECT * FROM users WHERE telegram_id = :tid"),
            {"tid": user_id},
        )
        user = result.mappings().first()
        if not user:
            await agent._send_response(chat_id, "No estás registrado. Usa /start")
            return

        # Count interactions
        result = await session.execute(
            sql_text("SELECT COUNT(*) FROM interactions WHERE user_id = :uid"),
            {"uid": user["id"]},
        )
        total_interactions = result.scalar() or 0

        # Count proposals
        result = await session.execute(
            sql_text("SELECT COUNT(*) FROM proposals WHERE user_id = :uid"),
            {"uid": user["id"]},
        )
        total_proposals = result.scalar() or 0

        # Check vote
        result = await session.execute(
            sql_text(
                "SELECT vote FROM votes WHERE telegram_id = :tid "
                "AND vote_type = 'proyecto' ORDER BY created_at DESC LIMIT 1"
            ),
            {"tid": user_id},
        )
        vote = result.scalar()

    bancada = BANCADAS.get(user["bancada_id"], {})
    temas = ", ".join(user.get("temas_interes", []) or []) or "No especificados"

    msg = (
        f"📊 *Tu estado — TavoDebate*\n\n"
        f"*{user['nombre_completo']}*\n"
        f"Concejal de {user['municipio']} ({user['provincia']})\n"
        f"Bancada: {bancada.get('nombre', '?')}\n"
        f"Voz activa: {user.get('active_voice', 'ciudadano')}\n"
        f"Temas: {temas}\n\n"
        f"*Métricas:*\n"
        f"Consultas realizadas: {total_interactions}\n"
        f"Propuestas presentadas: {total_proposals}\n"
        f"Voto proyecto: {vote or 'Pendiente'}\n"
    )

    await agent._send_response(chat_id, msg)
