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

            # Save interaction
            result = await session.execute(
                sql_text(
                    "INSERT INTO interactions (user_id, question, response, voice_used) "
                    "VALUES (:uid, :q, :r, :v) RETURNING id"
                ),
                {"uid": user["id"], "q": text, "r": response, "v": voice},
            )
            interaction_id = result.scalar()

        # Publish event for Intel agent
        await self.bus.publish("interaction:new", {
            "id": interaction_id,
            "user_id": user["id"],
            "telegram_id": user_id,
            "bancada_id": user.get("bancada_id"),
            "voice": voice,
            "question": text,
            "response": response,
        })

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
