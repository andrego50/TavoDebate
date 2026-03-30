"""TavoDebate - Handlers de fase y estado."""

import json
import logging

from core.config import BANCADAS, settings
from db.database import get_session

logger = logging.getLogger("handlers.phase")


async def handle_estado(agent, user_id: int, chat_id: int):
    """Muestra el estado del concejal o panel de dinamizador."""
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

        # Admin/dinamizador: show exercise-level stats
        if user_id in settings.admin_ids:
            total_users = (await session.execute(
                sql_text("SELECT COUNT(*) FROM users WHERE onboarding_complete = true")
            )).scalar() or 0

            total_interactions = (await session.execute(
                sql_text("SELECT COUNT(*) FROM interactions")
            )).scalar() or 0

            total_proposals = (await session.execute(
                sql_text("SELECT COUNT(*) FROM proposals")
            )).scalar() or 0

            total_votes = (await session.execute(
                sql_text("SELECT COUNT(*) FROM votes WHERE vote_type = 'proyecto'")
            )).scalar() or 0

            # Bancada breakdown
            bancada_counts = (await session.execute(
                sql_text(
                    "SELECT bancada_nombre, COUNT(*) as c FROM users "
                    "WHERE onboarding_complete = true AND bancada_nombre != '' "
                    "GROUP BY bancada_nombre ORDER BY c DESC"
                )
            )).mappings().all()

            bancada_lines = "\n".join(
                f"  {r['bancada_nombre']}: {r['c']}" for r in bancada_counts
            ) or "  Sin concejales registrados"

            # Get current phase from Redis
            phase = await agent.bus.get("current_phase") or "registro"

            msg = (
                f"🎛️ *Panel de Dinamizador — TavoDebate*\n\n"
                f"*Fase actual:* {phase}\n\n"
                f"*Concejales registrados:* {total_users}\n"
                f"*Interacciones totales:* {total_interactions}\n"
                f"*Propuestas presentadas:* {total_proposals}\n"
                f"*Votos emitidos:* {total_votes}\n\n"
                f"*Por bancada:*\n{bancada_lines}\n\n"
                f"Usa /fase <nombre> para cambiar la fase.\n"
                f"Usa /broadcast <msg> para enviar mensaje a todos."
            )
            await agent._send_response(chat_id, msg)
            return

        # Regular concejal view
        total_interactions = (await session.execute(
            sql_text("SELECT COUNT(*) FROM interactions WHERE user_id = :uid"),
            {"uid": user["id"]},
        )).scalar() or 0

        total_proposals = (await session.execute(
            sql_text("SELECT COUNT(*) FROM proposals WHERE user_id = :uid"),
            {"uid": user["id"]},
        )).scalar() or 0

        vote = (await session.execute(
            sql_text(
                "SELECT vote FROM votes WHERE telegram_id = :tid "
                "AND vote_type = 'proyecto' ORDER BY created_at DESC LIMIT 1"
            ),
            {"tid": user_id},
        )).scalar()

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


async def get_participants_summary() -> str:
    """Genera resumen de participantes registrados para el admin."""
    async with get_session() as session:
        from sqlalchemy import text as sql_text

        total = (await session.execute(
            sql_text(
                "SELECT COUNT(*) FROM users "
                "WHERE onboarding_complete = true AND bancada_nombre != 'Dinamizador'"
            )
        )).scalar() or 0

        # By bancada
        bancadas = (await session.execute(
            sql_text(
                "SELECT bancada_nombre, COUNT(*) as c FROM users "
                "WHERE onboarding_complete = true AND bancada_nombre != '' AND bancada_nombre != 'Dinamizador' "
                "GROUP BY bancada_nombre ORDER BY c DESC"
            )
        )).mappings().all()

        # By provincia (top 5)
        provincias = (await session.execute(
            sql_text(
                "SELECT provincia, COUNT(*) as c FROM users "
                "WHERE onboarding_complete = true AND provincia != '' AND provincia != 'Admin' "
                "GROUP BY provincia ORDER BY c DESC LIMIT 5"
            )
        )).mappings().all()

        # Recent registrations (last 5)
        recientes = (await session.execute(
            sql_text(
                "SELECT nombre_completo, municipio, bancada_nombre FROM users "
                "WHERE onboarding_complete = true AND bancada_nombre != 'Dinamizador' "
                "ORDER BY created_at DESC LIMIT 5"
            )
        )).mappings().all()

    bancada_lines = "\n".join(
        f"  {r['bancada_nombre']}: {r['c']} concejales" for r in bancadas
    ) or "  Ninguno aún"

    prov_lines = "\n".join(
        f"  {r['provincia']}: {r['c']}" for r in provincias
    ) or "  —"

    recientes_lines = "\n".join(
        f"  • {r['nombre_completo']} ({r['municipio']}) — {r['bancada_nombre']}"
        for r in recientes
    ) or "  Ninguno aún"

    return (
        f"📋 *Resumen de participantes*\n\n"
        f"*Total registrados:* {total}\n\n"
        f"*Por bancada:*\n{bancada_lines}\n\n"
        f"*Top provincias:*\n{prov_lines}\n\n"
        f"*Últimos registros:*\n{recientes_lines}"
    )
