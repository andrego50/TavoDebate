"""TavoDebate - Motor de Text-to-Speech con Edge-TTS."""

import logging
import hashlib
import tempfile
from pathlib import Path

import edge_tts

logger = logging.getLogger("services.tts")

# Voces colombianas Edge-TTS
VOICES_MAP = {
    "ciudadano_rural": "es-CO-GonzaloNeural",
    "experto_tech": "es-CO-SalomeNeural",
    "contraloria": "es-CO-GonzaloNeural",
    "empresa_tech": "es-CO-SalomeNeural",
    "alcalde": "es-CO-GonzaloNeural",
    "broadcast": "es-CO-SalomeNeural",
}

CACHE_DIR = Path(tempfile.gettempdir()) / "tavodebate_tts_cache"


async def generate_tts(text: str, voice_key: str = "broadcast") -> Path:
    """Genera audio TTS y devuelve la ruta del archivo MP3."""
    CACHE_DIR.mkdir(exist_ok=True)

    voice = VOICES_MAP.get(voice_key, "es-CO-GonzaloNeural")
    text_hash = hashlib.md5(f"{voice}:{text}".encode()).hexdigest()
    out_path = CACHE_DIR / f"{text_hash}.mp3"

    if out_path.exists():
        logger.debug(f"TTS cache hit: {text_hash}")
        return out_path

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_path))
    logger.info(f"TTS generated: {voice_key} -> {out_path.name}")
    return out_path


async def pregenerate_bombs(bombs: list[dict]) -> dict[str, Path]:
    """Pre-genera audio para todas las bombas informativas."""
    results = {}
    for bomb in bombs:
        key = f"bomb_{bomb.get('id', 'unknown')}"
        path = await generate_tts(bomb["text"], "broadcast")
        results[key] = path
    return results


async def pregenerate_phase_announcements(phases: list[str]) -> dict[str, Path]:
    """Pre-genera audio para anuncios de fase."""
    results = {}
    for phase in phases:
        text = f"Atención concejales. Iniciamos la fase de {phase}."
        path = await generate_tts(text, "broadcast")
        results[f"phase_{phase}"] = path
    return results
