"""TavoDebate - Agente Audio (Whisper + TTS)."""

import asyncio
import json
import logging
import os
from pathlib import Path

import httpx

from agents.base_agent import BaseAgent
from core.config import settings

logger = logging.getLogger("agent.audio")

# Edge-TTS Colombian voices
TTS_VOICES = {
    "broadcast": "es-CO-GonzaloNeural",
    "defensoria": "es-CO-SalomeNeural",
    "contraloria": "es-CO-GonzaloNeural",
    "sic": "es-CO-SalomeNeural",
    "alcalde": "es-CO-GonzaloNeural",
    "default": "es-CO-GonzaloNeural",
}


class AudioAgent(BaseAgent):
    name = "audio"

    def __init__(self):
        super().__init__()
        self.audio_cache_dir = Path("/app/audio_cache")

    async def setup(self):
        await super().setup()
        self.audio_cache_dir.mkdir(parents=True, exist_ok=True)
        # Pre-generate TTS for bombs and phases
        asyncio.create_task(self._pregenerate_tts())

    async def start(self):
        """Escucha canales de audio."""
        pubsub = self.bus.pubsub()
        await pubsub.subscribe(
            "audio:transcribe",
            "audio:generate_tts",
            "ponencia:record",
        )

        logger.info("Audio agent listening")
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                channel = message["channel"]
                if isinstance(channel, bytes):
                    channel = channel.decode()
                data = json.loads(message["data"] if isinstance(message["data"], str) else message["data"].decode())

                if channel == "audio:transcribe":
                    await self._handle_transcribe(data)
                elif channel == "audio:generate_tts":
                    await self._handle_tts(data)
                elif channel == "ponencia:record":
                    await self._handle_ponencia(data)
            except Exception as e:
                logger.error(f"Audio agent error: {e}", exc_info=True)

    async def _handle_transcribe(self, data: dict):
        """Transcribe audio con OpenAI Whisper API."""
        file_id = data.get("file_id")
        callback_channel = data.get("callback_channel")

        try:
            # Download file from Telegram
            audio_path = await self._download_telegram_file(file_id)

            # Transcribe with Whisper
            transcript = await self._transcribe_whisper(audio_path)

            # Publish result
            await self.bus.publish(callback_channel, {
                "transcript": transcript,
                "user_id": data.get("user_id"),
            })

            # Cleanup
            if os.path.exists(audio_path):
                os.remove(audio_path)

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            if callback_channel:
                await self.bus.publish(callback_channel, {
                    "transcript": "",
                    "error": str(e),
                })

    async def _download_telegram_file(self, file_id: str) -> str:
        """Descarga archivo de Telegram."""
        async with httpx.AsyncClient() as client:
            # Get file path
            resp = await client.get(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/getFile",
                params={"file_id": file_id},
            )
            file_path = resp.json()["result"]["file_path"]

            # Download file
            resp = await client.get(
                f"https://api.telegram.org/file/bot{settings.telegram_bot_token}/{file_path}"
            )
            local_path = f"/tmp/{file_id}.ogg"
            with open(local_path, "wb") as f:
                f.write(resp.content)

            return local_path

    async def _transcribe_whisper(self, audio_path: str) -> str:
        """Transcribe con OpenAI Whisper API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(audio_path, "rb") as f:
                resp = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    files={"file": ("audio.ogg", f, "audio/ogg")},
                    data={"model": "whisper-1", "language": "es"},
                )
            resp.raise_for_status()
            return resp.json()["text"]

    async def _handle_tts(self, data: dict):
        """Genera audio con Edge-TTS."""
        text = data.get("text", "")
        voice_key = data.get("voice", "default")
        send_to = data.get("send_to", [])

        voice = TTS_VOICES.get(voice_key, TTS_VOICES["default"])
        audio_path = await self._generate_tts(text, voice)

        if audio_path and send_to:
            # Send via Telegram
            async with httpx.AsyncClient() as client:
                for user_id in send_to:
                    try:
                        with open(audio_path, "rb") as f:
                            await client.post(
                                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendVoice",
                                data={"chat_id": str(user_id)},
                                files={"voice": ("audio.mp3", f, "audio/mpeg")},
                            )
                    except Exception as e:
                        logger.error(f"Failed to send voice to {user_id}: {e}")

    async def _handle_ponencia(self, data: dict):
        """Transcribe y analiza ponencia."""
        file_id = data.get("file_id")
        bancada_id = data.get("bancada_id")

        try:
            audio_path = await self._download_telegram_file(file_id)
            transcript = await self._transcribe_whisper(audio_path)

            await self.bus.publish("ponencia:analyzed", {
                "bancada_id": bancada_id,
                "transcript": transcript,
                "timestamp": data.get("timestamp"),
            })

            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception as e:
            logger.error(f"Ponencia error: {e}")

    async def _generate_tts(self, text: str, voice: str) -> str | None:
        """Genera audio con edge-tts."""
        import hashlib
        filename = hashlib.md5(f"{voice}:{text}".encode()).hexdigest()
        output_path = str(self.audio_cache_dir / f"{filename}.mp3")

        if os.path.exists(output_path):
            return output_path

        try:
            import edge_tts
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            return output_path
        except Exception as e:
            logger.error(f"TTS generation error: {e}")
            return None

    async def _pregenerate_tts(self):
        """Pre-genera audios al iniciar."""
        from core.bombs import BOMBS

        items = []
        for bomb_id, bomb in BOMBS.items():
            items.append((f"bomba_{bomb_id}", bomb["text"]))

        items.extend([
            ("fase_ponencia", "Fase de ponencia del alcalde. Escuchen al proponente."),
            ("fase_debate", "Fase de debate abierto. Las bancadas tienen la palabra."),
            ("fase_votacion", "Fase de votación. Emitan su voto."),
            ("timer_5min", "Quedan 5 minutos."),
            ("timer_1min", "Queda 1 minuto."),
            ("timer_fin", "Tiempo agotado."),
        ])

        voice = TTS_VOICES["broadcast"]
        for name, text in items:
            path = str(self.audio_cache_dir / f"{name}.mp3")
            if not os.path.exists(path):
                try:
                    import edge_tts
                    communicate = edge_tts.Communicate(text, voice)
                    await communicate.save(path)
                    logger.info(f"Pre-generated TTS: {name}")
                except Exception as e:
                    logger.error(f"Pre-gen TTS error for {name}: {e}")
