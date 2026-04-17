"""TavoDebate - Construcción del system prompt con memoria adaptativa."""

import json

from core.config import BANCADAS, ROLES
from core.voices import PROMPT_BASE, get_voice_prompt

# Extra instructions per role group
ROLE_INSTRUCTIONS = {
    "gobierno": (
        "Tu participante es parte del EQUIPO DE GOBIERNO que defiende el proyecto SIADR. "
        "Ayúdale a construir argumentos sólidos A FAVOR del proyecto. "
        "Puede pedirte que redactes comunicados, tweets de defensa, respuestas a críticas, "
        "o datos que fortalezcan la ponencia. Actúa como su asesor estratégico."
    ),
    "sociedad_civil": (
        "Tu participante representa a la SOCIEDAD CIVIL. "
        "Ayúdale a formular preguntas incisivas, denuncias, exigencias y propuestas desde su perspectiva comunitaria. "
        "Puede pedirte que redactes tweets, comunicados de prensa, o argumentos para presionar a los concejales."
    ),
    "empresa": (
        "Tu participante representa al SECTOR PRIVADO/EMPRESARIAL. "
        "Ayúdale a defender intereses empresariales, presentar beneficios económicos, "
        "o responder a acusaciones de conflicto de interés. Puede pedirte tweets o comunicados."
    ),
    "control": (
        "Tu participante es un ÓRGANO DE CONTROL (Contraloría, Personería, Veeduría). "
        "Ayúdale a formular alertas, advertencias legales, exigencias de transparencia "
        "y fiscalización. Sé riguroso con datos y normatividad."
    ),
    "concejo": (
        "Tu participante es un CONCEJAL que votará el proyecto. "
        "Ayúdale a investigar, preparar su ponencia, formular preguntas y tomar una decisión informada."
    ),
}


async def build_system_prompt(user: dict, session=None, advisor_key: str = None) -> str:
    """Construye el system prompt personalizado para un participante."""
    bancada_id = user.get("bancada_id", 1)
    bancada = BANCADAS.get(bancada_id, BANCADAS[1])
    voice = user.get("active_voice", "ciudadano")
    rol_key = user.get("rol", "concejal") or "concejal"
    rol_info = ROLES.get(rol_key, ROLES["concejal"])

    # Build base prompt with user context
    base = PROMPT_BASE.format(
        nombre_concejal=user.get("nombre_completo", "Participante"),
        municipio=user.get("municipio", "Desconocido"),
        provincia=user.get("provincia", "Desconocida"),
        bancada_nombre=bancada["nombre"],
        bancada_posicion=bancada["posicion"],
        intereses_resumen=user.get("intereses_resumen", "No especificados"),
        temas_interes=", ".join(user.get("temas_interes", []) or []),
    )

    # Add role context
    role_section = (
        f"\n--- ROL EN EL EJERCICIO ---\n"
        f"Rol: {rol_info['nombre']}\n"
        f"Descripción: {rol_info['descripcion']}\n"
        f"{'Puede votar el proyecto.' if rol_info['puede_votar'] else 'NO vota, pero participa activamente en el debate.'}\n"
        f"\n{ROLE_INSTRUCTIONS.get(rol_info.get('grupo', 'concejo'), '')}"
    )

    # Add voice prompt
    voice_prompt = get_voice_prompt(voice)

    # Add live context if available
    live_context = ""
    if session:
        live_context = await _get_live_context(user, bancada_id, session)

    # Add advisor section
    advisor_section = ""
    if advisor_key:
        from core.advisors import get_advisor_prompt
        advisor_prompt = get_advisor_prompt(advisor_key)
        advisor_section = (
            f"\n\n--- ASESOR ACTIVO ---\n{advisor_prompt}\n\n"
            "BÚSQUEDA WEB: Si necesitas información actualizada para responder, "
            "puedes solicitar una búsqueda escribiendo en tu respuesta:\n"
            "<<<BUSCAR>>>tu consulta aquí<<<FIN_BUSCAR>>>\n"
            "Se te proporcionarán los resultados y podrás usarlos para dar una respuesta mejor fundamentada."
        )

    return f"{base}{role_section}\n\n--- VOZ ACTIVA ---\n{voice_prompt}{advisor_section}\n\n{live_context}"


async def _get_live_context(user: dict, bancada_id: int, session) -> str:
    """Obtiene contexto en vivo del debate para que el asesor nunca hable a ciegas."""
    from sqlalchemy import text as sql_text

    parts = []

    # --- REAL-TIME SIGNALS (from Redis pub/sub cache) ---
    try:
        import redis.asyncio as aioredis
        from core.config import settings
        r = aioredis.from_url(settings.redis_url, decode_responses=True)

        # Current phase
        phase = await r.get("current_phase")
        if phase:
            parts.append(f"--- FASE ACTUAL ---\n{phase}")

        # Last open voting session
        last_vote_res = await session.execute(
            sql_text(
                "SELECT description, is_open, results FROM voting_sessions "
                "ORDER BY id DESC LIMIT 1"
            )
        )
        lv = last_vote_res.mappings().first()
        if lv:
            if lv["is_open"]:
                parts.append(
                    f"--- VOTACIÓN EN CURSO ---\n{lv['description']}"
                )
            elif lv["results"]:
                res = lv["results"] if isinstance(lv["results"], dict) else json.loads(lv["results"])
                parts.append(
                    f"--- ÚLTIMA VOTACIÓN ---\n"
                    f"{res.get('resultado', '?')} — "
                    f"sí {res.get('si', 0)} / no {res.get('no', 0)} / abs {res.get('abstencion', 0)}"
                )

        # Recent tweets (last 6) — already JSON-serialized in chat_agent
        raw_tweets = await r.lrange("tavodebate:recent_tweets", 0, 5)
        tweets = []
        for raw in raw_tweets:
            try:
                t = json.loads(raw)
                author = t.get("author", "?")
                text = (t.get("text", "") or "")[:140].replace("\n", " ")
                tid = t.get("tweet_id", "?")
                marker = ""
                if t.get("reply_to_id"):
                    marker = f" ↪#{t['reply_to_id']}"
                elif t.get("quote_to_id"):
                    marker = f" 🔁#{t['quote_to_id']}"
                tweets.append(f"#{tid} {author}{marker}: {text}")
            except Exception:
                continue
        if tweets:
            parts.append("--- TUITS RECIENTES EN PANTALLA ---\n" + "\n".join(tweets))

        # Recent pantalla events: bombs, fakenews, alerts, pressure (last 15)
        # pantalla_agent persists these to tavodebate:pantalla_history
        raw_hist = await r.lrange("tavodebate:pantalla_history", -20, -1)
        relevant_channels = {
            "bomb:sent": "💣 BOMBA",
            "fakenews:sent": "📰 FAKE NEWS",
            "alert:sent": "🚨 ALERTA",
            "pressure:sent": "📣 PRESIÓN",
            "broadcast:sent": "📢 COMUNICADO",
        }
        news_lines = []
        for raw in raw_hist:
            try:
                ev = json.loads(raw)
                ch = ev.get("channel", "")
                if ch not in relevant_channels:
                    continue
                data = ev.get("data", {}) or {}
                msg = (
                    data.get("message") or data.get("text") or
                    data.get("title") or data.get("description") or ""
                )
                msg = msg[:180].replace("\n", " ")
                if msg:
                    news_lines.append(f"{relevant_channels[ch]}: {msg}")
            except Exception:
                continue
        if news_lines:
            parts.append(
                "--- EVENTOS RECIENTES EN EL DEBATE ---\n"
                + "\n".join(news_lines[-8:])
            )

        await r.aclose()
    except Exception:
        pass

    # --- PERSISTED DEBATE STATE (DB) ---
    try:
        result = await session.execute(
            sql_text("SELECT global_summary, temperature, hottest_topic FROM debate_state WHERE id = 1")
        )
        state = result.mappings().first()
        if state and state["global_summary"] != "El debate aún no ha comenzado.":
            parts.append(
                f"--- ESTADO DEL DEBATE ---\n"
                f"Resumen: {state['global_summary']}\n"
                f"Temperatura: {state['temperature']}\n"
                f"Tema más caliente: {state['hottest_topic']}"
            )
    except Exception:
        pass

    try:
        result = await session.execute(
            sql_text("SELECT summary FROM bancada_state WHERE bancada_id = :bid"),
            {"bid": bancada_id},
        )
        bancada_state = result.scalar()
        if bancada_state and bancada_state != "Sin actividad aún.":
            parts.append(f"--- ESTADO DE TU BANCADA ---\n{bancada_state}")
    except Exception:
        pass

    # --- PERSISTENT USER MEMORY: rolling summary + last Q&A ---
    try:
        summary = user.get("session_summary")
        if summary:
            parts.append(f"--- RESUMEN DE TU SESIÓN PREVIA ---\n{summary}")
    except Exception:
        pass

    try:
        uid = user.get("id")
        result = await session.execute(
            sql_text(
                "SELECT question, response, voice_used, advisor_used "
                "FROM interactions WHERE user_id = :uid "
                "ORDER BY created_at DESC LIMIT 5"
            ),
            {"uid": uid},
        )
        recent = list(result.mappings())
        if recent:
            qa_lines = []
            for iv in reversed(recent):
                q = (iv["question"] or "")[:200].replace("\n", " ")
                r = (iv["response"] or "")[:260].replace("\n", " ")
                tag = iv.get("advisor_used") or iv.get("voice_used") or ""
                qa_lines.append(f"[{tag}] Tú preguntaste: {q}\nAsesor: {r}")
            parts.append(
                "--- ÚLTIMAS CONSULTAS DE ESTE PARTICIPANTE ---\n"
                "(el equipo YA le contestó esto; apóyate en lo anterior)\n\n"
                + "\n\n".join(qa_lines)
            )
    except Exception:
        pass

    try:
        result = await session.execute(
            sql_text(
                "SELECT COUNT(*) FROM interactions "
                "WHERE user_id = :uid AND created_at > NOW() - INTERVAL '30 minutes'"
            ),
            {"uid": user.get("id")},
        )
        recent_count = result.scalar() or 0
        if recent_count > 0:
            parts.append(f"Este participante ha hecho {recent_count} consultas en los últimos 30 minutos.")
    except Exception:
        pass

    if parts:
        preamble = (
            "INSTRUCCIÓN: El siguiente bloque es el ESTADO EN TIEMPO REAL del "
            "debate. Antes de responder, léelo y haz referencia explícita a "
            "cualquier tuit, bomba, fake news, alerta o votación relevante. "
            "NUNCA respondas como si no estuvieras al tanto de lo que acaba "
            "de pasar."
        )
        return preamble + "\n\n" + "\n\n".join(parts)
    return ""
