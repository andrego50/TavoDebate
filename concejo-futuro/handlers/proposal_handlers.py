"""TavoDebate - Handlers de propuestas (/proponer, /apoyar, /propuestas_todas)."""

import json
import logging

from db.database import get_session

logger = logging.getLogger("handlers.proposals")


async def handle_proponer(agent, user_id: int, chat_id: int, args: str):
    """Registra una nueva propuesta de enmienda."""
    if not args or len(args.strip()) < 10:
        await agent._send_response(
            chat_id, "Uso: /proponer <tu propuesta de enmienda>\nMínimo 10 caracteres."
        )
        return

    texto = args.strip()
    if len(texto) > 500:
        await agent._send_response(chat_id, "La propuesta no puede exceder 500 caracteres.")
        return

    async with get_session() as session:
        from sqlalchemy import text as sql_text

        # Get user
        result = await session.execute(
            sql_text("SELECT * FROM users WHERE telegram_id = :tid"),
            {"tid": user_id},
        )
        user = result.mappings().first()
        if not user:
            await agent._send_response(chat_id, "Debes registrarte primero con /start")
            return

        # Classify article with LLM
        classify_prompt = (
            "Clasifica qué artículo del Proyecto SIADR afecta esta propuesta. "
            "Art 1: Creación SIADR. Art 2: Variables de priorización. "
            "Art 3: Financiación. Art 4: Transparencia. Art 5: Participación. "
            "Responde SOLO el número del artículo (1-5) o 'general'."
        )
        articulo = await agent.llm.generate(
            classify_prompt, texto, temperature=0.1, max_tokens=10
        )
        articulo = articulo.strip().replace("Art ", "").replace(".", "")[:10]

        # Generate summary
        resumen_text = await agent.llm.generate(
            "Resume esta propuesta de enmienda en máximo 50 palabras:", texto,
            temperature=0.3, max_tokens=100,
        )

        # Save proposal
        result = await session.execute(
            sql_text(
                "INSERT INTO proposals (user_id, telegram_id, nombre_concejal, municipio, "
                "provincia, bancada_id, bancada_nombre, articulo_afectado, texto_propuesta, resumen) "
                "VALUES (:uid, :tid, :name, :mun, :prov, :bid, :bname, :art, :text, :res) "
                "RETURNING id"
            ),
            {
                "uid": user["id"], "tid": user_id,
                "name": user["nombre_completo"], "mun": user["municipio"],
                "prov": user["provincia"], "bid": user["bancada_id"],
                "bname": user["bancada_nombre"], "art": articulo,
                "text": texto, "res": resumen_text[:200],
            },
        )
        proposal_id = result.scalar()

        # Update user count
        await session.execute(
            sql_text("UPDATE users SET propuestas_count = propuestas_count + 1 WHERE id = :uid"),
            {"uid": user["id"]},
        )

    await agent._send_response(
        chat_id,
        f"*Propuesta #{proposal_id} registrada*\n\n"
        f"Artículo afectado: {articulo}\n"
        f"Resumen: _{resumen_text[:200]}_\n\n"
        f"Los demás concejales pueden apoyarla con /apoyar {proposal_id}",
    )

    # Publish event
    await agent.bus.publish("proposal:new", {
        "id": proposal_id,
        "bancada_id": user["bancada_id"],
        "bancada_nombre": user["bancada_nombre"],
        "nombre_concejal": user["nombre_completo"],
        "articulo": articulo,
        "resumen": resumen_text[:200],
    })


async def handle_apoyar(agent, user_id: int, chat_id: int, args: str):
    """Apoya una propuesta existente."""
    try:
        proposal_id = int(args.strip())
    except (ValueError, AttributeError):
        await agent._send_response(chat_id, "Uso: /apoyar <número de propuesta>")
        return

    async with get_session() as session:
        from sqlalchemy import text as sql_text

        # Check proposal exists
        result = await session.execute(
            sql_text("SELECT * FROM proposals WHERE id = :pid"),
            {"pid": proposal_id},
        )
        proposal = result.mappings().first()
        if not proposal:
            await agent._send_response(chat_id, f"No existe la propuesta #{proposal_id}")
            return

        # Check not already supported
        apoyada_por = proposal.get("apoyada_por") or []
        if user_id in apoyada_por:
            await agent._send_response(chat_id, "Ya apoyaste esta propuesta.")
            return

        # Add support
        await session.execute(
            sql_text(
                "UPDATE proposals SET apoyos = apoyos + 1, "
                "apoyada_por = array_append(apoyada_por, :tid) "
                "WHERE id = :pid"
            ),
            {"tid": user_id, "pid": proposal_id},
        )

    await agent._send_response(
        chat_id,
        f"Apoyo registrado para propuesta #{proposal_id} "
        f"(ahora tiene {(proposal.get('apoyos', 1)) + 1} apoyos)",
    )


async def handle_propuestas_todas(agent, chat_id: int):
    """Lista todas las propuestas ordenadas por apoyos."""
    async with get_session() as session:
        from sqlalchemy import text as sql_text
        result = await session.execute(
            sql_text(
                "SELECT id, bancada_nombre, nombre_concejal, articulo_afectado, "
                "resumen, apoyos, estado FROM proposals ORDER BY apoyos DESC LIMIT 20"
            )
        )
        proposals = result.mappings().all()

    if not proposals:
        await agent._send_response(chat_id, "No hay propuestas registradas aún.")
        return

    msg = "*Propuestas de enmienda (por apoyos):*\n\n"
    for p in proposals:
        msg += (
            f"*#{p['id']}* [{p['bancada_nombre']}] — Art. {p['articulo_afectado']}\n"
            f"_{p['resumen']}_\n"
            f"Por: {p['nombre_concejal']} | Apoyos: {p['apoyos']} | Estado: {p['estado']}\n"
            f"/apoyar {p['id']}\n\n"
        )

    await agent._send_response(chat_id, msg)
