"""TavoDebate - Agente Chat (responde a los 150 concejales)."""

import asyncio
import json
import logging

from agents.base_agent import BaseAgent
from core.config import settings
from core.llm_client import LLMClient
from db.database import get_session

logger = logging.getLogger("agent.chat")


class ChatAgent(BaseAgent):
    name = "chat"

    def __init__(self):
        super().__init__()
        self.llm: LLMClient | None = None

    async def setup(self):
        await super().setup()
        self.llm = LLMClient(redis_client=self.bus.raw)

    async def start(self):
        """Lee telegram:incoming como consumer group."""
        logger.info("Chat agent consuming telegram:incoming")
        while self._running:
            try:
                messages = await self.bus.stream_read_group(
                    "telegram:incoming",
                    "chat_agents",
                    count=10,
                    block=5000,
                )
                for entry_id, update in messages:
                    try:
                        await self._process_update(update)
                    except Exception as e:
                        logger.error(f"Error processing update: {e}", exc_info=True)
                    finally:
                        await self.bus.stream_ack(
                            "telegram:incoming", "chat_agents", entry_id
                        )
            except Exception as e:
                logger.error(f"Stream read error: {e}")
                await asyncio.sleep(2)

    async def _process_update(self, update: dict):
        """Procesa un update de Telegram."""
        message = update.get("message")
        if not message:
            # Could be callback_query, etc.
            callback = update.get("callback_query")
            if callback:
                await self._process_callback(callback)
            return

        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        username = message["from"].get("username", "")
        first_name = message["from"].get("first_name", "")

        # Rate limiting
        if not await self.bus.check_rate_limit(user_id):
            await self._send_response(
                chat_id, "Estás enviando mensajes muy rápido. Espera un momento."
            )
            return

        # Voice message
        if "voice" in message:
            await self._handle_voice(user_id, chat_id, message)
            return

        text = message.get("text", "")
        if not text:
            return

        # Commands
        if text.startswith("/"):
            await self._handle_command(user_id, chat_id, text, username, first_name)
            return

        # Check if user is in onboarding (step 0=PIN, 1-4=onboarding steps)
        async with get_session() as session:
            from sqlalchemy import text as sql_text
            result_full = await session.execute(
                sql_text("SELECT onboarding_step, onboarding_complete FROM users WHERE telegram_id = :tid"),
                {"tid": user_id},
            )
            row = result_full.mappings().first()

        if row and not row["onboarding_complete"]:
            from handlers.onboarding import process_onboarding_text
            await process_onboarding_text(self, user_id, chat_id, text)
            return

        # Admin natural language → try to interpret as command
        if user_id in settings.admin_ids:
            interpreted = await self._interpret_admin_nl(text)
            if interpreted:
                await self._handle_command(user_id, chat_id, interpreted, "", "Admin")
                return

        # Regular message - generate response
        await self._handle_message(user_id, chat_id, text)

    async def _handle_command(
        self, user_id: int, chat_id: int, text: str, username: str, first_name: str
    ):
        """Enruta comandos del bot."""
        command = text.split()[0].lower().replace("@tavodebate_bot", "")
        args = text[len(command):].strip()

        if command == "/start":
            from handlers.onboarding import handle_start
            await handle_start(self, user_id, chat_id, username, first_name)
        elif command == "/help":
            from handlers.onboarding import handle_help
            await handle_help(self, chat_id)
        elif command == "/estado":
            from handlers.phase_handlers import handle_estado
            await handle_estado(self, user_id, chat_id)
        elif command == "/proponer":
            from handlers.proposal_handlers import handle_proponer
            await handle_proponer(self, user_id, chat_id, args)
        elif command == "/apoyar":
            from handlers.proposal_handlers import handle_apoyar
            await handle_apoyar(self, user_id, chat_id, args)
        elif command == "/propuestas_todas":
            from handlers.proposal_handlers import handle_propuestas_todas
            await handle_propuestas_todas(self, chat_id)
        elif command == "/votar_proyecto":
            from handlers.voting_handlers import handle_votar_proyecto
            await handle_votar_proyecto(self, user_id, chat_id, args)
        elif command == "/votar_enmienda":
            from handlers.voting_handlers import handle_votar_enmienda
            await handle_votar_enmienda(self, user_id, chat_id, args)
        elif command == "/negociar":
            from handlers.negotiation_handlers import handle_negociar
            await handle_negociar(self, user_id, chat_id, args)
        elif command == "/mi_certificado":
            from handlers.certificate_generator import handle_certificado
            await handle_certificado(self, user_id, chat_id)
        elif command == "/preparar_ponencia":
            from handlers.ponencia_handler import handle_preparar_ponencia
            await handle_preparar_ponencia(self, user_id, chat_id, args)
        elif command == "/tutorial":
            from handlers.tutorial_handler import handle_tutorial
            await handle_tutorial(self, user_id, chat_id)
        elif command == "/mi_feedback":
            from handlers.feedback_handler import handle_mi_feedback
            await handle_mi_feedback(self, user_id, chat_id)
        elif command == "/votacion_articulos":
            from handlers.presidencia_handler import handle_votacion_articulos
            await handle_votacion_articulos(self, user_id, chat_id)
        elif command == "/votar_articulo":
            from handlers.presidencia_handler import handle_votar_articulo
            await handle_votar_articulo(self, user_id, chat_id, args)
        elif command == "/compilar_acuerdo":
            from handlers.presidencia_handler import handle_compilar_acuerdo
            await handle_compilar_acuerdo(self, user_id, chat_id)
        elif command == "/tuitear":
            await self._handle_tuitear(user_id, chat_id, args)
        elif command == "/asesores":
            from core.advisors import get_advisor_keyboard, ADVISORS, TEAM_KEY, TEAM_META
            current = await self._get_active_advisor(user_id)
            if current == TEAM_KEY:
                label = f"{TEAM_META['emoji']} {TEAM_META['nombre']}"
            else:
                adv_info = ADVISORS.get(current, {})
                label = f"{adv_info.get('emoji', '')} {adv_info.get('nombre', current)}"
            keyboard = json.dumps({"inline_keyboard": get_advisor_keyboard()})
            await self._send_response(
                chat_id,
                "🧠 *Panel de Asesores*\n\n"
                f"Modo activo: *{label}*\n\n"
                "• 🧠 *Equipo* (default): tus preguntas se enrutan a los "
                "asesores relevantes en paralelo y recibes una respuesta "
                "consolidada con la voz de cada especialista.\n\n"
                "• Los 5 asesores individuales están especializados en "
                "dominios estrictos (leyes, comunicación, cifras, política, "
                "tecnología). Útiles cuando ya sabes a quién necesitas.\n\n"
                "Selecciona:",
                reply_markup=keyboard,
            )
        # Voice switch commands
        elif command in ("/ciudadano", "/experto", "/contralor", "/empresa", "/alcalde"):
            voice_name = command[1:]  # Remove /
            async with get_session() as session:
                from sqlalchemy import text as sql_text
                await session.execute(
                    sql_text("UPDATE users SET active_voice = :v WHERE telegram_id = :tid"),
                    {"v": voice_name, "tid": user_id},
                )
            from core.voices import VOICES
            voice_info = VOICES.get(voice_name, {})
            await self._send_response(
                chat_id,
                f"Voz cambiada a *{voice_info.get('nombre', voice_name)}*\n"
                f"_{voice_info.get('descripcion', '')}_\n\n"
                f"Ahora todas tus preguntas serán respondidas desde esta perspectiva."
            )
        # Pantalla URL management (admin only)
        elif command == "/pantalla":
            if user_id not in settings.admin_ids:
                return
            import redis.asyncio as aioredis
            redis = aioredis.from_url(settings.redis_url, decode_responses=True)
            if not args:
                current = await redis.get("tavodebate:pantalla_url")
                if current:
                    await self._send_response(chat_id, f"🔗 Pantalla en vivo: {current}")
                else:
                    await self._send_response(chat_id, "No hay URL de pantalla configurada.\nUso: `/pantalla https://tu-url.trycloudflare.com`")
            else:
                url = args.strip()
                await redis.set("tavodebate:pantalla_url", url)
                await self._send_response(chat_id, f"🔗 URL de pantalla configurada:\n{url}")
            await redis.aclose()
        # PIN management (admin only)
        elif command == "/pin":
            if user_id not in settings.admin_ids:
                return
            import redis.asyncio as aioredis
            redis = aioredis.from_url(settings.redis_url, decode_responses=True)
            if not args:
                # Show current PIN or clear it
                current = await redis.get("tavodebate:access_pin")
                if current:
                    await self._send_response(chat_id, f"🔐 PIN activo: *{current}*\nPara quitar: `/pin off`")
                else:
                    await self._send_response(chat_id, "No hay PIN activo. Registro abierto.\nPara activar: `/pin 1234`")
            elif args.strip().lower() == "off":
                await redis.delete("tavodebate:access_pin")
                await self._send_response(chat_id, "🔓 PIN desactivado. Registro abierto para todos.")
            elif args.strip().isdigit() and len(args.strip()) == 4:
                await redis.set("tavodebate:access_pin", args.strip())
                await self._send_response(chat_id, f"🔐 PIN activado: *{args.strip()}*\nLos nuevos usuarios deben ingresar este código para registrarse.")
            else:
                await self._send_response(chat_id, "Uso: `/pin 1234` (4 dígitos) o `/pin off`")
            await redis.aclose()
        # Admin commands
        elif command in (
            "/broadcast", "/bomba", "/fakenews", "/presion", "/gabinete_remover",
            "/gabinete_amenaza", "/fase", "/ronda", "/tweet",
            "/llm", "/modo_test", "/briefing", "/pantalla",
            "/asignar_rol", "/roles", "/historial_votaciones",
        ):
            if user_id in settings.admin_ids:
                from handlers.admin_handlers import handle_admin_command
                await handle_admin_command(self, command, args, chat_id)
            else:
                await self._send_response(chat_id, "No tienes permisos de administrador.")
        else:
            await self._send_response(
                chat_id,
                "Comando no reconocido. Usa /help para ver los comandos disponibles."
            )

    async def _handle_message(self, user_id: int, chat_id: int, text: str):
        """Procesa mensaje de texto regular con LLM."""
        from core.memory_manager import build_system_prompt

        # Intercept ongoing alcalde interview before going to the regular LLM
        from handlers.ponencia_handler import handle_alcalde_interview_reply
        if await handle_alcalde_interview_reply(self, user_id, chat_id, text):
            return

        async with get_session() as session:
            # Get user from DB
            from sqlalchemy import text as sql_text
            result = await session.execute(
                sql_text("SELECT * FROM users WHERE telegram_id = :tid"),
                {"tid": user_id},
            )
            user = result.mappings().first()

            if not user:
                await self._send_response(
                    chat_id,
                    "Primero debes registrarte. Envía /start para comenzar."
                )
                return

            # Get active advisor and build prompt
            advisor_key = await self._get_active_advisor(user_id)
            voice = user.get("active_voice", "asesor_neutral")

            from core.advisors import TEAM_KEY

            if advisor_key == TEAM_KEY:
                # Team mode (orquestador): consulta paralela + síntesis
                from core.advisor_team import consult_team
                # Base system prompt without a specific advisor section
                base_system = await build_system_prompt(user, session, advisor_key=None)
                await self._send_response(
                    chat_id, "🧠 Tavo está coordinando a tu equipo..."
                )
                response = await consult_team(
                    self.llm, base_system, text, voice,
                )
            else:
                system_prompt = await build_system_prompt(
                    user, session, advisor_key=advisor_key
                )
                response = await self.llm.generate(
                    system_prompt, text, cache_voice=f"{voice}_{advisor_key}"
                )

                # Handle web search if LLM requested one (single-advisor path)
                import re
                search_match = re.search(r'<<<BUSCAR>>>(.*?)<<<FIN_BUSCAR>>>', response, re.DOTALL)
                if search_match:
                    query = search_match.group(1).strip()
                    from core.web_search import search_web
                    search_results = await search_web(query)
                    augmented = (
                        f"{text}\n\n--- RESULTADOS DE BÚSQUEDA WEB ---\n{search_results}\n\n"
                        "Usa estos resultados para complementar tu respuesta al participante."
                    )
                    response = await self.llm.generate(
                        system_prompt, augmented,
                        cache_voice=f"{voice}_{advisor_key}_search",
                        use_cache=False,
                    )

            # Clean LLM artifacts from response
            import re
            response = re.sub(r'<<<[^>]+>>>', '', response).strip()
            response = re.sub(r'\{[^}]*"tipo_alerta"[^}]*\}', '', response).strip()

            # Append map links for any mentioned municipalities
            from core.config import MUNICIPIOS_COORDS
            mentioned = []
            resp_lower = response.lower()
            for mun, (lat, lng) in MUNICIPIOS_COORDS.items():
                if mun.lower() in resp_lower:
                    mentioned.append((mun, lat, lng))
            if mentioned:
                links = "\n".join(
                    f"[{m} en mapa](https://maps.google.com/?q={la},{ln})"
                    for m, la, ln in mentioned[:5]
                )
                response += f"\n\n📍 *Ubicaciones:*\n{links}"

            # Save interaction with full location data
            result = await session.execute(
                sql_text(
                    "INSERT INTO interactions (user_id, telegram_id, nombre_concejal, "
                    "municipio, provincia, bancada_id, bancada_nombre, question, response, "
                    "voice_used, advisor_used) "
                    "VALUES (:uid, :tid, :nombre, :mun, :prov, :bid, :bname, :q, :r, :v, :adv) "
                    "RETURNING id"
                ),
                {
                    "uid": user["id"], "tid": user_id,
                    "nombre": user.get("nombre_completo", ""),
                    "mun": user.get("municipio", ""),
                    "prov": user.get("provincia", ""),
                    "bid": user.get("bancada_id"),
                    "bname": user.get("bancada_nombre", ""),
                    "q": text, "r": response, "v": voice,
                    "adv": advisor_key,
                },
            )
            interaction_id = result.scalar()

        # Publish event for Intel agent with location + coordinates
        from core.config import get_coords_for_municipio
        municipio = user.get("municipio", "")
        coords = get_coords_for_municipio(municipio)
        event_data = {
            "id": interaction_id,
            "user_id": user["id"],
            "telegram_id": user_id,
            "nombre_concejal": user.get("nombre_completo", ""),
            "municipio": municipio,
            "provincia": user.get("provincia", ""),
            "bancada_id": user.get("bancada_id"),
            "voice": voice,
            "question": text,
            "response": response,
        }
        if coords:
            event_data["lat"] = coords[0]
            event_data["lng"] = coords[1]
        await self.bus.publish("interaction:new", event_data)
        # Publish to pantalla for real-time map pin with coordinates
        if coords:
            await self.bus.raw.publish("interaction:live", json.dumps(event_data))

        # Refresh rolling session_summary every 5 interactions (background)
        asyncio.create_task(self._maybe_refresh_summary(user["id"], user_id))

        # Send response with advisor bar (equipo + 5 emoji buttons)
        from core.advisors import get_advisor_bar, ADVISORS, TEAM_KEY, TEAM_META
        if advisor_key == TEAM_KEY:
            advisor_label = f"\n\n_{TEAM_META['emoji']} {TEAM_META['nombre']}_"
        else:
            adv_info = ADVISORS.get(advisor_key, {})
            advisor_label = f"\n\n_{adv_info.get('emoji', '')} {adv_info.get('nombre', '')}_"
        bar = json.dumps({"inline_keyboard": get_advisor_bar()})
        await self._send_response(chat_id, response + advisor_label, reply_markup=bar)

        # Detect executable actions (tuits, enmiendas) and propose them
        # with approve-buttons. Tavo actúa SOLO cuando el usuario aprueba.
        try:
            from core.advisor_team import (
                extract_actions, store_pending_actions, build_action_buttons,
            )
            actions = extract_actions(response)
            if actions:
                action_id = await store_pending_actions(self.bus.raw, user_id, actions)
                buttons = build_action_buttons(action_id, actions)
                lines = [
                    "✨ *Acciones listas para ejecutar* (Tavo las hará si apruebas):",
                    "",
                ]
                for i, act in enumerate(actions, 1):
                    icon = "🐦" if act["type"] == "tuit" else "📝"
                    lines.append(f"{i}. {icon} _{act['text'][:200]}{'…' if len(act['text'])>200 else ''}_")
                await self._send_response(
                    chat_id,
                    "\n".join(lines),
                    reply_markup=json.dumps({"inline_keyboard": buttons}),
                )
        except Exception as e:
            logger.warning(f"Action extraction failed: {e}")

    async def _maybe_refresh_summary(self, db_user_id: int, telegram_id: int):
        """Resume la sesión del participante cada 5 interacciones.

        Guarda un resumen en users.session_summary para que los asesores
        nunca pierdan el contexto histórico, aunque la ventana del LLM se
        llene.
        """
        try:
            async with get_session() as session:
                from sqlalchemy import text as sql_text

                # Count total interactions
                total = (await session.execute(
                    sql_text("SELECT COUNT(*) FROM interactions WHERE user_id = :uid"),
                    {"uid": db_user_id},
                )).scalar() or 0

                # Only refresh every 5 interactions
                if total == 0 or total % 5 != 0:
                    return

                # Read last 15 interactions
                rows = (await session.execute(
                    sql_text(
                        "SELECT question, response, advisor_used "
                        "FROM interactions WHERE user_id = :uid "
                        "ORDER BY created_at DESC LIMIT 15"
                    ),
                    {"uid": db_user_id},
                )).mappings().all()

                previous = (await session.execute(
                    sql_text("SELECT session_summary FROM users WHERE id = :uid"),
                    {"uid": db_user_id},
                )).scalar() or ""

            history_text = "\n\n".join(
                f"[{r['advisor_used'] or '?'}] P: {(r['question'] or '')[:180]}\n"
                f"R: {(r['response'] or '')[:260]}"
                for r in reversed(rows)
            )
            system = (
                "Eres un redactor que mantiene la memoria del asesor de un "
                "participante en una simulación legislativa sobre el "
                "proyecto SIADR. Actualiza el resumen para que el próximo "
                "asesor sepa qué ha preguntado el participante, qué le han "
                "respondido, qué posición viene sosteniendo y qué tareas o "
                "compromisos quedan abiertos. Máximo 220 palabras, en "
                "bullets. Nada de saludos ni meta-comentarios."
            )
            user_msg = (
                f"Resumen previo:\n{previous or '(vacío)'}\n\n"
                f"Últimas interacciones (más recientes al final):\n\n{history_text}\n\n"
                "Redacta el resumen actualizado."
            )
            summary = await self.llm.generate(
                system, user_msg, temperature=0.4, max_tokens=350, use_cache=False,
            )

            async with get_session() as session:
                from sqlalchemy import text as sql_text
                await session.execute(
                    sql_text(
                        "UPDATE users SET session_summary = :s, "
                        "last_summary_at = NOW() WHERE id = :uid"
                    ),
                    {"s": summary[:4000], "uid": db_user_id},
                )
        except Exception as e:
            logger.warning(f"Session summary refresh failed for {telegram_id}: {e}")

    async def _handle_voice(self, user_id: int, chat_id: int, message: dict):
        """Envía nota de voz al Agente Audio para transcripción."""
        voice = message["voice"]
        file_id = voice["file_id"]

        await self._send_response(chat_id, "Transcribiendo tu nota de voz...")

        await self.bus.publish("audio:transcribe", {
            "user_id": user_id,
            "chat_id": chat_id,
            "file_id": file_id,
            "callback_channel": f"audio:result:{user_id}",
        })

        # Wait for transcription result
        pubsub = self.bus.pubsub()
        await pubsub.subscribe(f"audio:result:{user_id}")
        try:
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    data = json.loads(msg["data"])
                    transcript = data.get("transcript", "")
                    if transcript:
                        await self._handle_message(user_id, chat_id, transcript)
                    else:
                        await self._send_response(
                            chat_id, "No pude transcribir tu nota de voz. Intenta de nuevo."
                        )
                    break
        finally:
            await pubsub.unsubscribe(f"audio:result:{user_id}")

    async def _process_callback(self, callback: dict):
        """Procesa callback queries (botones inline)."""
        callback_id = callback["id"]
        chat_id = callback["message"]["chat"]["id"]
        user_id = callback["from"]["id"]
        data = callback.get("data", "")

        if data.startswith("vote_"):
            from handlers.voting_handlers import handle_vote_callback
            await handle_vote_callback(self, user_id, chat_id, data, callback_id)
        elif data.startswith("approve_"):
            from handlers.admin_handlers import handle_approval_callback
            await handle_approval_callback(self, user_id, chat_id, data, callback_id)
        elif data.startswith("onboard_"):
            from handlers.onboarding import handle_onboard_callback
            await handle_onboard_callback(self, user_id, chat_id, data, callback_id)
        elif data.startswith((
            "preview_", "send_", "cancel_",
            "regen_draft_", "confirm_modo_test", "confirm_briefing",
            "ronda_start_", "pantalla_mode_",
        )):
            if user_id in settings.admin_ids:
                from handlers.admin_handlers import handle_admin_callback
                await handle_admin_callback(self, user_id, chat_id, data, callback_id)
        elif data.startswith("advisor_"):
            advisor_key = data.replace("advisor_", "")
            await self._set_active_advisor(user_id, advisor_key)
            from core.advisors import ADVISORS, TEAM_KEY, TEAM_META, get_advisor_bar
            bar = json.dumps({"inline_keyboard": get_advisor_bar()})
            if advisor_key == TEAM_KEY:
                await self._send_response(
                    chat_id,
                    f"{TEAM_META['emoji']} Modo *{TEAM_META['nombre']}* activado.\n\n"
                    "Tus preguntas se enrutarán automáticamente a los "
                    "asesores especializados relevantes. Respuesta "
                    "consolidada con la voz de cada uno.\n\n"
                    "Para hablar con un asesor específico, usa /asesores.",
                    reply_markup=bar,
                )
            else:
                adv = ADVISORS.get(advisor_key, {})
                await self._send_response(
                    chat_id,
                    f"{adv.get('emoji', '')} Asesor cambiado a *{adv.get('nombre', advisor_key)}*\n\n"
                    "Ahora estás en modo directo con un solo especialista.\n"
                    "Para volver al modo equipo, toca 🧠 abajo o usa /asesores.",
                    reply_markup=bar,
                )
        elif data == "presi_oficializar":
            from handlers.presidencia_handler import handle_oficializar
            await handle_oficializar(self, user_id, chat_id)
        elif data == "presi_regenerar":
            from handlers.presidencia_handler import handle_regenerar
            await handle_regenerar(self, user_id, chat_id)
        elif data.startswith("tavo_do_"):
            try:
                _, _, action_id, idx_str = data.split("_", 3)
                idx = int(idx_str)
            except (ValueError, IndexError):
                return
            from core.advisor_team import load_pending_actions
            actions = await load_pending_actions(self.bus.raw, user_id, action_id)
            if not actions or idx >= len(actions):
                await self._send_response(
                    chat_id, "Esa acción ya expiró o no existe."
                )
                return
            act = actions[idx]

            if act["type"] == "tuit":
                # Get user info for the tweet
                async with get_session() as session:
                    from sqlalchemy import text as sql_text
                    result = await session.execute(
                        sql_text(
                            "SELECT nombre_completo, municipio, bancada_nombre "
                            "FROM users WHERE telegram_id = :tid"
                        ),
                        {"tid": user_id},
                    )
                    u = result.mappings().first()
                if not u:
                    await self._send_response(chat_id, "Debes registrarte primero.")
                    return
                handle = "@" + "".join(w.capitalize() for w in u["nombre_completo"].split()[:2])
                await self._publish_tweet({
                    "author": handle,
                    "text": act["text"],
                    "municipio": u["municipio"],
                    "bancada": u["bancada_nombre"],
                    "is_concejal": True,
                    "is_quote": False,
                    "is_reply": False,
                })
                await self._send_response(
                    chat_id,
                    f"🐦 Tavo publicó tu tuit:\n\n*{handle}*: {act['text'][:200]}"
                )
            elif act["type"] == "enmienda":
                from handlers.proposal_handlers import handle_proponer
                await handle_proponer(self, user_id, chat_id, act["text"])
                await self._send_response(
                    chat_id, "📝 Tavo propuso la enmienda a tu nombre."
                )
        elif data.startswith(("tweet_reply_", "tweet_quote_")):
            mode = "reply" if data.startswith("tweet_reply_") else "quote"
            try:
                tid = int(data.rsplit("_", 1)[1])
            except ValueError:
                return
            recent = await self._get_recent_tweets(30)
            target = next((t for t in recent if t.get("tweet_id") == tid), None)
            if not target:
                await self._send_response(chat_id, "Ese tuit ya no está disponible. Usa /tuitear para ver los actuales.")
                return
            await self._save_tweet_context(user_id, mode, target)
            verb = "respondiendo" if mode == "reply" else "citando"
            preview = (target.get("text", "") or "")[:100]
            await self._send_response(
                chat_id,
                f"🐦 Estás {verb} a *{target.get('author', '?')}*:\n"
                f"_{preview}…_\n\n"
                f"Escribe `/tuitear <tu texto>` para publicar. Tienes 5 min."
            )
        elif data.startswith("assign_role_"):
            if user_id in settings.admin_ids:
                rol_key = data.replace("assign_role_", "")
                from core.config import ROLES
                rol_info = ROLES.get(rol_key, {})
                await self._send_response(
                    chat_id,
                    f"Escribe el nombre del participante para asignar *{rol_info.get('nombre', rol_key)}*:\n\n"
                    f"`/asignar_rol <nombre> {rol_key}`"
                )
        elif data.startswith("fase_"):
            if user_id in settings.admin_ids:
                fase_key = data.split("_", 1)[1]
                from handlers.onboarding import FASES
                fase_info = FASES.get(fase_key)
                if fase_info:
                    await self.bus.publish("simulation:command", {
                        "action": "phase_change",
                        "args": {"phase": fase_key},
                    })
                    await self._send_response(chat_id, f"✅ Fase cambiada a: *{fase_info['nombre']}*")
                    from handlers.phase_handlers import get_participants_summary
                    summary = await get_participants_summary()
                    await self._send_response(chat_id, summary)
                    from handlers.admin_handlers import _execute_phase_actions
                    await _execute_phase_actions(self, fase_key, chat_id)

    async def _interpret_admin_nl(self, text: str) -> str | None:
        """Interpreta texto natural del admin como comando.
        Returns the command string (e.g. '/bomba') or None if not a command."""
        t = text.lower().strip()

        # Quick keyword matching (no LLM needed)
        keyword_map = [
            (["bomba", "dato bomba", "lanza bomba", "enviar bomba"], "/bomba"),
            (["fake", "fakenews", "noticia falsa", "lanzar fake"], "/fakenews"),
            (["tweet", "tuit", "publicar tweet", "twit"], "/tweet"),
            (["fase", "cambiar fase", "pasar a", "siguiente fase"], "/fase"),
            (["estado", "estadísticas", "stats", "cómo va", "como va", "cuántos", "cuantos"], "/estado"),
            (["broadcast", "mensaje a todos", "enviar a todos", "comunicado"], "/broadcast"),
            (["ronda", "timer", "temporizador", "cronómetro", "minutos"], "/ronda"),
            (["votación", "votacion", "abrir votación", "votar"], "/fase votacion"),
            (["presión", "presion", "amenaza", "presionar"], "/presion"),
            (["alerta", "alertar"], "/alerta"),
            (["pantalla", "modo pantalla", "cambiar pantalla"], "/pantalla"),
            (["ayuda", "help", "comandos", "qué puedo hacer", "que puedo hacer"], "/help"),
        ]

        for keywords, cmd in keyword_map:
            for kw in keywords:
                if kw in t:
                    # Extract remaining text after keyword as args
                    rest = t
                    for kw2 in keywords:
                        rest = rest.replace(kw2, "").strip()
                    # Handle specific patterns
                    if cmd == "/bomba" and not rest:
                        return "/bomba"
                    if cmd == "/fakenews" and not rest:
                        return "/fakenews"
                    if cmd == "/tweet" and not rest:
                        return "/tweet"
                    if rest:
                        return f"{cmd} {rest}"
                    return cmd

        return None

    async def _handle_tuitear(self, user_id: int, chat_id: int, text: str):
        """Permite a cualquier concejal publicar un tweet en la pantalla."""
        # Sin texto: mostrar menú con tuits recientes para citar/responder
        if not text.strip():
            await self._show_tuitear_menu(chat_id)
            return

        # Get user info
        async with get_session() as session:
            from sqlalchemy import text as sql_text
            result = await session.execute(
                sql_text("SELECT nombre_completo, municipio, bancada_nombre FROM users WHERE telegram_id = :tid"),
                {"tid": user_id},
            )
            user = result.mappings().first()

        if not user:
            await self._send_response(chat_id, "Debes registrarte primero con /start")
            return

        handle = "@" + "".join(w.capitalize() for w in user["nombre_completo"].split()[:2])
        municipio = user["municipio"]
        bancada = user["bancada_nombre"]
        tweet_text = text.strip()

        # Check pending reply/quote context
        ctx = await self._load_tweet_context(user_id)

        payload = {
            "author": handle,
            "text": tweet_text,
            "municipio": municipio,
            "bancada": bancada,
            "is_concejal": True,
            "is_quote": False,
            "is_reply": False,
        }
        if ctx:
            if ctx["mode"] == "reply":
                payload["is_reply"] = True
                payload["reply_to_id"] = ctx["target_id"]
                payload["reply_to_author"] = ctx["target_author"]
            elif ctx["mode"] == "quote":
                payload["is_quote"] = True
                payload["quote_to_id"] = ctx["target_id"]
                payload["quote_to_author"] = ctx["target_author"]
                payload["quote_to_text"] = ctx.get("target_text", "")
        else:
            # Legacy formats still supported
            payload["is_quote"] = tweet_text.upper().startswith("RT ")
            payload["is_reply"] = tweet_text.startswith("@") and not payload["is_quote"]

        await self._publish_tweet(payload)

        suffix = ""
        if ctx:
            suffix = f" (en {'respuesta a' if ctx['mode'] == 'reply' else 'cita a'} {ctx['target_author']})"
        await self._send_response(
            chat_id,
            f"🐦 Tu tweet fue publicado en la pantalla{suffix}:\n\n*{handle}*: {tweet_text[:200]}"
        )

    async def _publish_tweet(self, payload: dict) -> int:
        """Asigna tweet_id incremental y persiste en Redis para permitir citas/respuestas."""
        tweet_id = await self.bus.raw.incr("tavodebate:tweet_counter")
        payload["tweet_id"] = int(tweet_id)
        # Persist for future lookups (last 30)
        await self.bus.raw.lpush(
            "tavodebate:recent_tweets", json.dumps(payload)
        )
        await self.bus.raw.ltrim("tavodebate:recent_tweets", 0, 29)
        await self.bus.publish("tweet:new", payload)
        return int(tweet_id)

    async def _save_tweet_context(self, user_id: int, mode: str, target: dict):
        """Guarda el contexto de respuesta/cita pendiente del usuario (TTL 5 min)."""
        await self.bus.raw.setex(
            f"tweet_ctx:{user_id}",
            300,
            json.dumps({
                "mode": mode,
                "target_id": target["tweet_id"],
                "target_author": target["author"],
                "target_text": target.get("text", "")[:200],
            }),
        )

    async def _load_tweet_context(self, user_id: int) -> dict | None:
        """Lee y limpia el contexto pendiente de tuit."""
        raw = await self.bus.raw.get(f"tweet_ctx:{user_id}")
        if not raw:
            return None
        await self.bus.raw.delete(f"tweet_ctx:{user_id}")
        if isinstance(raw, bytes):
            raw = raw.decode()
        try:
            return json.loads(raw)
        except Exception:
            return None

    async def _get_recent_tweets(self, limit: int = 8) -> list[dict]:
        """Devuelve los tuits recientes desde Redis."""
        raw_list = await self.bus.raw.lrange("tavodebate:recent_tweets", 0, limit - 1)
        tweets = []
        for raw in raw_list:
            if isinstance(raw, bytes):
                raw = raw.decode()
            try:
                tweets.append(json.loads(raw))
            except Exception:
                continue
        return tweets

    async def _show_tuitear_menu(self, chat_id: int):
        """Muestra tuits recientes con botones para responder o citar."""
        recent = await self._get_recent_tweets(8)
        if not recent:
            await self._send_response(
                chat_id,
                "🐦 *¿Qué quieres tuitear?*\n\n"
                "Todavía no hay tuits en la pantalla para citar. "
                "Escribe: `/tuitear Tu opinión aquí`"
            )
            return

        keyboard = []
        text_lines = ["🐦 *Últimos tuits en pantalla:*", ""]
        for i, tw in enumerate(recent, 1):
            tid = tw.get("tweet_id")
            if not tid:
                continue
            snippet = (tw.get("text", "") or "")[:70].replace("\n", " ")
            text_lines.append(f"*{i}.* {tw.get('author', '?')}: {snippet}…")
            keyboard.append([
                {"text": f"💬 Responder #{tid}", "callback_data": f"tweet_reply_{tid}"},
                {"text": f"🔄 Citar #{tid}", "callback_data": f"tweet_quote_{tid}"},
            ])
        text_lines += [
            "",
            "Elige un tuit para *responder* o *citar*, o envía `/tuitear <tu texto>` para un tuit nuevo."
        ]

        await self.bus.stream_add("telegram:outgoing", {
            "chat_id": str(chat_id),
            "text": "\n".join(text_lines),
            "parse_mode": "Markdown",
            "reply_markup": json.dumps({"inline_keyboard": keyboard}),
        })

    async def _get_active_advisor(self, telegram_id: int) -> str:
        """Obtiene el asesor activo del usuario desde Redis (default: equipo)."""
        from core.advisors import TEAM_KEY
        key = f"advisor:{telegram_id}"
        advisor = await self.bus.raw.get(key)
        if isinstance(advisor, bytes):
            advisor = advisor.decode()
        return advisor or TEAM_KEY

    async def _set_active_advisor(self, telegram_id: int, advisor_key: str):
        """Guarda el asesor activo en Redis con TTL de 24h."""
        key = f"advisor:{telegram_id}"
        await self.bus.raw.setex(key, 86400, advisor_key)

    async def _send_response(self, chat_id: int, text: str, parse_mode: str = "Markdown",
                             reply_markup: str = None):
        """Envía respuesta al usuario via telegram:outgoing stream."""
        data = {
            "chat_id": str(chat_id),
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            data["reply_markup"] = reply_markup
        await self.bus.stream_add("telegram:outgoing", data)

    async def shutdown(self):
        if self.llm:
            await self.llm.close()
        await super().shutdown()
