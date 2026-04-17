"""TavoDebate - Rúbrica de uso de IA por participante.

Calcula un puntaje 0-100 en seis dimensiones (frecuencia, diversidad de
asesores consultados, profundidad de preguntas, uso de evidencia,
adaptación en el debate y productividad) y le entrega al participante un
feedback con comentario cualitativo generado por Tavo.
"""

import logging
import re

from db.database import get_session

logger = logging.getLogger("handlers.feedback")


FEEDBACK_SYSTEM = (
    "Eres Tavo, jefe de gabinete del participante en el Concejo del "
    "Futuro. Escribe un comentario cualitativo breve (máx 70 palabras) "
    "sobre su desempeño, basado ESTRICTAMENTE en las métricas entregadas "
    "y la muestra de preguntas que hizo. Destaca una fortaleza específica "
    "y una oportunidad concreta de mejora. Tono directo, segunda persona. "
    "Sin saludos, sin firma, sin emojis."
)


WEIGHTS = {
    "frecuencia": 10,
    "diversidad": 15,
    "profundidad": 20,
    "evidencia": 20,
    "adaptacion": 15,
    "productividad": 20,
}


DIM_LABEL = {
    "frecuencia": "Frecuencia",
    "diversidad": "Diversidad",
    "profundidad": "Profundidad",
    "evidencia": "Evidencia",
    "adaptacion": "Adaptación",
    "productividad": "Productividad",
}


EVIDENCE_PAT = re.compile(
    r"(\d+\s*%|\bley\s*\d+|art[\.\s]*\d+|conpes|sentencia|\$\s*\d|\d+\s*(millones|billones)|\bdane\b|\bdnp\b|\bigac\b)",
    re.IGNORECASE,
)


async def handle_mi_feedback(agent, user_id: int, chat_id: int):
    """Calcula y entrega la rúbrica de uso de IA del participante."""
    from sqlalchemy import text as sql_text

    async with get_session() as session:
        result = await session.execute(
            sql_text("SELECT * FROM users WHERE telegram_id = :tid"),
            {"tid": user_id},
        )
        user = result.mappings().first()

    if not user:
        await agent._send_response(chat_id, "Debes registrarte primero con /start.")
        return

    await agent._send_response(chat_id, "🎓 Tavo está evaluando tu desempeño...")

    scores, sample = await _compute_scores(user_id, user["id"])
    total = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS) / 100
    total = int(round(total))

    if total >= 85:
        label = "🌟 Excelente"
    elif total >= 70:
        label = "✅ Muy bueno"
    elif total >= 55:
        label = "👍 Aceptable"
    elif total >= 40:
        label = "📚 Por mejorar"
    else:
        label = "⚠️ Participación mínima"

    comentario = await _generate_comment(agent, user, scores, sample)

    def bar(v: int) -> str:
        v = max(0, min(100, v))
        filled = v // 10
        return "█" * filled + "░" * (10 - filled)

    nombre = user.get("nombre_completo", "Participante")
    rol = (user.get("rol") or "concejal").replace("_", " ").title()

    rows = "\n".join(
        f"{DIM_LABEL[k]:<15} {bar(scores[k])}  {scores[k]:>3}"
        for k in WEIGHTS
    )

    msg = (
        f"🎓 *Tu rúbrica de uso de IA*\n"
        f"_{nombre} — {rol}_\n\n"
        f"📊 Puntaje total: *{total}/100* — {label}\n\n"
        f"```\n{rows}\n```\n\n"
        f"📝 *Comentario de Tavo:*\n"
        f"_{comentario}_"
    )
    await agent._send_response(chat_id, msg)


async def _compute_scores(telegram_id: int, db_user_id: int) -> tuple[dict, dict]:
    """Calcula los 6 puntajes y devuelve también muestra para el LLM."""
    from sqlalchemy import text as sql_text

    async with get_session() as session:
        # Total interacciones del user
        my_count = (await session.execute(
            sql_text("SELECT COUNT(*) FROM interactions WHERE user_id = :uid"),
            {"uid": db_user_id},
        )).scalar() or 0

        # Mediana de interacciones del grupo
        mediana = (await session.execute(sql_text(
            "SELECT COALESCE(percentile_cont(0.5) WITHIN GROUP (ORDER BY n), 1) "
            "FROM (SELECT COUNT(*) as n FROM interactions GROUP BY user_id) t"
        ))).scalar() or 1

        # Asesores distintos
        asesores_distintos = (await session.execute(sql_text(
            "SELECT COUNT(DISTINCT advisor_used) FROM interactions "
            "WHERE user_id = :uid AND advisor_used IS NOT NULL"
        ), {"uid": db_user_id})).scalar() or 0

        # Muestra de preguntas
        result = await session.execute(sql_text(
            "SELECT question FROM interactions WHERE user_id = :uid "
            "ORDER BY created_at DESC LIMIT 8"
        ), {"uid": db_user_id})
        preguntas = [r[0] or "" for r in result.fetchall()]

        # Enmiendas propuestas
        result = await session.execute(sql_text(
            "SELECT resumen, apoyos FROM proposals WHERE telegram_id = :tid"
        ), {"tid": telegram_id})
        enmiendas = [(r[0] or "", r[1] or 0) for r in result.fetchall()]

        # Cambios de sentiment (adaptación)
        result = await session.execute(sql_text(
            "SELECT sentiment FROM interactions "
            "WHERE user_id = :uid AND sentiment IS NOT NULL "
            "ORDER BY created_at"
        ), {"uid": db_user_id})
        sentiments = [r[0] for r in result.fetchall()]

        # position_strength evolución
        result = await session.execute(sql_text(
            "SELECT position_strength FROM interactions "
            "WHERE user_id = :uid AND position_strength IS NOT NULL "
            "ORDER BY created_at"
        ), {"uid": db_user_id})
        strengths = [r[0] for r in result.fetchall()]

        # Votos
        votos = (await session.execute(sql_text(
            "SELECT COUNT(*) FROM votes WHERE user_id = :uid"
        ), {"uid": db_user_id})).scalar() or 0

        # key_argument de interacciones
        result = await session.execute(sql_text(
            "SELECT key_argument FROM interactions "
            "WHERE user_id = :uid AND key_argument IS NOT NULL"
        ), {"uid": db_user_id})
        key_args = [r[0] or "" for r in result.fetchall()]

    # --- Cálculos ---
    # 1. Frecuencia — vs mediana (2× mediana = 100)
    frecuencia = int(min(100, my_count / max(mediana, 1) * 50))

    # 2. Diversidad — 10 asesores = 100
    diversidad = int(min(100, asesores_distintos * 10))

    # 3. Profundidad — avg longitud + proporción con contexto
    if preguntas:
        avg_len = sum(len(q) for q in preguntas) / len(preguntas)
        con_contexto = sum(1 for q in preguntas if len(q) > 80) / len(preguntas)
        profundidad = int(min(100, avg_len / 200 * 50 + con_contexto * 50))
    else:
        profundidad = 0

    # 4. Evidencia — % de textos (enmiendas + key_args) con cifras/leyes
    texts = [e[0] for e in enmiendas] + key_args
    texts = [t for t in texts if t]
    if texts:
        with_ev = sum(1 for t in texts if EVIDENCE_PAT.search(t))
        evidencia = int(with_ev / len(texts) * 100)
    else:
        evidencia = 0

    # 5. Adaptación — cambios fundamentados + crecimiento de firmeza
    cambios = sum(1 for i in range(1, len(sentiments)) if sentiments[i] != sentiments[i-1])
    growth = 0
    if len(strengths) >= 2:
        growth = max(0, strengths[-1] - strengths[0])
    adaptacion = int(min(100, cambios * 25 + growth * 15))

    # 6. Productividad — enmiendas + votos + apoyos recibidos
    apoyos_recibidos = sum(e[1] for e in enmiendas)
    productividad = int(min(
        100, len(enmiendas) * 25 + votos * 10 + apoyos_recibidos * 5
    ))

    scores = {
        "frecuencia": frecuencia,
        "diversidad": diversidad,
        "profundidad": profundidad,
        "evidencia": evidencia,
        "adaptacion": adaptacion,
        "productividad": productividad,
    }
    sample = {
        "preguntas": preguntas[:3],
        "enmiendas": [e[0] for e in enmiendas[:3]],
        "interacciones_totales": my_count,
        "asesores_distintos": asesores_distintos,
        "votos_emitidos": votos,
    }
    return scores, sample


async def _generate_comment(agent, user: dict, scores: dict, sample: dict) -> str:
    """Comentario cualitativo con Tavo (LLM)."""
    top = max(scores, key=scores.get)
    bottom = min(scores, key=scores.get)

    preguntas_txt = "\n".join(f"- {q[:160]}" for q in sample["preguntas"]) or "(sin preguntas registradas)"
    enmiendas_txt = "\n".join(f"- {e[:160]}" for e in sample["enmiendas"]) or "(ninguna)"

    context = (
        f"Participante: {user.get('nombre_completo', '')}\n"
        f"Rol: {user.get('rol', 'concejal')}\n"
        f"Bancada: {user.get('bancada_nombre', '?')}\n\n"
        f"Puntajes:\n"
        f"- Frecuencia: {scores['frecuencia']}/100\n"
        f"- Diversidad de asesores: {scores['diversidad']}/100 "
        f"({sample['asesores_distintos']} de 10 consultados)\n"
        f"- Profundidad de preguntas: {scores['profundidad']}/100\n"
        f"- Uso de evidencia: {scores['evidencia']}/100\n"
        f"- Adaptación en el debate: {scores['adaptacion']}/100\n"
        f"- Productividad: {scores['productividad']}/100\n\n"
        f"Dimensión más fuerte: {top} ({scores[top]})\n"
        f"Dimensión más débil: {bottom} ({scores[bottom]})\n\n"
        f"Muestra de preguntas recientes:\n{preguntas_txt}\n\n"
        f"Enmiendas presentadas:\n{enmiendas_txt}\n\n"
        f"Total interacciones: {sample['interacciones_totales']}\n"
        f"Votos emitidos: {sample['votos_emitidos']}\n\n"
        "Redacta el comentario (máx 70 palabras)."
    )
    try:
        comment = await agent.llm.generate(
            FEEDBACK_SYSTEM, context, temperature=0.5,
            max_tokens=200, use_cache=False,
        )
        return comment.strip()
    except Exception as e:
        logger.error(f"Feedback comment failed: {e}")
        return (
            f"Tu mayor fortaleza fue {DIM_LABEL[top]} "
            f"({scores[top]}); tu oportunidad está en {DIM_LABEL[bottom]} "
            f"({scores[bottom]})."
        )
