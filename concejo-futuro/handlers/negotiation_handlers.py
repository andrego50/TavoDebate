"""TavoDebate - Handlers de negociación entre bancadas."""

import json
import logging
from datetime import datetime

from core.config import BANCADAS
from db.database import get_session

logger = logging.getLogger("handlers.negotiation")


async def handle_negociar(agent, user_id: int, chat_id: int, args: str):
    """Inicia negociación con otra bancada."""
    try:
        target_bancada = int(args.strip())
    except (ValueError, AttributeError):
        await agent._send_response(chat_id, "Uso: /negociar <número de bancada 1-6>")
        return

    if target_bancada not in BANCADAS:
        await agent._send_response(chat_id, "Bancada debe ser entre 1 y 6.")
        return

    async with get_session() as session:
        from sqlalchemy import text as sql_text

        # Get initiator
        result = await session.execute(
            sql_text("SELECT * FROM users WHERE telegram_id = :tid"),
            {"tid": user_id},
        )
        initiator = result.mappings().first()
        if not initiator:
            return

        if initiator["bancada_id"] == target_bancada:
            await agent._send_response(chat_id, "No puedes negociar con tu propia bancada.")
            return

        # Find "vocero" of target bancada (most active)
        result = await session.execute(
            sql_text(
                "SELECT telegram_id, nombre_completo FROM users "
                "WHERE bancada_id = :bid AND onboarding_complete = true "
                "ORDER BY total_queries DESC LIMIT 1"
            ),
            {"bid": target_bancada},
        )
        vocero = result.mappings().first()
        if not vocero:
            await agent._send_response(
                chat_id, f"No hay concejales registrados en {BANCADAS[target_bancada]['nombre']}."
            )
            return

        # Create negotiation
        result = await session.execute(
            sql_text(
                "INSERT INTO negotiations (bancada_a, bancada_b, iniciador_id, receptor_id) "
                "VALUES (:ba, :bb, :init, :recv) RETURNING id"
            ),
            {
                "ba": initiator["bancada_id"],
                "bb": target_bancada,
                "init": user_id,
                "recv": vocero["telegram_id"],
            },
        )
        neg_id = result.scalar()

    target_name = BANCADAS[target_bancada]["nombre"]
    await agent._send_response(
        chat_id,
        f"Solicitud de negociación enviada a {target_name}.\n"
        f"Vocero contactado: {vocero['nombre_completo']}\n"
        f"Negociación #{neg_id}",
    )

    # Notify vocero
    await agent.bus.stream_add("telegram:outgoing", {
        "chat_id": str(vocero["telegram_id"]),
        "text": (
            f"🤝 *Solicitud de negociación*\n\n"
            f"{initiator['nombre_completo']} ({BANCADAS[initiator['bancada_id']]['nombre']}) "
            f"solicita negociar contigo.\n\n"
            f"Negociación #{neg_id}\n"
            f"Usa /msg\\_negociacion {neg_id} <tu mensaje> para responder."
        ),
        "parse_mode": "Markdown",
    })

    # Notify admin
    await agent.bus.stream_add("telegram:outgoing", {
        "chat_id": str(agent.bus.redis and settings.admin_chat_id if hasattr(agent, 'bus') else ""),
        "text": (
            f"Negociación #{neg_id} abierta: "
            f"{BANCADAS[initiator['bancada_id']]['nombre']} ↔ {target_name}"
        ),
        "parse_mode": "Markdown",
    })
