"""TavoDebate - Flujo /start en 4 pasos + /help."""

import json
import logging

from core.config import BANCADAS, PROVINCIAS_MUNICIPIOS, get_provincia_for_municipio, settings
from core.dossiers import get_dossier
from core.gabinete import format_power_map
from core.voices import get_voice_selection_text
from db.database import get_session

logger = logging.getLogger("handlers.onboarding")

CLASSIFY_INTERESTS_PROMPT = """Un concejal municipal de Cundinamarca describió sus intereses así:
"{texto_concejal}"

Clasifica en JSON (sin backticks):
{{"temas": ["lista de temas normalizados"], "keywords": ["palabras clave adicionales"], "resumen": "resumen en 1 línea"}}

Temas válidos (usa estos exactamente):
agro, derechos_humanos, turismo, seguridad, educacion, salud,
ambiente, infraestructura, mujer_genero, juventud, indigena_etnico,
comercio, tecnologia, hacienda, victimas, agua, vivienda,
cultura, deporte, adulto_mayor, discapacidad, paz,
transporte, mineria, emprendimiento

Máximo 5 temas, máximo 10 keywords."""

FASES = {
    "registro": {"nombre": "Registro", "bot_permite": ["start"]},
    "ponencia_alcalde": {"nombre": "Ponencia del Alcalde", "bot_permite": ["preguntar"]},
    "preguntas_alcalde": {"nombre": "Preguntas al Alcalde", "bot_permite": ["preguntar"]},
    "investigacion": {"nombre": "Investigación", "bot_permite": ["preguntar", "proponer"]},
    "debate": {"nombre": "Debate", "bot_permite": ["preguntar", "proponer", "grabar"]},
    "enmiendas": {"nombre": "Enmiendas", "bot_permite": ["proponer", "apoyar", "negociar"]},
    "votacion": {"nombre": "Votación", "bot_permite": ["votar"]},
    "debriefing": {"nombre": "Debriefing", "bot_permite": ["certificado"]},
}


async def handle_start(agent, user_id: int, chat_id: int, username: str, first_name: str):
    """Inicia el onboarding o muestra perfil si ya está registrado."""
    # Admin/dinamizador: skip onboarding entirely
    if user_id in settings.admin_ids:
        async with get_session() as session:
            from sqlalchemy import text as sql_text
            result = await session.execute(
                sql_text("SELECT * FROM users WHERE telegram_id = :tid"),
                {"tid": user_id},
            )
            user = result.mappings().first()
            if not user:
                await session.execute(
                    sql_text(
                        "INSERT INTO users (telegram_id, username, nombre_completo, municipio, "
                        "provincia, bancada_id, bancada_nombre, onboarding_step, onboarding_complete) "
                        "VALUES (:tid, :un, :name, 'Cundinamarca', 'Admin', 0, 'Dinamizador', "
                        "0, true) "
                        "ON CONFLICT (telegram_id) DO UPDATE SET onboarding_complete = true, "
                        "onboarding_step = 0"
                    ),
                    {"tid": user_id, "un": username or "", "name": first_name or "Admin"},
                )
            else:
                await session.execute(
                    sql_text(
                        "UPDATE users SET onboarding_complete = true, onboarding_step = 0 "
                        "WHERE telegram_id = :tid"
                    ),
                    {"tid": user_id},
                )

        msg = (
            "*Panel de Dinamizador — TavoDebate*\n\n"
            "Eres el administrador del ejercicio. Comandos disponibles:\n\n"
            "*Fases:*\n"
            "/fase registro — Abrir registro\n"
            "/fase ponencia\\_alcalde — Iniciar ponencia\n"
            "/fase debate — Abrir debate\n"
            "/fase votacion — Abrir votación\n\n"
            "*Control:*\n"
            "/broadcast <msg> — Mensaje a todos\n"
            "/bomba <msg> — Bomba informativa\n"
            "/fakenews <msg> — Fake news\n"
            "/ronda <min> — Timer de N minutos\n"
            "/tweet <texto> — Tweet simulado\n"
            "/alerta <msg> — Alerta visual\n\n"
            "*Info:*\n"
            "/estado — Stats del ejercicio\n"
            "/pin 1234 — Activar PIN de acceso\n"
            "/pin off — Desactivar PIN\n"
            "/llm deepseek|kimi — Cambiar LLM\n"
            "/briefing — Forzar briefing\n"
            "/help — Ayuda completa"
        )
        await agent._send_response(chat_id, msg)
        return

    async with get_session() as session:
        from sqlalchemy import text as sql_text
        result = await session.execute(
            sql_text("SELECT * FROM users WHERE telegram_id = :tid"),
            {"tid": user_id},
        )
        user = result.mappings().first()

    if user and user.get("onboarding_complete"):
        bancada = BANCADAS.get(user["bancada_id"], {})
        msg = (
            f"Ya estás registrado:\n\n"
            f"*{user['nombre_completo']}*\n"
            f"Concejal de {user['municipio']} ({user['provincia']})\n"
            f"Bancada: {bancada.get('nombre', '?')}\n"
            f"Voz activa: {user.get('active_voice', 'ciudadano')}\n\n"
            f"Usa /help para ver los comandos disponibles."
        )
        await agent._send_response(chat_id, msg)
        return

    # Check if access PIN is active
    import redis.asyncio as aioredis
    redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    pin = await redis.get("tavodebate:access_pin")
    await redis.aclose()

    if pin:
        # PIN is active — start at step 0 (PIN verification)
        start_step = 0
        msg = (
            "🏛️ *Bienvenido al Gran Concejo del Futuro — TavoDebate*\n\n"
            "Soy tu asistente de IA para la simulación legislativa sobre el "
            "proyecto SIADR de Cundinamarca.\n\n"
            "🔐 *Ingresa el código de acceso (4 dígitos):*"
        )
    else:
        # No PIN — go straight to step 1
        start_step = 1
        msg = (
            "🏛️ *Bienvenido al Gran Concejo del Futuro — TavoDebate*\n\n"
            "Soy tu asistente de IA para la simulación legislativa sobre el "
            "proyecto SIADR de Cundinamarca.\n\n"
            "*Paso 1 de 4:* ¿Cuál es tu nombre completo?"
        )

    # Create user record
    async with get_session() as session:
        from sqlalchemy import text as sql_text
        if not user:
            await session.execute(
                sql_text(
                    "INSERT INTO users (telegram_id, username, nombre_completo, municipio, "
                    "provincia, bancada_id, bancada_nombre, onboarding_step) "
                    "VALUES (:tid, :un, '', '', '', 1, '', :step) "
                    "ON CONFLICT (telegram_id) DO UPDATE SET onboarding_step = :step"
                ),
                {"tid": user_id, "un": username or "", "step": start_step},
            )
        else:
            await session.execute(
                sql_text("UPDATE users SET onboarding_step = :step WHERE telegram_id = :tid"),
                {"step": start_step, "tid": user_id},
            )

    await agent._send_response(chat_id, msg)


async def handle_onboard_callback(agent, user_id: int, chat_id: int, data: str, callback_id: str):
    """Procesa callbacks del onboarding."""
    parts = data.split("_", 2)
    if len(parts) < 3:
        return

    step = parts[1]

    if step == "prov":
        # User selected a provincia, show municipalities
        provincia = parts[2]
        municipios = PROVINCIAS_MUNICIPIOS.get(provincia, [])

        buttons = []
        for mun in municipios:
            buttons.append({"text": mun, "callback_data": f"onboard_mun_{provincia}|{mun}"})

        # Format as inline keyboard (2 per row)
        keyboard = []
        for i in range(0, len(buttons), 2):
            row = buttons[i:i+2]
            keyboard.append([{"text": b["text"], "callback_data": b["callback_data"]} for b in row])

        await agent.bus.stream_add("telegram:outgoing", {
            "chat_id": str(chat_id),
            "text": f"Municipios de {provincia}. Selecciona el tuyo:",
            "parse_mode": "Markdown",
            "reply_markup": json.dumps({"inline_keyboard": keyboard}),
        })

    elif step == "mun":
        # User selected municipality
        prov_mun = parts[2]
        provincia, municipio = prov_mun.split("|", 1)

        async with get_session() as session:
            from sqlalchemy import text as sql_text
            await session.execute(
                sql_text(
                    "UPDATE users SET municipio = :mun, provincia = :prov, "
                    "onboarding_step = 3 WHERE telegram_id = :tid"
                ),
                {"mun": municipio, "prov": provincia, "tid": user_id},
            )

        # Step 3: Show posición sobre el proyecto (3 opciones simples)
        keyboard = [
            [{"text": "✅ A FAVOR del proyecto", "callback_data": "onboard_ban_1"}],
            [{"text": "❌ EN CONTRA del proyecto", "callback_data": "onboard_ban_2"}],
            [{"text": "🤔 INDECISO / depende", "callback_data": "onboard_ban_4"}],
        ]

        await agent.bus.stream_add("telegram:outgoing", {
            "chat_id": str(chat_id),
            "text": (
                f"Registrado: *{municipio}* ({provincia})\n\n"
                "*Paso 3 de 4:* ¿Cuál es tu posición inicial sobre el "
                "Proyecto de Acuerdo 001-2026 (SIADR)?\n\n"
                "_Puedes cambiar de opinión durante el debate._"
            ),
            "parse_mode": "Markdown",
            "reply_markup": json.dumps({"inline_keyboard": keyboard}),
        })

    elif step == "ban":
        # User selected bancada
        bancada_id = int(parts[2])
        bancada = BANCADAS.get(bancada_id, BANCADAS[1])

        async with get_session() as session:
            from sqlalchemy import text as sql_text
            await session.execute(
                sql_text(
                    "UPDATE users SET bancada_id = :bid, bancada_nombre = :bname, "
                    "onboarding_step = 4 WHERE telegram_id = :tid"
                ),
                {"bid": bancada_id, "bname": bancada["nombre"], "tid": user_id},
            )

        posicion_label = {1: "✅ A FAVOR", 2: "❌ EN CONTRA", 4: "🤔 INDECISO"}.get(
            bancada_id, bancada["nombre"]
        )
        await agent._send_response(
            chat_id,
            f"Posición inicial: {posicion_label}\n\n"
            f"*Paso 4 de 4:* Cuéntame en tus propias palabras, "
            f"¿qué temas o causas defiendes como concejal? "
            f"¿Qué te apasiona de tu labor?\n\n"
            f"_Ejemplo: 'Yo trabajo por los campesinos de mi vereda, "
            f"la educación rural y el acceso a agua potable'_",
        )


async def process_onboarding_text(agent, user_id: int, chat_id: int, text: str):
    """Procesa texto libre durante onboarding (nombre o intereses)."""
    async with get_session() as session:
        from sqlalchemy import text as sql_text
        result = await session.execute(
            sql_text("SELECT onboarding_step FROM users WHERE telegram_id = :tid"),
            {"tid": user_id},
        )
        step = result.scalar()

    if step == 0:
        # Step 0: PIN verification
        import redis.asyncio as aioredis
        redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        pin = await redis.get("tavodebate:access_pin")
        await redis.aclose()

        if text.strip() == pin:
            # PIN correct — advance to step 1
            async with get_session() as session:
                from sqlalchemy import text as sql_text
                await session.execute(
                    sql_text("UPDATE users SET onboarding_step = 1 WHERE telegram_id = :tid"),
                    {"tid": user_id},
                )
            await agent._send_response(
                chat_id,
                "✅ Código correcto.\n\n*Paso 1 de 4:* ¿Cuál es tu nombre completo?"
            )
        else:
            await agent._send_response(
                chat_id,
                "❌ Código incorrecto. Intenta de nuevo (4 dígitos):"
            )
        return

    elif step == 1:
        # Step 1: Save name, show provinces
        nombre = text.strip()
        async with get_session() as session:
            from sqlalchemy import text as sql_text
            await session.execute(
                sql_text(
                    "UPDATE users SET nombre_completo = :name, onboarding_step = 2 "
                    "WHERE telegram_id = :tid"
                ),
                {"name": nombre, "tid": user_id},
            )

        # Show provinces as inline keyboard
        keyboard = []
        provincias = sorted(PROVINCIAS_MUNICIPIOS.keys())
        for i in range(0, len(provincias), 2):
            row = []
            for prov in provincias[i:i+2]:
                row.append({
                    "text": prov,
                    "callback_data": f"onboard_prov_{prov}",
                })
            keyboard.append(row)

        await agent.bus.stream_add("telegram:outgoing", {
            "chat_id": str(chat_id),
            "text": f"Hola *{nombre}*.\n\n*Paso 2 de 4:* Selecciona tu provincia:",
            "parse_mode": "Markdown",
            "reply_markup": json.dumps({"inline_keyboard": keyboard}),
        })

    elif step in (2, 3):
        # Steps 2 & 3 expect inline button callbacks, not text
        await agent._send_response(
            chat_id,
            "Por favor usa los botones de arriba para seleccionar tu opción. "
            "Si no los ves, envía /start para reiniciar el registro."
        )

    elif step == 4:
        # Step 4: Classify interests with LLM
        await agent._send_response(chat_id, "Clasificando tus intereses...")

        prompt = CLASSIFY_INTERESTS_PROMPT.format(texto_concejal=text)
        classification_text = await agent.llm.generate(
            prompt, "Clasifica.", temperature=0.3, max_tokens=300
        )

        try:
            parsed = json.loads(classification_text)
        except json.JSONDecodeError:
            parsed = {"temas": [], "keywords": [], "resumen": text[:200]}

        temas = parsed.get("temas", [])[:5]
        keywords = parsed.get("keywords", [])[:10]
        resumen = parsed.get("resumen", "")[:200]

        async with get_session() as session:
            from sqlalchemy import text as sql_text
            # Convert lists to PostgreSQL array literal format
            temas_pg = "{" + ",".join(temas) + "}" if temas else "{}"
            kw_pg = "{" + ",".join(keywords) + "}" if keywords else "{}"
            await session.execute(
                sql_text(
                    "UPDATE users SET intereses_raw = :raw, "
                    "temas_interes = CAST(:temas AS text[]), "
                    "intereses_keywords = CAST(:kw AS text[]), "
                    "intereses_resumen = :res, "
                    "onboarding_complete = true, onboarding_step = 0, "
                    "posicion_inicial = :pos "
                    "WHERE telegram_id = :tid"
                ),
                {
                    "raw": text,
                    "temas": temas_pg,
                    "kw": kw_pg,
                    "res": resumen,
                    "pos": "neutral",
                    "tid": user_id,
                },
            )

            # Get full user for completion message
            result = await session.execute(
                sql_text("SELECT * FROM users WHERE telegram_id = :tid"),
                {"tid": user_id},
            )
            user = result.mappings().first()

        if user:
            bancada = BANCADAS.get(user["bancada_id"], {})
            temas_display = ", ".join(temas) if temas else "Generales"

            msg = (
                f"*Registro completado*\n\n"
                f"*{user['nombre_completo']}*\n"
                f"Concejal de {user['municipio']} ({user['provincia']})\n"
                f"Bancada: {bancada.get('nombre', '?')}\n"
                f"Temas: {temas_display}\n"
                f"_{resumen}_\n\n"
                f"{get_voice_selection_text()}\n\n"
                f"Escribe cualquier pregunta para comenzar."
            )
            await agent._send_response(chat_id, msg)

            # Send dossier
            dossier = get_dossier(user["bancada_id"])
            await agent._send_response(chat_id, dossier)

            # Send power map
            power_map = format_power_map(
                user["bancada_id"],
                user.get("temas_interes", []) or [],
            )
            if power_map:
                await agent._send_response(chat_id, power_map)


async def handle_help(agent, chat_id: int):
    """Muestra comandos disponibles."""
    msg = (
        "🏛️ *TavoDebate — Comandos disponibles*\n\n"
        "*Voces (cambian cómo responde la IA):*\n"
        "🧑‍🌾 /ciudadano — Líder campesino\n"
        "🔬 /experto — Científico de datos\n"
        "📋 /contralor — Control fiscal\n"
        "🏢 /empresa — Empresa tech\n"
        "👔 /alcalde — Alcalde proponente\n\n"
        "*Preparación:*\n"
        "/preparar\\_ponencia — La IA te ayuda a armar tu ponencia\n"
        "/preparar\\_ponencia <ideas> — Incluye tus ideas\n\n"
        "*Participación:*\n"
        "/proponer — Proponer enmienda al proyecto\n"
        "/apoyar N — Apoyar propuesta #N\n"
        "/propuestas\\_todas — Ver todas las propuestas\n"
        "/negociar N — Negociar con bancada N\n"
        "/votar\\_proyecto — Votar el proyecto\n"
        "/votar\\_enmienda N — Votar enmienda N\n\n"
        "*Info:*\n"
        "/estado — Tu resumen personal\n"
        "/mi\\_certificado — Certificado PDF\n"
        "/help — Este mensaje\n\n"
        "_Escribe cualquier pregunta para consultar a la IA._"
    )
    await agent._send_response(chat_id, msg)
