"""TavoDebate - Comandos exclusivos del Presidente del Concejo.

- /votacion_articulos : abre votaciones secuenciales por artículo
- /cerrar_articulo    : cierra manualmente la votación del artículo en curso
- /compilar_acuerdo   : Tavo redacta el texto final con artículos y enmiendas aprobadas
- /proclamar_acuerdo  : (vía botón) difunde el texto firmado como Presidente
"""

import json
import logging

from core.articulado import ARTICULOS, PROYECTO_ID, PROYECTO_TITULO, get_articulo
from db.database import get_session

logger = logging.getLogger("handlers.presidencia")


ARTICULO_TIMER_MIN = 3  # minutos por artículo


async def _load_user(user_id: int) -> dict | None:
    from sqlalchemy import text as sql_text
    async with get_session() as session:
        result = await session.execute(
            sql_text("SELECT * FROM users WHERE telegram_id = :tid"),
            {"tid": user_id},
        )
        return result.mappings().first()


def _is_presidente(user: dict | None) -> bool:
    if not user:
        return False
    rol = (user.get("rol") or "").lower()
    return rol == "presidente_concejo"


async def handle_votacion_articulos(agent, user_id: int, chat_id: int):
    """Abre la votación del Artículo 1. Los siguientes se abren
    automáticamente al cerrarse el anterior (simulation_agent)."""
    user = await _load_user(user_id)
    from core.config import settings
    if not _is_presidente(user) and user_id not in settings.admin_ids:
        await agent._send_response(
            chat_id,
            "Este comando es del Presidente del Concejo (o del dinamizador)."
        )
        return

    from sqlalchemy import text as sql_text
    async with get_session() as session:
        # Close any existing open articulo sessions
        await session.execute(sql_text(
            "UPDATE voting_sessions SET is_open = false, closed_at = NOW() "
            "WHERE is_open = true AND type LIKE 'articulo%'"
        ))

    await _open_articulo_vote(agent, 1, chat_id)


async def _open_articulo_vote(agent, numero: int, notify_chat_id: int | None):
    """Abre la voting_session del artículo N y notifica a todos los participantes."""
    art = get_articulo(numero)
    if not art:
        logger.warning(f"Artículo {numero} no existe")
        return

    from sqlalchemy import text as sql_text
    async with get_session() as session:
        await session.execute(
            sql_text(
                "INSERT INTO voting_sessions (type, target_id, description, is_open) "
                "VALUES ('articulo', :n, :desc, true)"
            ),
            {
                "n": numero,
                "desc": f"Art. {numero} — {art['titulo']}",
            },
        )

        # Get all concejales for notification
        result = await session.execute(sql_text(
            "SELECT telegram_id FROM users WHERE onboarding_complete = true "
            "AND COALESCE(rol, 'concejal') IN ('concejal', 'presidente_concejo')"
        ))
        tids = [row[0] for row in result.fetchall()]

    total = len(ARTICULOS)
    msg = (
        f"🗳️ *Votación — Artículo {numero} de {total}*\n\n"
        f"*{art['titulo']}*\n\n"
        f"_{art['texto']}_\n\n"
        f"Votá con:\n"
        f"• `/votar_articulo {numero} a_favor`\n"
        f"• `/votar_articulo {numero} en_contra`\n"
        f"• `/votar_articulo {numero} abstencion`\n\n"
        f"Tienes {ARTICULO_TIMER_MIN} minutos."
    )
    for tid in tids:
        await agent.bus.stream_add("telegram:outgoing", {
            "chat_id": str(tid),
            "text": msg,
            "parse_mode": "Markdown",
        })

    # Start timer in simulation_agent (named "votacion_articulo" so the
    # close handler knows to open the next one)
    await agent.bus.publish("simulation:command", {
        "action": "start_timer",
        "args": {
            "name": f"votacion_articulo_{numero}",
            "minutes": ARTICULO_TIMER_MIN,
        },
    })

    if notify_chat_id:
        await agent.bus.stream_add("telegram:outgoing", {
            "chat_id": str(notify_chat_id),
            "text": (
                f"✅ Votación del Art. {numero} abierta. "
                f"Timer {ARTICULO_TIMER_MIN} min. "
                f"Se enviará notificación a {len(tids)} concejales."
            ),
            "parse_mode": "Markdown",
        })


async def handle_votar_articulo(agent, user_id: int, chat_id: int, args: str):
    """Registra el voto de un concejal sobre un artículo específico."""
    parts = (args or "").strip().split()
    if len(parts) < 2:
        await agent._send_response(
            chat_id,
            "Uso: `/votar_articulo <N> a_favor | en_contra | abstencion`"
        )
        return
    try:
        numero = int(parts[0])
    except ValueError:
        await agent._send_response(chat_id, "Número de artículo inválido.")
        return

    vote_map = {
        "a_favor": "si", "si": "si", "favor": "si",
        "en_contra": "no", "no": "no", "contra": "no",
        "abstencion": "abstencion", "abstención": "abstencion",
    }
    vote = vote_map.get(parts[1].lower())
    if not vote:
        await agent._send_response(
            chat_id, "Voto inválido. Usa: a_favor / en_contra / abstencion"
        )
        return

    # Only concejales & presidente can vote
    user = await _load_user(user_id)
    rol = (user or {}).get("rol") or "concejal"
    if rol not in ("concejal", "presidente_concejo"):
        await agent._send_response(
            chat_id, "Tu rol no tiene voto en el Concejo."
        )
        return

    from sqlalchemy import text as sql_text
    async with get_session() as session:
        result = await session.execute(sql_text(
            "SELECT id FROM voting_sessions WHERE type = 'articulo' "
            "AND target_id = :n AND is_open = true ORDER BY id DESC LIMIT 1"
        ), {"n": numero})
        session_id = result.scalar()
        if not session_id:
            await agent._send_response(
                chat_id,
                f"La votación del Art. {numero} no está abierta."
            )
            return

        # Upsert-style: if already voted, update; else insert
        result = await session.execute(sql_text(
            "SELECT id, vote FROM votes WHERE telegram_id = :tid "
            "AND vote_type = 'articulo' AND target_id = :n"
        ), {"tid": user_id, "n": numero})
        existing = result.mappings().first()
        if existing:
            await session.execute(sql_text(
                "UPDATE votes SET vote = :v, changed_from = :old WHERE id = :vid"
            ), {"v": vote, "old": existing["vote"], "vid": existing["id"]})
            msg = f"Voto *actualizado* Art. {numero}: {vote.upper()}"
        else:
            await session.execute(sql_text(
                "INSERT INTO votes (user_id, telegram_id, nombre_concejal, "
                "municipio, bancada_id, vote_type, target_id, vote) "
                "VALUES (:uid, :tid, :nm, :mun, :bid, 'articulo', :tg, :v)"
            ), {
                "uid": user["id"], "tid": user_id,
                "nm": user.get("nombre_completo", ""),
                "mun": user.get("municipio", ""),
                "bid": user.get("bancada_id"),
                "tg": numero, "v": vote,
            })
            msg = f"Voto registrado Art. {numero}: *{vote.upper()}*"

    await agent._send_response(chat_id, msg)
    await agent.bus.publish("vote:cast", {
        "telegram_id": user_id,
        "bancada_id": user.get("bancada_id"),
        "municipio": user.get("municipio"),
        "vote_type": "articulo",
        "target_id": numero,
        "vote": vote,
    })


async def handle_compilar_acuerdo(agent, user_id: int, chat_id: int):
    """Pide a Tavo que redacte el texto final del acuerdo con los
    artículos APROBADOS y las enmiendas con apoyos.
    Muestra preview con botones "✅ Oficializar / 🔄 Regenerar / ❌ Cancelar"."""
    user = await _load_user(user_id)
    from core.config import settings
    if not _is_presidente(user) and user_id not in settings.admin_ids:
        await agent._send_response(
            chat_id,
            "Solo el Presidente del Concejo (o el dinamizador) puede compilar el acuerdo."
        )
        return

    await agent._send_response(
        chat_id, "📜 Tavo está redactando el texto final del acuerdo..."
    )

    from sqlalchemy import text as sql_text
    async with get_session() as session:
        # Artículo-level results
        result = await session.execute(sql_text(
            "SELECT target_id, results FROM voting_sessions "
            "WHERE type = 'articulo' AND results IS NOT NULL "
            "ORDER BY target_id"
        ))
        rows = list(result.mappings())
        # Enmiendas con apoyos
        result = await session.execute(sql_text(
            "SELECT id, resumen, apoyos, articulo, nombre_concejal "
            "FROM proposals ORDER BY apoyos DESC, id"
        ))
        enmiendas = list(result.mappings())

    if not rows:
        await agent._send_response(
            chat_id,
            "Aún no hay votaciones cerradas por artículo. "
            "Abre el flujo con `/votacion_articulos`."
        )
        return

    # Build structured compilation for LLM
    results_summary = []
    for r in rows:
        res = r["results"]
        if isinstance(res, str):
            res = json.loads(res)
        art = get_articulo(r["target_id"]) or {"numero": r["target_id"], "titulo": "?", "texto": "?"}
        results_summary.append({
            "numero": art["numero"],
            "titulo": art["titulo"],
            "texto_original": art["texto"],
            "aprobado": res.get("aprobado", False),
            "si": res.get("si", 0),
            "no": res.get("no", 0),
            "abs": res.get("abstencion", 0),
        })

    enmiendas_text = "\n".join(
        f"- Art. {e.get('articulo', '?')}: {e['resumen']} "
        f"(apoyos: {e.get('apoyos', 0)}, autor: {e.get('nombre_concejal', '')})"
        for e in enmiendas
    ) or "Sin enmiendas presentadas."

    art_block = "\n".join(
        f"Art. {r['numero']} — {r['titulo']}\n"
        f"Original: {r['texto_original']}\n"
        f"Resultado: {'APROBADO' if r['aprobado'] else 'RECHAZADO'} "
        f"({r['si']}sí / {r['no']}no / {r['abs']}abs)"
        for r in results_summary
    )

    system = (
        "Eres Tavo, jefe de gabinete del Presidente del Concejo. Redacta "
        "el TEXTO FINAL del Proyecto de Acuerdo integrando:\n"
        "1) Los artículos APROBADOS (mantén su numeración original).\n"
        "2) Las enmiendas con mayor apoyo (intégralas al artículo "
        "correspondiente, reescribiéndolo).\n"
        "3) NO incluyas artículos rechazados; renumera si es necesario.\n"
        "4) Usa lenguaje jurídico institucional ('El Concejo Municipal de "
        "... acuerda...').\n"
        "5) Al final incluye una sección 'Resultados de la votación por "
        "artículo'.\n\n"
        f"Título del proyecto: {PROYECTO_TITULO}"
    )
    user_msg = (
        f"Articulado y resultados:\n\n{art_block}\n\n"
        f"Enmiendas presentadas:\n{enmiendas_text}\n\n"
        "Redacta el texto final del acuerdo."
    )
    try:
        final_text = await agent.llm.generate(
            system, user_msg, temperature=0.5, max_tokens=1800, use_cache=False,
        )
    except Exception as e:
        logger.error(f"Compile failed: {e}")
        await agent._send_response(
            chat_id, f"Error al compilar el acuerdo: {e}"
        )
        return

    # Store for later "oficializar"
    await agent.bus.raw.setex(
        f"acuerdo_borrador:{user_id}", 1800, final_text,
    )

    keyboard = json.dumps({"inline_keyboard": [
        [
            {"text": "✅ Oficializar y difundir", "callback_data": "presi_oficializar"},
            {"text": "🔄 Regenerar", "callback_data": "presi_regenerar"},
        ],
        [{"text": "❌ Cancelar", "callback_data": "cancel_action"}],
    ]})
    preview = (
        f"📜 *Borrador del acuerdo final — compilado por Tavo*\n"
        f"_{PROYECTO_TITULO}_\n\n"
        f"{final_text[:3500]}\n\n"
        "_Revísalo. Al oficializar se enviará a todos los participantes "
        "firmado por ti como Presidente._"
    )
    await agent.bus.stream_add("telegram:outgoing", {
        "chat_id": str(chat_id),
        "text": preview,
        "parse_mode": "Markdown",
        "reply_markup": keyboard,
    })


async def handle_oficializar(agent, user_id: int, chat_id: int):
    """Difunde el texto del acuerdo firmado por el Presidente."""
    user = await _load_user(user_id)
    from core.config import settings
    if not _is_presidente(user) and user_id not in settings.admin_ids:
        await agent._send_response(
            chat_id, "Solo el Presidente del Concejo puede oficializar."
        )
        return

    raw = await agent.bus.raw.get(f"acuerdo_borrador:{user_id}")
    if not raw:
        await agent._send_response(
            chat_id,
            "No hay borrador activo. Usa /compilar_acuerdo para armarlo."
        )
        return
    if isinstance(raw, bytes):
        raw = raw.decode()

    presidente = user.get("nombre_completo", "Presidente del Concejo")

    from sqlalchemy import text as sql_text
    async with get_session() as session:
        result = await session.execute(sql_text(
            "SELECT telegram_id FROM users WHERE onboarding_complete = true"
        ))
        tids = [row[0] for row in result.fetchall()]

    announcement = (
        f"📜 *EL PRESIDENTE DEL CONCEJO COMUNICA*\n\n"
        f"Tras la deliberación y votación por artículos del "
        f"_{PROYECTO_TITULO}_, se promulga el siguiente texto final:\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{raw}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"_Firmado: {presidente} — Presidente del Concejo_"
    )

    for tid in tids:
        await agent.bus.stream_add("telegram:outgoing", {
            "chat_id": str(tid),
            "text": announcement,
            "parse_mode": "Markdown",
        })
    # Clear draft
    await agent.bus.raw.delete(f"acuerdo_borrador:{user_id}")
    await agent.bus.publish("broadcast:sent", {
        "message": "El Presidente del Concejo promulgó el acuerdo final.",
        "target": "all",
        "reach": len(tids),
    })
    await agent._send_response(
        chat_id,
        f"✅ Acuerdo oficializado y enviado a *{len(tids)}* participantes."
    )


async def handle_regenerar(agent, user_id: int, chat_id: int):
    """Vuelve a compilar el acuerdo."""
    await handle_compilar_acuerdo(agent, user_id, chat_id)
