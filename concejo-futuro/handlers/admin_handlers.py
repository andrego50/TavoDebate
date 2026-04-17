"""TavoDebate - Comandos admin de Telegram."""

import json
import logging

from core.config import settings
from db.database import get_session

logger = logging.getLogger("handlers.admin")


async def _build_context_snapshot() -> str:
    """Lee últimas señales del debate para que el LLM haga un borrador contextual."""
    from sqlalchemy import text as sql_text
    import redis.asyncio as aioredis

    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    phase = await r.get("current_phase") or "en curso"
    await r.aclose()

    parts = [f"Fase actual: {phase}"]

    async with get_session() as session:
        result = await session.execute(
            sql_text(
                "SELECT nombre_concejal, bancada_nombre, question "
                "FROM interactions ORDER BY created_at DESC LIMIT 5"
            )
        )
        interactions = list(result.mappings())
        if interactions:
            parts.append("Últimas preguntas de participantes:")
            for iv in interactions:
                q = (iv["question"] or "")[:140].replace("\n", " ")
                parts.append(f"- [{iv['bancada_nombre']}] {iv['nombre_concejal']}: {q}")

        result = await session.execute(
            sql_text(
                "SELECT description, results, closed_at FROM voting_sessions "
                "WHERE results IS NOT NULL ORDER BY id DESC LIMIT 1"
            )
        )
        last_vote = result.mappings().first()
        if last_vote:
            res = last_vote["results"]
            if isinstance(res, str):
                res = json.loads(res)
            parts.append(
                f"Última votación: {res.get('resultado', '?')} "
                f"(sí {res.get('si', 0)} / no {res.get('no', 0)} / "
                f"abs {res.get('abstencion', 0)})"
            )

    return "\n".join(parts)


async def _generate_draft(agent, kind: str, context: str) -> str:
    """Genera un borrador contextual (broadcast/alerta/presion) con el LLM."""
    if kind == "alerta":
        system = (
            "Eres el dinamizador del Concejo del Futuro. Redacta una ALERTA "
            "institucional breve (máx 50 palabras) basada en el contexto. Tono: "
            "Defensoría del Pueblo / Personería — formal, urgente, interpelativo. "
            "Sin saludos ni firma. No inventes datos que no estén en el contexto."
        )
        user = f"Contexto del debate:\n{context}\n\nRedacta la alerta."
    elif kind == "presion":
        system = (
            "Eres el dinamizador del Concejo del Futuro. Redacta una PRESIÓN "
            "política breve (máx 60 palabras) que un actor externo (gremio, "
            "comunidad, medio, ONG) dirige al Concejo. Tono: interpelativo, "
            "directo, con mención explícita del SIADR. Sin saludos ni firma."
        )
        user = f"Contexto del debate:\n{context}\n\nRedacta la presión política."
    else:
        system = (
            "Eres el dinamizador del Concejo del Futuro. Redacta un COMUNICADO "
            "breve (máx 60 palabras) para todos los participantes basado en el "
            "contexto actual del debate. Debe orientar la deliberación: recordar "
            "tiempo restante, invitar a argumentar mejor, o señalar un hecho "
            "reciente relevante. Sin saludos. No inventes datos."
        )
        user = f"Contexto del debate:\n{context}\n\nRedacta el comunicado."

    try:
        text = await agent.llm.generate(system, user, temperature=0.7, max_tokens=200)
        return text.strip().strip('"')
    except Exception as e:
        logger.error(f"Draft generation failed: {e}")
        return ""


async def _store_draft(user_id: int, kind: str, text: str):
    import redis.asyncio as aioredis
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    await r.setex(f"tavodebate:draft:{kind}:{user_id}", 900, text)
    await r.aclose()


async def _load_draft(user_id: int, kind: str) -> str | None:
    import redis.asyncio as aioredis
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    text = await r.get(f"tavodebate:draft:{kind}:{user_id}")
    if text:
        await r.delete(f"tavodebate:draft:{kind}:{user_id}")
    await r.aclose()
    return text


async def _show_draft_preview(agent, chat_id: int, user_id: int, kind: str):
    """Genera borrador contextual y muestra preview con botones."""
    await agent._send_response(chat_id, f"⏳ Generando borrador de {kind}...")

    try:
        context = await _build_context_snapshot()
    except Exception as e:
        logger.error(f"Context snapshot failed: {e}", exc_info=True)
        context = "Sin contexto disponible."

    draft = await _generate_draft(agent, kind, context)
    if not draft:
        await agent._send_response(
            chat_id,
            f"No pude generar un borrador. Usa `/{kind} <texto>` para enviar manualmente."
        )
        return

    await _store_draft(user_id, kind, draft)

    icon = {"alerta": "🚨", "presion": "📣"}.get(kind, "📢")
    keyboard = json.dumps({"inline_keyboard": [
        [
            {"text": "✅ Aprobar y enviar", "callback_data": f"send_draft_{kind}"},
            {"text": "🔄 Regenerar", "callback_data": f"regen_draft_{kind}"},
        ],
        [{"text": "❌ Cancelar", "callback_data": "cancel_action"}],
    ]})
    await agent.bus.stream_add("telegram:outgoing", {
        "chat_id": str(chat_id),
        "text": (
            f"{icon} *Borrador de {kind}:*\n\n{draft}\n\n"
            f"_Aprueba para enviar a todos, regenera para otro intento, "
            f"o escribe `/{kind} <tu texto>` para versión manual._"
        ),
        "parse_mode": "Markdown",
        "reply_markup": keyboard,
    })


async def handle_admin_command(agent, command: str, args: str, chat_id: int):
    """Enruta comandos admin al orquestador via Redis."""
    cmd = command.lstrip("/")

    if cmd == "broadcast":
        if not args.strip():
            await _show_draft_preview(agent, chat_id, chat_id, "broadcast")
            return
        await agent.bus.publish("control:command", {
            "action": "broadcast",
            "args": {"message": args, "target": "all"},
        })
        await agent._send_response(chat_id, "Broadcast enviado.")

    elif cmd == "bomba":
        from core.bombs import BOMBS
        if not args.strip():
            # Show bomb menu
            keyboard = []
            for bid, bomb in BOMBS.items():
                # First 60 chars as label
                label = bomb["text"].replace("*", "").replace("🔴 ", "")[:55]
                keyboard.append([{"text": f"💣 {bid}. {label}…", "callback_data": f"preview_bomb_{bid}"}])
            await agent.bus.stream_add("telegram:outgoing", {
                "chat_id": str(chat_id),
                "text": "💣 *Selecciona una bomba informativa:*",
                "parse_mode": "Markdown",
                "reply_markup": json.dumps({"inline_keyboard": keyboard}),
            })
            return
        try:
            bomb_id = int(args.strip())
        except ValueError:
            await agent._send_response(chat_id, "Uso: /bomba o /bomba <1-8>")
            return
        # Show preview with confirm button
        bomb = BOMBS.get(bomb_id)
        if not bomb:
            await agent._send_response(chat_id, f"Bomba #{bomb_id} no existe (1-8).")
            return
        preview = bomb["text"][:500].replace("*", "")
        keyboard = json.dumps({"inline_keyboard": [
            [{"text": "✅ Enviar", "callback_data": f"send_bomb_{bomb_id}"},
             {"text": "❌ Cancelar", "callback_data": "cancel_action"}],
        ]})
        await agent.bus.stream_add("telegram:outgoing", {
            "chat_id": str(chat_id),
            "text": f"💣 *Preview Bomba #{bomb_id}:*\n\n{preview}\n\n_Se enviará a todos los concejales + pantalla._",
            "parse_mode": "Markdown",
            "reply_markup": keyboard,
        })

    elif cmd == "fakenews":
        from core.fakenews import FAKE_NEWS
        if not args.strip():
            # Show fakenews menu
            keyboard = []
            for nid, news in FAKE_NEWS.items():
                label = news["text"].replace("*", "").replace("📰 ", "")[:55]
                keyboard.append([{"text": f"📰 {nid}. {label}…", "callback_data": f"preview_fn_{nid}"}])
            await agent.bus.stream_add("telegram:outgoing", {
                "chat_id": str(chat_id),
                "text": "📰 *Selecciona una fake news:*",
                "parse_mode": "Markdown",
                "reply_markup": json.dumps({"inline_keyboard": keyboard}),
            })
            return
        try:
            news_id = int(args.strip())
        except ValueError:
            await agent._send_response(chat_id, "Uso: /fakenews o /fakenews <1-6>")
            return
        news = FAKE_NEWS.get(news_id)
        if not news:
            await agent._send_response(chat_id, f"Fake news #{news_id} no existe (1-6).")
            return
        preview = news["text"][:500].replace("*", "")
        keyboard = json.dumps({"inline_keyboard": [
            [{"text": "✅ Enviar", "callback_data": f"send_fn_{news_id}"},
             {"text": "❌ Cancelar", "callback_data": "cancel_action"}],
        ]})
        await agent.bus.stream_add("telegram:outgoing", {
            "chat_id": str(chat_id),
            "text": f"📰 *Preview Fake News #{news_id}:*\n\n{preview}\n\n_Se enviará a todos los concejales + pantalla._",
            "parse_mode": "Markdown",
            "reply_markup": keyboard,
        })

    elif cmd == "presion":
        if not args.strip():
            await _show_draft_preview(agent, chat_id, chat_id, "presion")
            return
        # /presion <tipo> <tema> <actor> <mensaje>
        parts = args.split('"')
        if len(parts) >= 4:
            header = parts[0].strip().split()
            tipo = header[0] if len(header) > 0 else "comunicado"
            tema = header[1] if len(header) > 1 else "general"
            actor = parts[1]
            mensaje = parts[3] if len(parts) > 3 else parts[1]
        else:
            tipo, tema, actor, mensaje = "comunicado", "general", "Sistema", args
        await agent.bus.publish("control:command", {
            "action": "pressure",
            "args": {"type": tipo, "tema": tema, "actor": actor, "message": mensaje},
        })
        await agent._send_response(chat_id, f"Presión '{tipo}' enviada.")

    elif cmd == "gabinete_remover":
        if not args.strip():
            from core.gabinete import GABINETE
            keyboard = [
                [{"text": g["nombre"], "callback_data": f"preview_gab_remove_{gid}"}]
                for gid, g in GABINETE.items()
            ]
            await agent.bus.stream_add("telegram:outgoing", {
                "chat_id": str(chat_id),
                "text": "🏛️ *Selecciona el gabinete a remover:*",
                "parse_mode": "Markdown",
                "reply_markup": json.dumps({"inline_keyboard": keyboard}),
            })
            return
        gab_id = args.strip()
        await agent.bus.publish("control:command", {
            "action": "gabinete",
            "args": {"gabinete_action": "remover", "gabinete_id": gab_id},
        })
        await agent._send_response(chat_id, f"Gabinete: {gab_id} removido.")

    elif cmd == "gabinete_amenaza":
        if not args.strip():
            from core.gabinete import GABINETE
            keyboard = [
                [{"text": g["nombre"], "callback_data": f"preview_gab_threat_{gid}"}]
                for gid, g in GABINETE.items()
            ]
            await agent.bus.stream_add("telegram:outgoing", {
                "chat_id": str(chat_id),
                "text": "⚠️ *Selecciona el gabinete que emitirá la amenaza:*",
                "parse_mode": "Markdown",
                "reply_markup": json.dumps({"inline_keyboard": keyboard}),
            })
            return
        parts = args.strip().split(" ", 2)
        gab_id = parts[0] if parts else ""
        bancada_id = int(parts[1]) if len(parts) > 1 else 0
        mensaje = parts[2] if len(parts) > 2 else ""
        await agent.bus.publish("control:command", {
            "action": "gabinete",
            "args": {
                "gabinete_action": "amenaza",
                "gabinete_id": gab_id,
                "bancada_id": bancada_id,
                "message": mensaje,
            },
        })
        await agent._send_response(chat_id, f"Amenaza de gabinete enviada a bancada {bancada_id}.")

    elif cmd == "alerta":
        if not args.strip():
            await _show_draft_preview(agent, chat_id, chat_id, "alerta")
            return
        await agent.bus.publish("control:command", {
            "action": "alert",
            "args": {"alert_type": "defensoria", "message": args},
        })
        await agent._send_response(chat_id, "Alerta enviada.")

    elif cmd == "fase":
        if not args.strip():
            # Show inline keyboard with phases
            from handlers.onboarding import FASES
            keyboard = []
            for fase_key, fase_info in FASES.items():
                keyboard.append([{
                    "text": f"{fase_info['nombre']}",
                    "callback_data": f"fase_{fase_key}",
                }])
            await agent.bus.stream_add("telegram:outgoing", {
                "chat_id": str(chat_id),
                "text": "🏛️ *Selecciona la fase del ejercicio:*",
                "parse_mode": "Markdown",
                "reply_markup": json.dumps({"inline_keyboard": keyboard}),
            })
        else:
            from handlers.onboarding import FASES
            fase_key = args.strip().lower()
            fase_info = FASES.get(fase_key)
            if not fase_info:
                await agent._send_response(chat_id, f"Fase '{fase_key}' no existe.")
                return
            await agent.bus.publish("simulation:command", {
                "action": "phase_change",
                "args": {"phase": fase_key},
            })
            await agent._send_response(chat_id, f"✅ Fase cambiada a: *{fase_info['nombre']}*")
            # Send participants summary + phase-specific actions
            from handlers.phase_handlers import get_participants_summary
            summary = await get_participants_summary()
            await agent._send_response(chat_id, summary)
            await _execute_phase_actions(agent, fase_key, chat_id)

    elif cmd == "ronda":
        if not args.strip():
            keyboard = [
                [
                    {"text": "⏱️ 3 min", "callback_data": "ronda_start_3"},
                    {"text": "⏱️ 5 min", "callback_data": "ronda_start_5"},
                    {"text": "⏱️ 10 min", "callback_data": "ronda_start_10"},
                    {"text": "⏱️ 15 min", "callback_data": "ronda_start_15"},
                ],
                [{"text": "❌ Cancelar", "callback_data": "cancel_action"}],
            ]
            await agent.bus.stream_add("telegram:outgoing", {
                "chat_id": str(chat_id),
                "text": "⏱️ *Selecciona la duración del timer:*",
                "parse_mode": "Markdown",
                "reply_markup": json.dumps({"inline_keyboard": keyboard}),
            })
            return
        try:
            minutes = int(args.strip())
        except ValueError:
            minutes = 5
        await agent.bus.publish("simulation:command", {
            "action": "start_timer",
            "args": {"name": "Ronda", "minutes": minutes},
        })
        await agent._send_response(chat_id, f"Timer de {minutes} min iniciado.")

    elif cmd == "historial_votaciones":
        async with get_session() as session:
            from sqlalchemy import text as sql_text
            result = await session.execute(
                sql_text(
                    "SELECT id, opened_at, closed_at, description, results, is_open "
                    "FROM voting_sessions ORDER BY id"
                )
            )
            rows = list(result.mappings())

        if not rows:
            await agent._send_response(chat_id, "No hay votaciones registradas.")
            return

        lines = ["*📜 Historial de votaciones*", ""]
        for i, r in enumerate(rows, 1):
            res = r["results"]
            if isinstance(res, str):
                res = json.loads(res)
            if res:
                marker = "✅" if res.get("aprobado") else "❌"
                lines.append(
                    f"{i}. {marker} *{res.get('resultado', '?')}* — "
                    f"{res.get('si', 0)}sí / {res.get('no', 0)}no / "
                    f"{res.get('abstencion', 0)}abs "
                    f"(cerrada {r['closed_at'].strftime('%H:%M') if r['closed_at'] else '?'})"
                )
            elif r["is_open"]:
                lines.append(f"{i}. 🟢 EN CURSO — {r['description']}")
            else:
                lines.append(f"{i}. ⏸️ Cerrada sin resultados — {r['description']}")

        await agent._send_response(chat_id, "\n".join(lines))

    elif cmd == "tweet":
        from core.tweets import TIMELINE_TWEETS
        if not args.strip():
            # Show tweet menu
            keyboard = []
            for tid, tw in TIMELINE_TWEETS.items():
                label = tw["text"][:50]
                keyboard.append([{"text": f"🐦 {tid}. {label}…", "callback_data": f"preview_tweet_{tid}"}])
            await agent.bus.stream_add("telegram:outgoing", {
                "chat_id": str(chat_id),
                "text": "🐦 *Selecciona un tweet o escribe /tweet <texto>:*",
                "parse_mode": "Markdown",
                "reply_markup": json.dumps({"inline_keyboard": keyboard}),
            })
            return
        # Check if it's a number (predefined tweet)
        try:
            tweet_id = int(args.strip())
            tw = TIMELINE_TWEETS.get(tweet_id)
            if tw:
                preview = tw["text"][:300]
                keyboard = json.dumps({"inline_keyboard": [
                    [{"text": "✅ Publicar", "callback_data": f"send_tweet_{tweet_id}"},
                     {"text": "❌ Cancelar", "callback_data": "cancel_action"}],
                ]})
                await agent.bus.stream_add("telegram:outgoing", {
                    "chat_id": str(chat_id),
                    "text": f"🐦 *Preview Tweet #{tweet_id}:*\n\n*{tw['author']}*\n{preview}\n\n_Se publicará en pantalla._",
                    "parse_mode": "Markdown",
                    "reply_markup": keyboard,
                })
                return
        except ValueError:
            pass
        # Free text tweet
        await agent.bus.publish("tweet:new", {
            "author": "@ConcejoCund",
            "text": args,
            "is_manual": True,
        })
        await agent._send_response(chat_id, "Tweet publicado en pantalla.")

    elif cmd == "llm":
        parts = args.strip().split()
        if parts and parts[0] == "switch" and len(parts) > 1:
            provider = parts[1]
            if agent.llm:
                await agent.llm.switch_primary(provider)
            await agent._send_response(chat_id, f"LLM primario: {provider}")
        elif parts and parts[0] == "status":
            await agent._send_response(chat_id, "Estado LLM: operativo")
        else:
            await agent._send_response(chat_id, "Uso: /llm switch <deepseek|kimi> | /llm status")

    elif cmd == "modo_test":
        keyboard = json.dumps({"inline_keyboard": [
            [
                {"text": "✅ Crear 15 usuarios de prueba", "callback_data": "confirm_modo_test"},
                {"text": "❌ Cancelar", "callback_data": "cancel_action"},
            ],
        ]})
        await agent.bus.stream_add("telegram:outgoing", {
            "chat_id": str(chat_id),
            "text": (
                "⚠️ *Modo test*\n\n"
                "Se crearán 15 usuarios ficticios (alcalde, secretarios, "
                "concejales, líderes, veedor, empresa) con `telegram_id` en "
                "el rango 900000000-900000014.\n\n"
                "¿Continuar?"
            ),
            "parse_mode": "Markdown",
            "reply_markup": keyboard,
        })

    elif cmd == "briefing":
        keyboard = json.dumps({"inline_keyboard": [
            [
                {"text": "✅ Forzar briefing ahora", "callback_data": "confirm_briefing"},
                {"text": "❌ Cancelar", "callback_data": "cancel_action"},
            ],
        ]})
        await agent.bus.stream_add("telegram:outgoing", {
            "chat_id": str(chat_id),
            "text": (
                "🕵️ *Forzar briefing de inteligencia*\n\n"
                "El agente Intel generará un reporte inmediato sobre el estado "
                "del debate y lo enviará al dinamizador.\n\n¿Continuar?"
            ),
            "parse_mode": "Markdown",
            "reply_markup": keyboard,
        })

    elif cmd == "pantalla":
        if not args.strip():
            keyboard = [
                [
                    {"text": "📺 Normal", "callback_data": "pantalla_mode_normal"},
                    {"text": "🗳️ Votación", "callback_data": "pantalla_mode_votacion"},
                ],
                [
                    {"text": "🎤 Ponencia", "callback_data": "pantalla_mode_ponencia"},
                    {"text": "📊 Debate", "callback_data": "pantalla_mode_debate"},
                ],
                [{"text": "❌ Cancelar", "callback_data": "cancel_action"}],
            ]
            await agent.bus.stream_add("telegram:outgoing", {
                "chat_id": str(chat_id),
                "text": "📺 *Selecciona el modo de pantalla:*",
                "parse_mode": "Markdown",
                "reply_markup": json.dumps({"inline_keyboard": keyboard}),
            })
            return
        await agent.bus.publish("pantalla:command", {
            "action": "layout_change",
            "args": {"mode": args.strip()},
        })
        await agent._send_response(chat_id, f"Pantalla: modo {args.strip()}")

    elif cmd == "asignar_rol":
        await _handle_asignar_rol(agent, chat_id, args)

    elif cmd == "roles":
        # Show all users and their roles
        async with get_session() as session:
            from sqlalchemy import text as sql_text
            result = await session.execute(
                sql_text(
                    "SELECT nombre_completo, municipio, bancada_nombre, "
                    "COALESCE(rol, 'concejal') as rol FROM users "
                    "WHERE onboarding_complete = true AND bancada_nombre != 'Dinamizador' "
                    "ORDER BY rol, nombre_completo"
                )
            )
            rows = result.fetchall()
        if not rows:
            await agent._send_response(chat_id, "No hay participantes registrados.")
            return
        from core.config import ROLES
        lines = ["*Participantes y roles:*\n"]
        current_rol = None
        for name, mun, bancada, rol in rows:
            rol_info = ROLES.get(rol, {})
            rol_nombre = rol_info.get("nombre", rol)
            if rol != current_rol:
                current_rol = rol
                lines.append(f"\n*{rol_nombre}*")
            lines.append(f"  - {name} ({mun}) — {bancada}")
        await agent._send_response(chat_id, "\n".join(lines))

    else:
        await agent._send_response(chat_id, f"Comando admin no reconocido: {cmd}")


async def handle_approval_callback(agent, user_id: int, chat_id: int, data: str, callback_id: str):
    """Procesa callbacks de aprobación de propuestas proactivas."""
    if user_id not in settings.admin_ids:
        return

    parts = data.split("_")
    action = parts[1] if len(parts) > 1 else ""
    proposal_idx = parts[2] if len(parts) > 2 else "0"

    if action == "yes":
        await agent._send_response(chat_id, f"Propuesta #{proposal_idx} aprobada. Ejecutando...")
    elif action == "no":
        await agent._send_response(chat_id, f"Propuesta #{proposal_idx} rechazada.")


async def handle_admin_callback(agent, user_id: int, chat_id: int, data: str, callback_id: str):
    """Procesa callbacks de preview/send/cancel de bombas, fakenews, tweets."""
    if data == "cancel_action":
        await agent._send_response(chat_id, "Acción cancelada.")
        return

    # Preview callbacks: show full content + confirm button
    if data.startswith("preview_bomb_"):
        bomb_id = int(data.split("_")[-1])
        from core.bombs import BOMBS
        bomb = BOMBS.get(bomb_id)
        if bomb:
            preview = bomb["text"].replace("*", "")[:500]
            keyboard = json.dumps({"inline_keyboard": [
                [{"text": "✅ Enviar", "callback_data": f"send_bomb_{bomb_id}"},
                 {"text": "❌ Cancelar", "callback_data": "cancel_action"}],
            ]})
            await agent.bus.stream_add("telegram:outgoing", {
                "chat_id": str(chat_id),
                "text": f"💣 *Preview Bomba #{bomb_id}:*\n\n{preview}\n\n_Se enviará a todos + pantalla con tweets de reacción._",
                "parse_mode": "Markdown",
                "reply_markup": keyboard,
            })
        return

    if data.startswith("preview_fn_"):
        news_id = int(data.split("_")[-1])
        from core.fakenews import FAKE_NEWS
        news = FAKE_NEWS.get(news_id)
        if news:
            preview = news["text"].replace("*", "")[:500]
            keyboard = json.dumps({"inline_keyboard": [
                [{"text": "✅ Enviar", "callback_data": f"send_fn_{news_id}"},
                 {"text": "❌ Cancelar", "callback_data": "cancel_action"}],
            ]})
            await agent.bus.stream_add("telegram:outgoing", {
                "chat_id": str(chat_id),
                "text": f"📰 *Preview Fake News #{news_id}:*\n\n{preview}\n\n_Se enviará a todos + pantalla con tweets de reacción._",
                "parse_mode": "Markdown",
                "reply_markup": keyboard,
            })
        return

    if data.startswith("preview_tweet_"):
        tweet_id = int(data.split("_")[-1])
        from core.tweets import TIMELINE_TWEETS
        tw = TIMELINE_TWEETS.get(tweet_id)
        if tw:
            keyboard = json.dumps({"inline_keyboard": [
                [{"text": "✅ Publicar", "callback_data": f"send_tweet_{tweet_id}"},
                 {"text": "❌ Cancelar", "callback_data": "cancel_action"}],
            ]})
            await agent.bus.stream_add("telegram:outgoing", {
                "chat_id": str(chat_id),
                "text": f"🐦 *Preview Tweet #{tweet_id}:*\n\n*{tw['author']}*\n{tw['text']}\n\n_Se publicará en pantalla._",
                "parse_mode": "Markdown",
                "reply_markup": keyboard,
            })
        return

    # Send callbacks: execute the action
    if data.startswith("send_bomb_"):
        bomb_id = int(data.split("_")[-1])
        await agent.bus.publish("control:command", {
            "action": "bomb",
            "args": {"bomb_id": bomb_id},
        })
        await agent._send_response(chat_id, f"💣 Bomba #{bomb_id} enviada a todos los concejales + pantalla.")
        return

    if data.startswith("send_fn_"):
        news_id = int(data.split("_")[-1])
        await agent.bus.publish("control:command", {
            "action": "fakenews",
            "args": {"news_id": news_id},
        })
        await agent._send_response(chat_id, f"📰 Fake news #{news_id} enviada a todos los concejales + pantalla.")
        return

    if data in ("send_draft_broadcast", "send_draft_alerta", "send_draft_presion"):
        kind = data.rsplit("_", 1)[1]
        draft = await _load_draft(chat_id, kind)
        if not draft:
            await agent._send_response(chat_id, "Borrador expirado. Usa el comando de nuevo.")
            return
        if kind == "broadcast":
            await agent.bus.publish("control:command", {
                "action": "broadcast",
                "args": {"message": draft, "target": "all"},
            })
            await agent._send_response(chat_id, "📢 Broadcast enviado.")
        elif kind == "alerta":
            await agent.bus.publish("control:command", {
                "action": "alert",
                "args": {"alert_type": "defensoria", "message": draft},
            })
            await agent._send_response(chat_id, "🚨 Alerta enviada.")
        elif kind == "presion":
            await agent.bus.publish("control:command", {
                "action": "pressure",
                "args": {
                    "type": "comunicado", "tema": "general",
                    "actor": "Actor externo", "message": draft,
                },
            })
            await agent._send_response(chat_id, "📣 Presión política enviada.")
        return

    if data in ("regen_draft_broadcast", "regen_draft_alerta", "regen_draft_presion"):
        kind = data.rsplit("_", 1)[1]
        await _show_draft_preview(agent, chat_id, chat_id, kind)
        return

    if data == "confirm_modo_test":
        await _create_test_users(agent, chat_id)
        return

    if data == "confirm_briefing":
        await agent.bus.publish("intel:command", {
            "action": "force_briefing", "args": {},
        })
        await agent._send_response(chat_id, "🕵️ Briefing forzado.")
        return

    if data.startswith("ronda_start_"):
        minutes = int(data.rsplit("_", 1)[1])
        await agent.bus.publish("simulation:command", {
            "action": "start_timer",
            "args": {"name": "Ronda", "minutes": minutes},
        })
        await agent._send_response(chat_id, f"⏱️ Timer de {minutes} min iniciado.")
        return

    if data.startswith("pantalla_mode_"):
        mode = data.rsplit("_", 1)[1]
        await agent.bus.publish("pantalla:command", {
            "action": "layout_change",
            "args": {"mode": mode},
        })
        await agent._send_response(chat_id, f"📺 Pantalla: modo {mode}.")
        return

    if data.startswith("preview_gab_remove_"):
        gab_id = data.replace("preview_gab_remove_", "")
        from core.gabinete import GABINETE
        gab = GABINETE.get(gab_id, {})
        keyboard = json.dumps({"inline_keyboard": [
            [
                {"text": "✅ Confirmar remoción", "callback_data": f"send_gab_remove_{gab_id}"},
                {"text": "❌ Cancelar", "callback_data": "cancel_action"},
            ],
        ]})
        await agent.bus.stream_add("telegram:outgoing", {
            "chat_id": str(chat_id),
            "text": (
                f"🏛️ *Remover gabinete:* {gab.get('nombre', gab_id)}\n"
                f"Titular: {gab.get('titular', '?')}\n\n"
                "¿Confirmar?"
            ),
            "parse_mode": "Markdown",
            "reply_markup": keyboard,
        })
        return

    if data.startswith("send_gab_remove_"):
        gab_id = data.replace("send_gab_remove_", "")
        await agent.bus.publish("control:command", {
            "action": "gabinete",
            "args": {"gabinete_action": "remover", "gabinete_id": gab_id},
        })
        await agent._send_response(chat_id, f"🏛️ Gabinete *{gab_id}* removido.")
        return

    if data.startswith("preview_gab_threat_"):
        gab_id = data.replace("preview_gab_threat_", "")
        from core.gabinete import GABINETE
        gab = GABINETE.get(gab_id, {})
        # Ask which bancada to threaten
        from core.config import BANCADAS
        keyboard = [
            [{"text": b["nombre"], "callback_data": f"send_gab_threat_{gab_id}_{bid}"}]
            for bid, b in BANCADAS.items()
        ]
        keyboard.append([{"text": "❌ Cancelar", "callback_data": "cancel_action"}])
        await agent.bus.stream_add("telegram:outgoing", {
            "chat_id": str(chat_id),
            "text": (
                f"⚠️ *{gab.get('nombre', gab_id)} emitirá amenaza.*\n"
                f"Titular: {gab.get('titular', '?')}\n\n"
                "Selecciona la bancada destinataria:"
            ),
            "parse_mode": "Markdown",
            "reply_markup": json.dumps({"inline_keyboard": keyboard}),
        })
        return

    if data.startswith("send_gab_threat_"):
        rest = data.replace("send_gab_threat_", "")
        gab_id, bid = rest.rsplit("_", 1)
        await agent.bus.publish("control:command", {
            "action": "gabinete",
            "args": {
                "gabinete_action": "amenaza",
                "gabinete_id": gab_id,
                "bancada_id": int(bid),
                "message": "",
            },
        })
        await agent._send_response(
            chat_id, f"⚠️ Amenaza de *{gab_id}* → bancada {bid} enviada."
        )
        return

    if data.startswith("send_tweet_"):
        tweet_id = int(data.split("_")[-1])
        from core.tweets import TIMELINE_TWEETS
        tw = TIMELINE_TWEETS.get(tweet_id)
        if tw:
            await agent.bus.publish("tweet:new", {
                "author": tw["author"],
                "text": tw["text"],
                "is_manual": True,
            })
            await agent._send_response(chat_id, f"🐦 Tweet #{tweet_id} publicado en pantalla.")
        return


async def _create_test_users(agent, chat_id: int):
    """Crea 15 participantes ficticios con roles variados."""
    from core.config import BANCADAS

    # (nombre, municipio, provincia, bancada_id, temas, rol)
    test_users = [
        # Gobierno (defienden proyecto)
        ("Roberto Alcalde", "Bogotá", "Sabana Centro", 1, ["gobierno", "proyecto"], "alcalde"),
        ("Diana Planeación", "Bogotá", "Sabana Centro", 1, ["datos", "metodologia"], "sec_planeacion"),
        ("Fernando Hacienda", "Bogotá", "Sabana Centro", 1, ["presupuesto", "regalias"], "sec_hacienda"),
        # Concejales (votan)
        ("Juan Pérez", "Fusagasugá", "Sumapaz", 1, ["agro", "infraestructura"], "concejal"),
        ("María López", "Zipaquirá", "Sabana Centro", 2, ["ambiente", "agua"], "concejal"),
        ("Carlos Gómez", "Girardot", "Alto Magdalena", 3, ["agro", "educacion"], "concejal"),
        ("Ana Rodríguez", "Facatativá", "Sabana Occidente", 4, ["tecnologia", "comercio"], "concejal"),
        ("Pedro Martínez", "Chía", "Sabana Centro", 5, ["hacienda", "infraestructura"], "concejal"),
        ("Laura Torres", "Soacha", "Soacha", 6, ["derechos_humanos", "seguridad"], "concejal"),
        ("Diego Hernández", "La Mesa", "Tequendama", 1, ["turismo", "cultura"], "concejal"),
        ("Camila Vargas", "Pacho", "Rionegro", 2, ["salud", "mujer_genero"], "concejal"),
        # Sociedad civil + control
        ("Rosa Campesina", "Cabrera", "Sumapaz", 3, ["campo", "agua"], "lider_campesino"),
        ("Tomás Ambientalista", "Guasca", "Guavio", 6, ["ambiente", "ecosistemas"], "ambientalista"),
        ("Gloria Veedora", "Ubaté", "Ubaté", 6, ["transparencia", "control"], "veedor"),
        ("Sergio TechCundi", "Bogotá", "Sabana Centro", 4, ["tecnologia", "iot"], "empresa_tech"),
    ]

    async with get_session() as session:
        from sqlalchemy import text as sql_text
        for i, (nombre, mun, prov, bid, temas, rol) in enumerate(test_users):
            tid = 900000000 + i
            bancada = BANCADAS[bid]
            await session.execute(
                sql_text(
                    "INSERT INTO users (telegram_id, username, nombre_completo, municipio, "
                    "provincia, bancada_id, bancada_nombre, temas_interes, onboarding_complete, rol) "
                    "VALUES (:tid, :un, :name, :mun, :prov, :bid, :bname, :temas, true, :rol) "
                    "ON CONFLICT (telegram_id) DO UPDATE SET rol = :rol, nombre_completo = :name"
                ),
                {
                    "tid": tid, "un": f"test_user_{i}",
                    "name": nombre, "mun": mun, "prov": prov,
                    "bid": bid, "bname": bancada["nombre"],
                    "temas": temas, "rol": rol,
                },
            )

    await agent._send_response(
        chat_id,
        "15 participantes de prueba creados:\n"
        "- 1 Alcalde + 2 Secretarios (gobierno)\n"
        "- 8 Concejales (votan)\n"
        "- 1 Líder campesino + 1 Ambientalista + 1 Veedora + 1 Empresa Tech"
    )


async def _handle_asignar_rol(agent, chat_id: int, args: str):
    """Asigna un rol institucional a un participante.

    /asignar_rol → muestra menú de participantes
    /asignar_rol <nombre_parcial> <rol>
    """
    from core.config import ROLES

    if not args.strip():
        # Show inline keyboard with roles
        keyboard = []
        for rol_key, rol_info in ROLES.items():
            if rol_key == "concejal":
                continue  # Default, no need to assign
            keyboard.append([{
                "text": f"{rol_info['nombre']}",
                "callback_data": f"assign_role_{rol_key}",
            }])
        await agent.bus.stream_add("telegram:outgoing", {
            "chat_id": str(chat_id),
            "text": (
                "👤 *Asignar rol institucional*\n\n"
                "Selecciona el rol, luego te pido el nombre del participante.\n\n"
                "O usa: `/asignar_rol <nombre> <rol>`\n"
                "Ejemplo: `/asignar_rol Juan alcalde`\n\n"
                "Roles disponibles:\n" +
                "\n".join(f"  `{k}` — {v['nombre']}" for k, v in ROLES.items() if k != "concejal")
            ),
            "parse_mode": "Markdown",
            "reply_markup": json.dumps({"inline_keyboard": keyboard}),
        })
        return

    # Parse: /asignar_rol <nombre_parcial> <rol>
    parts = args.strip().rsplit(" ", 1)
    if len(parts) < 2:
        await agent._send_response(chat_id, "Uso: `/asignar_rol <nombre> <rol>`")
        return

    nombre_parcial = parts[0].strip()
    rol_key = parts[1].strip().lower()

    if rol_key not in ROLES:
        await agent._send_response(chat_id, f"Rol '{rol_key}' no existe. Usa `/asignar_rol` para ver opciones.")
        return

    async with get_session() as session:
        from sqlalchemy import text as sql_text
        result = await session.execute(
            sql_text(
                "SELECT id, nombre_completo, telegram_id FROM users "
                "WHERE LOWER(nombre_completo) LIKE :pattern AND onboarding_complete = true "
                "LIMIT 1"
            ),
            {"pattern": f"%{nombre_parcial.lower()}%"},
        )
        user = result.fetchone()
        if not user:
            await agent._send_response(chat_id, f"No encontré a nadie con nombre '{nombre_parcial}'.")
            return

        await session.execute(
            sql_text("UPDATE users SET rol = :rol WHERE id = :uid"),
            {"rol": rol_key, "uid": user[0]},
        )

    rol_info = ROLES[rol_key]
    await agent._send_response(
        chat_id,
        f"✅ *{user[1]}* ahora es *{rol_info['nombre']}*"
    )
    # Notify the user
    await agent.bus.stream_add("telegram:outgoing", {
        "chat_id": str(user[2]),
        "text": (
            f"🎭 *Tu rol ha sido asignado:*\n\n"
            f"*{rol_info['nombre']}*\n"
            f"_{rol_info['descripcion']}_\n\n"
            f"{'🗳️ Puedes votar el proyecto.' if rol_info['puede_votar'] else '📢 No votas, pero puedes opinar, tuitear y participar en el debate.'}"
        ),
        "parse_mode": "Markdown",
    })


async def _get_pantalla_url() -> str:
    """Gets the public pantalla URL from Redis, or falls back to local."""
    import redis.asyncio as aioredis
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    url = await r.get("tavodebate:pantalla_url")
    await r.aclose()
    return url or f"http://{settings.vps_domain}:8085/pantalla"


async def _execute_phase_actions(agent, fase_key: str, admin_chat_id: int):
    """Ejecuta acciones automáticas al cambiar de fase."""
    if fase_key == "ponencia_alcalde":
        # Broadcast the alcalde presentation to all registered concejales
        from core.ponencia_alcalde import PONENCIA_ALCALDE, PONENCIA_ALCALDE_CORTA
        pantalla_url = await _get_pantalla_url()

        # Get all registered concejal telegram_ids
        async with get_session() as session:
            from sqlalchemy import text as sql_text
            result = await session.execute(
                sql_text(
                    "SELECT telegram_id FROM users "
                    "WHERE onboarding_complete = true AND bancada_nombre != 'Dinamizador'"
                )
            )
            concejales = [row[0] for row in result.fetchall()]

        if not concejales:
            await agent._send_response(admin_chat_id, "⚠️ No hay concejales registrados para enviar la ponencia.")
            return

        # Send full presentation to all concejales
        ponencia = PONENCIA_ALCALDE.replace("{pantalla_url}", pantalla_url)
        for tid in concejales:
            await agent.bus.stream_add("telegram:outgoing", {
                "chat_id": str(tid),
                "text": ponencia,
                "parse_mode": "Markdown",
            })

        # Send PDF presentation
        from pathlib import Path
        pdf_path = str(Path(__file__).parent.parent / "static" / "ponencia_siadr.pdf")
        for tid in concejales:
            await agent.bus.stream_add("telegram:outgoing", {
                "type": "document",
                "chat_id": str(tid),
                "file_path": pdf_path,
                "caption": "📊 Presentación — Proyecto de Acuerdo 001-2026 SIADR",
                "parse_mode": "Markdown",
            })

        await agent._send_response(
            admin_chat_id,
            f"📨 Ponencia + PDF enviados a *{len(concejales)}* concejales."
        )

    elif fase_key == "votacion":
        # Create voting session + remind all concejales to vote
        async with get_session() as session:
            from sqlalchemy import text as sql_text
            # Close any existing open sessions
            await session.execute(
                sql_text("UPDATE voting_sessions SET is_open = false, closed_at = NOW() WHERE is_open = true")
            )
            # Open new voting session
            await session.execute(
                sql_text(
                    "INSERT INTO voting_sessions (type, description, is_open) "
                    "VALUES ('proyecto', 'Proyecto de Acuerdo 001-2026 — SIADR', true)"
                )
            )
            result = await session.execute(
                sql_text(
                    "SELECT telegram_id FROM users "
                    "WHERE onboarding_complete = true AND bancada_nombre != 'Dinamizador'"
                )
            )
            concejales = [row[0] for row in result.fetchall()]

        for tid in concejales:
            await agent.bus.stream_add("telegram:outgoing", {
                "chat_id": str(tid),
                "text": (
                    "🗳️ *FASE DE VOTACIÓN ABIERTA*\n\n"
                    "Es hora de votar el Proyecto de Acuerdo SIADR.\n\n"
                    "Usa: `/votar_proyecto a_favor`, `en_contra` o `abstencion`\n\n"
                    "Tu voto es secreto y personal."
                ),
                "parse_mode": "Markdown",
            })

        await agent._send_response(
            admin_chat_id,
            f"🗳️ Aviso de votación enviado a *{len(concejales)}* concejales."
        )

    elif fase_key == "debriefing":
        # Remind about certificates
        pantalla_url = await _get_pantalla_url()
        async with get_session() as session:
            from sqlalchemy import text as sql_text
            result = await session.execute(
                sql_text(
                    "SELECT telegram_id FROM users "
                    "WHERE onboarding_complete = true AND bancada_nombre != 'Dinamizador'"
                )
            )
            concejales = [row[0] for row in result.fetchall()]

        for tid in concejales:
            await agent.bus.stream_add("telegram:outgoing", {
                "chat_id": str(tid),
                "text": (
                    "🎓 *SESIÓN FINALIZADA*\n\n"
                    "Gracias por participar en el Gran Concejo del Futuro.\n\n"
                    "Descarga tu certificado de participación: /mi\\_certificado\n\n"
                    f"🔗 Revive el debate en vivo:\n{pantalla_url}"
                ),
                "parse_mode": "Markdown",
            })

        await agent._send_response(
            admin_chat_id,
            f"🎓 Aviso de cierre enviado a *{len(concejales)}* concejales."
        )
