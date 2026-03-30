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
            "/gabinete_amenaza", "/alerta", "/fase", "/ronda", "/tweet",
            "/llm", "/modo_test", "/briefing", "/pantalla",
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

            # Build prompt and generate
            system_prompt = await build_system_prompt(user, session)
            voice = user.get("active_voice", "asesor_neutral")
            response = await self.llm.generate(
                system_prompt, text, cache_voice=voice
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
                    "voice_used) "
                    "VALUES (:uid, :tid, :nombre, :mun, :prov, :bid, :bname, :q, :r, :v) "
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

        await self._send_response(chat_id, response)

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

    async def _send_response(self, chat_id: int, text: str, parse_mode: str = "Markdown"):
        """Envía respuesta al usuario via telegram:outgoing stream."""
        await self.bus.stream_add("telegram:outgoing", {
            "chat_id": str(chat_id),
            "text": text,
            "parse_mode": parse_mode,
        })

    async def shutdown(self):
        if self.llm:
            await self.llm.close()
        await super().shutdown()
