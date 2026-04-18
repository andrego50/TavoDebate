"""TavoDebate - Flujo /start en 4 pasos + /help."""

import json
import logging

from core.config import BANCADAS, PROVINCIAS_MUNICIPIOS, ROLES, get_provincia_for_municipio, settings
from core.dossiers import get_dossier
from core.gabinete import format_power_map
from core.voices import get_voice_selection_text
from db.database import get_session

logger = logging.getLogger("handlers.onboarding")

# Grupos de alto nivel para elegir rol en onboarding (step 2).
# Los concejales son los únicos que eligen bancada (a favor/contra/indeciso).
# Los demás obtienen bancada automática según su grupo.
GRUPOS_ONBOARDING = {
    "concejo": {
        "label": "🏛️ Concejo",
        "roles": ["concejal", "presidente_concejo"],
    },
    "gobierno": {
        "label": "👔 Gobierno / Alcaldía",
        "roles": ["alcalde", "sec_planeacion", "sec_hacienda",
                  "sec_agricultura", "dir_tic", "dir_umata"],
        "bancada_auto": 1,  # Gobierno
    },
    "sociedad_civil": {
        "label": "🧑‍🌾 Sociedad civil",
        "roles": ["lider_campesino", "lider_indigena", "lider_jac",
                  "ambientalista", "periodista"],
        "bancada_auto": 3,  # Rural
    },
    "empresa": {
        "label": "🏢 Empresa / Gremio",
        "roles": ["empresa_tech", "gremio_agro"],
        "bancada_auto": 4,  # Urbana/Pragmáticos
    },
    "control": {
        "label": "⚖️ Control / Veeduría",
        "roles": ["contralor", "personero", "veedor"],
        "bancada_auto": 5,  # Presupuesto/Fiscalización
    },
}


async def _count_titulares(rol_key: str, exclude_tid: int | None = None) -> int:
    """Cuántos usuarios activos ya tienen este rol."""
    from sqlalchemy import text as sql_text
    async with get_session() as session:
        if exclude_tid is not None:
            result = await session.execute(
                sql_text(
                    "SELECT COUNT(*) FROM users WHERE rol = :rol "
                    "AND onboarding_complete = true AND telegram_id != :tid"
                ),
                {"rol": rol_key, "tid": exclude_tid},
            )
        else:
            result = await session.execute(
                sql_text(
                    "SELECT COUNT(*) FROM users WHERE rol = :rol "
                    "AND onboarding_complete = true"
                ),
                {"rol": rol_key},
            )
    return result.scalar() or 0


async def _show_roles_menu(agent, user_id: int, chat_id: int, grupo: dict):
    """Muestra los sub-roles del grupo, marcando los que ya llegaron a su
    cupo máximo (max_titulares) como «(cupo lleno)» y deshabilitados."""
    async with get_session() as session:
        from sqlalchemy import text as sql_text
        await session.execute(
            sql_text(
                "UPDATE users SET onboarding_step = 3 WHERE telegram_id = :tid"
            ),
            {"tid": user_id},
        )

    keyboard = []
    for rk in grupo["roles"]:
        rol_info = ROLES[rk]
        max_t = rol_info.get("max_titulares")
        ocupados = 0
        if max_t is not None:
            ocupados = await _count_titulares(rk, exclude_tid=user_id)

        if max_t is not None and ocupados >= max_t:
            # Cupo lleno → botón deshabilitado (callback sin acción)
            label = f"🔒 {rol_info['nombre']} — cupo lleno ({ocupados}/{max_t})"
            keyboard.append([{"text": label, "callback_data": "cancel_action"}])
        elif max_t is not None:
            label = f"{rol_info['nombre']} ({ocupados}/{max_t})"
            keyboard.append([{"text": label, "callback_data": f"onboard_rol_{rk}"}])
        else:
            keyboard.append([{
                "text": rol_info["nombre"],
                "callback_data": f"onboard_rol_{rk}",
            }])

    await agent.bus.stream_add("telegram:outgoing", {
        "chat_id": str(chat_id),
        "text": (
            f"Grupo: *{grupo['label']}*\n\n"
            f"*Paso 2b:* Selecciona tu rol específico.\n"
            f"_Los roles con 🔒 están con cupo lleno._"
        ),
        "parse_mode": "Markdown",
        "reply_markup": json.dumps({"inline_keyboard": keyboard}),
    })


async def _show_provincias(agent, chat_id: int):
    """Muestra el selector de provincias (paso 3 del nuevo flujo)."""
    keyboard = []
    provincias = sorted(PROVINCIAS_MUNICIPIOS.keys())
    for i in range(0, len(provincias), 2):
        row = [
            {"text": p, "callback_data": f"onboard_prov_{p}"}
            for p in provincias[i:i+2]
        ]
        keyboard.append(row)

    await agent.bus.stream_add("telegram:outgoing", {
        "chat_id": str(chat_id),
        "text": "*Paso 3 de 5:* Selecciona tu provincia:",
        "parse_mode": "Markdown",
        "reply_markup": json.dumps({"inline_keyboard": keyboard}),
    })


def _bancada_auto_for_rol(rol_key: str) -> int:
    """Devuelve la bancada automática para un rol no-concejal."""
    for grupo in GRUPOS_ONBOARDING.values():
        if rol_key in grupo["roles"] and "bancada_auto" in grupo:
            return grupo["bancada_auto"]
    return 1  # fallback


# Temas predefinidos para selección determinista en onboarding (single-select)
# key → (emoji + label para botón, lista de temas canónicos, resumen)
TEMAS_ONBOARDING = {
    "agro": {
        "label": "🌾 Agro y desarrollo rural",
        "temas": ["agro", "agua"],
        "resumen": "Defensa de campesinos, agricultura y desarrollo rural.",
    },
    "infra": {
        "label": "💡 Infraestructura y alumbrado",
        "temas": ["infraestructura", "transporte"],
        "resumen": "Obras públicas, alumbrado rural y vías.",
    },
    "tec": {
        "label": "💻 Tecnología e innovación",
        "temas": ["tecnologia", "emprendimiento"],
        "resumen": "Modernización, IoT y gobierno digital.",
    },
    "hacienda": {
        "label": "💰 Presupuesto y hacienda",
        "temas": ["hacienda"],
        "resumen": "Fiscalización presupuestal y uso de regalías.",
    },
    "ambiente": {
        "label": "🌱 Medio ambiente y agua",
        "temas": ["ambiente", "agua"],
        "resumen": "Protección ambiental y acceso a agua potable.",
    },
    "educacion": {
        "label": "📚 Educación y juventud",
        "temas": ["educacion", "juventud"],
        "resumen": "Educación rural, juventud y formación.",
    },
    "salud": {
        "label": "🏥 Salud y derechos",
        "temas": ["salud", "derechos_humanos"],
        "resumen": "Salud pública y derechos de poblaciones vulnerables.",
    },
    "seguridad": {
        "label": "🛡️ Seguridad y transparencia",
        "temas": ["seguridad"],
        "resumen": "Seguridad rural y control a la corrupción.",
    },
}

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
            "*Paso 1 de 5:* ¿Cuál es tu nombre completo?"
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

    if step == "grupo":
        grupo_key = parts[2]
        grupo = GRUPOS_ONBOARDING.get(grupo_key)
        if not grupo:
            return

        await _show_roles_menu(agent, user_id, chat_id, grupo)

    elif step == "rol":
        rol_key = parts[2]
        if rol_key not in ROLES:
            return

        # Verifica si el usuario ya tenía un rol asignado (para liberar
        # su cupo anterior si cambia) y si ya ocupaba el mismo rol
        # (re-selección idempotente).
        async with get_session() as session:
            from sqlalchemy import text as sql_text
            result = await session.execute(
                sql_text("SELECT rol FROM users WHERE telegram_id = :tid"),
                {"tid": user_id},
            )
            rol_previo = result.scalar()

        max_titulares = ROLES[rol_key].get("max_titulares")
        # Atomic claim del cupo en Redis (solo si el rol tiene límite y
        # es un cambio real). INCR en Redis es atómico — dos usuarios
        # simultáneos NUNCA obtienen el mismo número.
        if max_titulares is not None and rol_previo != rol_key:
            claimed = await agent.bus.claim_role_slot(rol_key, max_titulares)
            if not claimed:
                rol_info = ROLES[rol_key]
                grupo_key = rol_info.get("grupo")
                grupo = next(
                    (g for k, g in GRUPOS_ONBOARDING.items() if k == grupo_key),
                    None,
                )
                await agent._send_response(
                    chat_id,
                    f"⚠️ El cupo de *{rol_info['nombre']}* se acaba de "
                    f"llenar (máx {max_titulares}). Elige otro rol."
                )
                if grupo:
                    await _show_roles_menu(agent, user_id, chat_id, grupo)
                return

        # Libera el cupo del rol anterior si era un rol con cupo
        if (rol_previo
                and rol_previo != rol_key
                and rol_previo in ROLES
                and ROLES[rol_previo].get("max_titulares") is not None):
            await agent.bus.release_role_slot(rol_previo)

        async with get_session() as session:
            from sqlalchemy import text as sql_text
            await session.execute(
                sql_text(
                    "UPDATE users SET rol = :rol, onboarding_step = 4 "
                    "WHERE telegram_id = :tid"
                ),
                {"rol": rol_key, "tid": user_id},
            )
        await _show_provincias(agent, chat_id)

    elif step == "prov":
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
            result = await session.execute(
                sql_text("SELECT rol FROM users WHERE telegram_id = :tid"),
                {"tid": user_id},
            )
            rol = (result.scalar() or "concejal")

            if rol == "concejal":
                await session.execute(
                    sql_text(
                        "UPDATE users SET municipio = :mun, provincia = :prov, "
                        "onboarding_step = 5 WHERE telegram_id = :tid"
                    ),
                    {"mun": municipio, "prov": provincia, "tid": user_id},
                )
            else:
                # No-concejal: asignar bancada automática y saltar al paso de causa
                bid = _bancada_auto_for_rol(rol)
                bancada = BANCADAS.get(bid, BANCADAS[1])
                await session.execute(
                    sql_text(
                        "UPDATE users SET municipio = :mun, provincia = :prov, "
                        "bancada_id = :bid, bancada_nombre = :bname, "
                        "onboarding_step = 6 WHERE telegram_id = :tid"
                    ),
                    {
                        "mun": municipio, "prov": provincia,
                        "bid": bid, "bname": bancada["nombre"],
                        "tid": user_id,
                    },
                )

        if rol == "concejal":
            # Step 5: Posición sobre el proyecto (3 opciones simples)
            keyboard = [
                [{"text": "✅ A FAVOR del proyecto", "callback_data": "onboard_ban_1"}],
                [{"text": "🟡 A FAVOR CON CONDICIONES", "callback_data": "onboard_ban_3"}],
                [{"text": "❌ EN CONTRA del proyecto", "callback_data": "onboard_ban_2"}],
                [{"text": "🤔 INDECISO / depende", "callback_data": "onboard_ban_4"}],
            ]
            text_msg = (
                f"Registrado: *{municipio}* ({provincia})\n\n"
                "*Paso 4 de 5:* ¿Cuál es tu posición inicial sobre el "
                "Proyecto de Acuerdo 001-2026 (SIADR)?\n\n"
                "_Puedes cambiar de opinión durante el debate._"
            )
        else:
            # Saltar bancada — ir directo a causa principal
            keyboard = []
            items = list(TEMAS_ONBOARDING.items())
            for i in range(0, len(items), 2):
                keyboard.append([
                    {"text": info["label"], "callback_data": f"onboard_tema_{key}"}
                    for key, info in items[i:i+2]
                ])
            rol_nombre = ROLES.get(rol, {}).get("nombre", rol)
            text_msg = (
                f"Registrado: *{municipio}* ({provincia})\n"
                f"Rol: {rol_nombre}\n\n"
                f"*Paso 4 de 5:* ¿Cuál es tu causa o tema principal?"
            )

        await agent.bus.stream_add("telegram:outgoing", {
            "chat_id": str(chat_id),
            "text": text_msg,
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
                    "onboarding_step = 6 WHERE telegram_id = :tid"
                ),
                {"bid": bancada_id, "bname": bancada["nombre"], "tid": user_id},
            )

        posicion_label = {1: "✅ A FAVOR", 2: "❌ EN CONTRA", 3: "🟡 A FAVOR CON CONDICIONES", 4: "🤔 INDECISO"}.get(
            bancada_id, bancada["nombre"]
        )

        # Step 5: show predefined themes as buttons (single-select)
        keyboard = []
        items = list(TEMAS_ONBOARDING.items())
        for i in range(0, len(items), 2):
            row = []
            for key, info in items[i:i+2]:
                row.append({
                    "text": info["label"],
                    "callback_data": f"onboard_tema_{key}",
                })
            keyboard.append(row)

        await agent.bus.stream_add("telegram:outgoing", {
            "chat_id": str(chat_id),
            "text": (
                f"Posición inicial: {posicion_label}\n\n"
                f"*Paso 5 de 5:* ¿Cuál es tu causa principal como concejal?"
            ),
            "parse_mode": "Markdown",
            "reply_markup": json.dumps({"inline_keyboard": keyboard}),
        })

    elif step == "tema":
        # User selected tema → complete onboarding
        tema_key = parts[2]
        info = TEMAS_ONBOARDING.get(tema_key)
        if not info:
            return

        temas = info["temas"]
        resumen = info["resumen"]
        temas_pg = "{" + ",".join(temas) + "}"

        async with get_session() as session:
            from sqlalchemy import text as sql_text
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
                    "raw": info["label"],
                    "temas": temas_pg,
                    "kw": "{}",
                    "res": resumen,
                    "pos": "neutral",
                    "tid": user_id,
                },
            )
            result = await session.execute(
                sql_text("SELECT * FROM users WHERE telegram_id = :tid"),
                {"tid": user_id},
            )
            user = result.mappings().first()

        if user:
            bancada = BANCADAS.get(user["bancada_id"], {})
            user_rol = user.get("rol") or "concejal"
            rol_info = ROLES.get(user_rol, {})
            rol_nombre = rol_info.get("nombre", "🏛️ Concejal")

            if user_rol == "concejal":
                posicion_label = {
                    1: "✅ A FAVOR", 2: "❌ EN CONTRA", 4: "🤔 INDECISO"
                }.get(user["bancada_id"], bancada.get("nombre", "?"))
                header = (
                    f"Concejal de {user['municipio']} ({user['provincia']})\n"
                    f"Posición: {posicion_label}\n"
                )
            else:
                header = (
                    f"{rol_nombre}\n"
                    f"{user['municipio']} ({user['provincia']})\n"
                )

            msg = (
                f"*Registro completado*\n\n"
                f"*{user['nombre_completo']}*\n"
                f"{header}"
                f"Causa: {info['label']}\n\n"
                f"{get_voice_selection_text()}\n\n"
                f"Escribe cualquier pregunta para comenzar."
            )
            await agent._send_response(chat_id, msg)

            dossier = get_dossier(user["bancada_id"])
            await agent._send_response(chat_id, dossier)

            power_map = format_power_map(
                user["bancada_id"],
                user.get("temas_interes", []) or [],
            )
            if power_map:
                await agent._send_response(chat_id, power_map)


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
                "✅ Código correcto.\n\n*Paso 1 de 5:* ¿Cuál es tu nombre completo?"
            )
        else:
            await agent._send_response(
                chat_id,
                "❌ Código incorrecto. Intenta de nuevo (4 dígitos):"
            )
        return

    elif step == 1:
        # Step 1: Save name, show role groups
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

        # Filtro de grupos habilitados desde Redis (para que el admin
        # pueda restringir el onboarding a ciertos grupos durante fases
        # puntuales del taller). Key: tavodebate:enabled_groups — lista
        # separada por comas; si está vacía/no existe, se habilitan todos.
        enabled_raw = await agent.bus.raw.get("tavodebate:enabled_groups")
        if isinstance(enabled_raw, bytes):
            enabled_raw = enabled_raw.decode()
        enabled_set = None
        if enabled_raw:
            enabled_set = {g.strip() for g in enabled_raw.split(",") if g.strip()}

        keyboard = [
            [{"text": g["label"], "callback_data": f"onboard_grupo_{key}"}]
            for key, g in GRUPOS_ONBOARDING.items()
            if enabled_set is None or key in enabled_set
        ]

        info_line = ""
        if enabled_set and len(enabled_set) < len(GRUPOS_ONBOARDING):
            info_line = (
                f"\n_Registro limitado por el dinamizador a: "
                f"{', '.join(sorted(enabled_set))}_\n"
            )

        await agent.bus.stream_add("telegram:outgoing", {
            "chat_id": str(chat_id),
            "text": (
                f"Hola *{nombre}*.\n\n"
                f"*Paso 2 de 5:* ¿En qué rol participarás en el Concejo?"
                f"{info_line}"
            ),
            "parse_mode": "Markdown",
            "reply_markup": json.dumps({"inline_keyboard": keyboard}),
        })

    elif step in (2, 3, 4, 5, 6):
        # Steps 2..6 expect inline button callbacks, not text
        await agent._send_response(
            chat_id,
            "Por favor usa los botones de arriba para seleccionar tu opción. "
            "Si no los ves, envía /start para reiniciar el registro."
        )


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
