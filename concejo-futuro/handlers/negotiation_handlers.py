"""TavoDebate - Handlers de negociación entre bancadas."""

import json
import logging
from datetime import datetime

from core.config import BANCADAS, settings
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
        "chat_id": str(settings.admin_chat_id),
        "text": (
            f"Negociación #{neg_id} abierta: "
            f"{BANCADAS[initiator['bancada_id']]['nombre']} ↔ {target_name}"
        ),
        "parse_mode": "Markdown",
    })


async def handle_msg_negociacion(agent, user_id: int, chat_id: int, args: str):
    """Envía mensaje a la contraparte de una negociación."""
    parts = (args or "").strip().split(" ", 1)
    if len(parts) < 2 or not parts[0].isdigit():
        await agent._send_response(chat_id, "Uso: /msg_negociacion <número> <mensaje>")
        return

    neg_id = int(parts[0])
    msg_text = parts[1].strip()
    if not msg_text:
        await agent._send_response(chat_id, "El mensaje no puede estar vacío.")
        return

    async with get_session() as session:
        from sqlalchemy import text as sql_text

        result = await session.execute(
            sql_text("SELECT * FROM negotiations WHERE id = :nid"),
            {"nid": neg_id},
        )
        neg = result.mappings().first()
        if not neg:
            await agent._send_response(chat_id, f"No existe la negociación #{neg_id}.")
            return

        # Determine who the counterpart is
        if user_id == neg["iniciador_id"]:
            counterpart_id = neg["receptor_id"]
        elif user_id == neg["receptor_id"]:
            counterpart_id = neg["iniciador_id"]
        else:
            await agent._send_response(chat_id, "No participas en esa negociación.")
            return

        # Fetch sender info
        result = await session.execute(
            sql_text("SELECT nombre_completo, bancada_id FROM users WHERE telegram_id = :tid"),
            {"tid": user_id},
        )
        sender = result.mappings().first()
        sender_name = sender["nombre_completo"] if sender else str(user_id)
        bancada_name = BANCADAS.get(sender["bancada_id"], {}).get("nombre", "?") if sender else "?"

        # Log message in DB
        await session.execute(
            sql_text(
                "INSERT INTO negotiation_messages (negotiation_id, sender_id, message) "
                "VALUES (:nid, :sid, :msg)"
            ),
            {"nid": neg_id, "sid": user_id, "msg": msg_text},
        )

    await agent._send_response(chat_id, f"Mensaje enviado a la contraparte (Neg. #{neg_id}).")

    await agent.bus.stream_add("telegram:outgoing", {
        "chat_id": str(counterpart_id),
        "text": (
            f"📩 *Mensaje de negociación #{neg_id}*\n\n"
            f"De: {sender_name} ({bancada_name})\n\n"
            f"{msg_text}\n\n"
            f"Responde con /msg_negociacion {neg_id} <tu respuesta>"
        ),
        "parse_mode": "Markdown",
    })
