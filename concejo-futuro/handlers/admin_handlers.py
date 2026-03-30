"""TavoDebate - Comandos admin de Telegram."""

import json
import logging

from core.config import settings
from db.database import get_session

logger = logging.getLogger("handlers.admin")


async def handle_admin_command(agent, command: str, args: str, chat_id: int):
    """Enruta comandos admin al orquestador via Redis."""
    cmd = command.lstrip("/")

    if cmd == "broadcast":
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
        gab_id = args.strip()
        await agent.bus.publish("control:command", {
            "action": "gabinete",
            "args": {"gabinete_action": "remover", "gabinete_id": gab_id},
        })
        await agent._send_response(chat_id, f"Gabinete: {gab_id} removido.")

    elif cmd == "gabinete_amenaza":
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
        try:
            minutes = int(args.strip())
        except ValueError:
            minutes = 5
        await agent.bus.publish("simulation:command", {
            "action": "start_timer",
            "args": {"name": "Ronda", "minutes": minutes},
        })
        await agent._send_response(chat_id, f"Timer de {minutes} min iniciado.")

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
        await _create_test_users(agent, chat_id)

    elif cmd == "briefing":
        await agent.bus.publish("intel:command", {
            "action": "force_briefing",
            "args": {},
        })
        await agent._send_response(chat_id, "Briefing forzado solicitado.")

    elif cmd == "pantalla":
        await agent.bus.publish("pantalla:command", {
            "action": "layout_change",
            "args": {"mode": args.strip()},
        })
        await agent._send_response(chat_id, f"Pantalla: modo {args.strip()}")

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
    """Crea 10 concejales ficticios para pruebas."""
    from core.config import BANCADAS, PROVINCIAS_MUNICIPIOS

    test_users = [
        ("Juan Pérez", "Fusagasugá", "Sumapaz", 1, ["agro", "infraestructura"]),
        ("María López", "Zipaquirá", "Sabana Centro", 2, ["ambiente", "agua"]),
        ("Carlos Gómez", "Girardot", "Alto Magdalena", 3, ["agro", "educacion"]),
        ("Ana Rodríguez", "Facatativá", "Sabana Occidente", 4, ["tecnologia", "comercio"]),
        ("Pedro Martínez", "Chía", "Sabana Centro", 5, ["hacienda", "infraestructura"]),
        ("Laura Torres", "Soacha", "Soacha", 6, ["derechos_humanos", "seguridad"]),
        ("Diego Hernández", "La Mesa", "Tequendama", 1, ["turismo", "cultura"]),
        ("Camila Vargas", "Pacho", "Rionegro", 2, ["salud", "mujer_genero"]),
        ("Andrés Castro", "Guaduas", "Bajo Magdalena", 3, ["transporte", "mineria"]),
        ("Sofía Ramírez", "Chocontá", "Almeidas", 4, ["juventud", "educacion"]),
    ]

    async with get_session() as session:
        from sqlalchemy import text as sql_text
        for i, (nombre, mun, prov, bid, temas) in enumerate(test_users):
            tid = 900000000 + i
            bancada = BANCADAS[bid]
            await session.execute(
                sql_text(
                    "INSERT INTO users (telegram_id, username, nombre_completo, municipio, "
                    "provincia, bancada_id, bancada_nombre, temas_interes, onboarding_complete) "
                    "VALUES (:tid, :un, :name, :mun, :prov, :bid, :bname, :temas, true) "
                    "ON CONFLICT (telegram_id) DO NOTHING"
                ),
                {
                    "tid": tid, "un": f"test_user_{i}",
                    "name": nombre, "mun": mun, "prov": prov,
                    "bid": bid, "bname": bancada["nombre"],
                    "temas": temas,
                },
            )

    await agent._send_response(chat_id, "10 usuarios de prueba creados.")


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

        await agent._send_response(
            admin_chat_id,
            f"📨 Ponencia del Alcalde enviada a *{len(concejales)}* concejales."
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
