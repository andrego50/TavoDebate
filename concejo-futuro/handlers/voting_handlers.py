"""TavoDebate - Handlers de votación."""

import json
import logging

from db.database import get_session

logger = logging.getLogger("handlers.voting")


async def handle_votar_proyecto(agent, user_id: int, chat_id: int, args: str):
    """Inicia votación del proyecto con botones inline."""
    async with get_session() as session:
        from sqlalchemy import text as sql_text

        # Check active session
        result = await session.execute(
            sql_text(
                "SELECT id FROM voting_sessions "
                "WHERE type = 'proyecto' AND is_open = true LIMIT 1"
            )
        )
        session_row = result.scalar()
        if not session_row:
            await agent._send_response(chat_id, "No hay sesión de votación del proyecto abierta.")
            return

    keyboard = json.dumps({
        "inline_keyboard": [
            [
                {"text": "A favor", "callback_data": f"vote_proyecto_si"},
                {"text": "En contra", "callback_data": f"vote_proyecto_no"},
                {"text": "Abstención", "callback_data": f"vote_proyecto_abstencion"},
            ]
        ]
    })

    await agent.bus.stream_add("telegram:outgoing", {
        "chat_id": str(chat_id),
        "text": "*Votación del Proyecto de Acuerdo 001-2026 (SIADR)*\n\nSelecciona tu voto:",
        "parse_mode": "Markdown",
        "reply_markup": keyboard,
    })


async def handle_votar_enmienda(agent, user_id: int, chat_id: int, args: str):
    """Inicia votación de una enmienda."""
    try:
        proposal_id = int(args.strip())
    except (ValueError, AttributeError):
        await agent._send_response(chat_id, "Uso: /votar\\_enmienda <número>")
        return

    keyboard = json.dumps({
        "inline_keyboard": [
            [
                {"text": "A favor", "callback_data": f"vote_enmienda_{proposal_id}_si"},
                {"text": "En contra", "callback_data": f"vote_enmienda_{proposal_id}_no"},
                {"text": "Abstención", "callback_data": f"vote_enmienda_{proposal_id}_abstencion"},
            ]
        ]
    })

    await agent.bus.stream_add("telegram:outgoing", {
        "chat_id": str(chat_id),
        "text": f"*Votación de enmienda #{proposal_id}*\n\nSelecciona tu voto:",
        "parse_mode": "Markdown",
        "reply_markup": keyboard,
    })


async def handle_vote_callback(agent, user_id: int, chat_id: int, data: str, callback_id: str):
    """Procesa el voto con confirmación de 2 pasos."""
    parts = data.split("_")
    # vote_proyecto_si or vote_enmienda_N_si or vote_confirm_...
    if len(parts) < 3:
        return

    if parts[1] == "confirm":
        # Second step: actually register the vote
        vote_type = parts[2]
        target_id = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else None
        vote_value = parts[-1]
        await _register_vote(agent, user_id, chat_id, vote_type, target_id, vote_value)
        return

    # First step: confirmation
    vote_type = parts[1]  # proyecto or enmienda
    if vote_type == "enmienda":
        target_id = parts[2]
        vote_value = parts[3]
    else:
        target_id = "0"
        vote_value = parts[2]

    vote_labels = {"si": "A FAVOR", "no": "EN CONTRA", "abstencion": "ABSTENCIÓN"}
    label = vote_labels.get(vote_value, vote_value)

    confirm_data = f"vote_confirm_{vote_type}_{target_id}_{vote_value}"
    cancel_data = f"vote_cancel"

    keyboard = json.dumps({
        "inline_keyboard": [
            [
                {"text": f"Confirmar: {label}", "callback_data": confirm_data},
                {"text": "Cancelar", "callback_data": cancel_data},
            ]
        ]
    })

    await agent.bus.stream_add("telegram:outgoing", {
        "chat_id": str(chat_id),
        "text": f"*Confirma tu voto: {label}*\n\n_Una vez confirmado no podrás cambiarlo._",
        "parse_mode": "Markdown",
        "reply_markup": keyboard,
    })


async def _register_vote(
    agent, user_id: int, chat_id: int,
    vote_type: str, target_id: int | None, vote_value: str
):
    """Registra el voto en la base de datos."""
    async with get_session() as session:
        from sqlalchemy import text as sql_text

        # Get user
        result = await session.execute(
            sql_text("SELECT * FROM users WHERE telegram_id = :tid"),
            {"tid": user_id},
        )
        user = result.mappings().first()
        if not user:
            await agent._send_response(chat_id, "Debes registrarte primero.")
            return

        # Check if already voted (allow change)
        result = await session.execute(
            sql_text(
                "SELECT id, vote FROM votes WHERE telegram_id = :tid "
                "AND vote_type = :vtype AND (target_id = :target OR (target_id IS NULL AND :target IS NULL))"
            ),
            {"tid": user_id, "vtype": vote_type, "target": target_id},
        )
        existing = result.mappings().first()

        if existing:
            # Update vote
            await session.execute(
                sql_text(
                    "UPDATE votes SET vote = :vote, changed_from = :old WHERE id = :vid"
                ),
                {"vote": vote_value, "old": existing["vote"], "vid": existing["id"]},
            )
            msg = f"Voto *actualizado*: {vote_value.upper()} (antes: {existing['vote']})"
        else:
            # Insert new vote
            await session.execute(
                sql_text(
                    "INSERT INTO votes (user_id, telegram_id, nombre_concejal, municipio, "
                    "bancada_id, vote_type, target_id, vote) "
                    "VALUES (:uid, :tid, :name, :mun, :bid, :vtype, :target, :vote)"
                ),
                {
                    "uid": user["id"], "tid": user_id,
                    "name": user["nombre_completo"], "mun": user["municipio"],
                    "bid": user["bancada_id"], "vtype": vote_type,
                    "target": target_id, "vote": vote_value,
                },
            )
            msg = f"Voto registrado: *{vote_value.upper()}*"

        # Update user
        if vote_type == "proyecto":
            await session.execute(
                sql_text("UPDATE users SET voto_proyecto = :vote WHERE telegram_id = :tid"),
                {"vote": vote_value, "tid": user_id},
            )

    await agent._send_response(chat_id, msg)

    # Publish vote event for pantalla
    await agent.bus.publish("vote:cast", {
        "user_id": user["id"],
        "telegram_id": user_id,
        "bancada_id": user["bancada_id"],
        "municipio": user["municipio"],
        "vote_type": vote_type,
        "target_id": target_id,
        "vote": vote_value,
    })
