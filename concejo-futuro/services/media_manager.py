"""TavoDebate - Gestión de archivos multimedia."""

import logging
from pathlib import Path
import tempfile

logger = logging.getLogger("services.media")

MEDIA_DIR = Path(tempfile.gettempdir()) / "tavodebate_media"


def ensure_dirs():
    """Crea directorios de media si no existen."""
    for sub in ("audio", "images", "certificates", "uploads"):
        (MEDIA_DIR / sub).mkdir(parents=True, exist_ok=True)


def get_audio_path(filename: str) -> Path:
    ensure_dirs()
    return MEDIA_DIR / "audio" / filename


def get_image_path(filename: str) -> Path:
    ensure_dirs()
    return MEDIA_DIR / "images" / filename


def get_cert_path(filename: str) -> Path:
    ensure_dirs()
    return MEDIA_DIR / "certificates" / filename


def get_upload_path(filename: str) -> Path:
    ensure_dirs()
    return MEDIA_DIR / "uploads" / filename


def cleanup_temp_files(max_age_hours: int = 4):
    """Limpia archivos temporales antiguos."""
    import time

    ensure_dirs()
    cutoff = time.time() - (max_age_hours * 3600)
    count = 0

    for subdir in MEDIA_DIR.iterdir():
        if not subdir.is_dir():
            continue
        for f in subdir.iterdir():
            if f.stat().st_mtime < cutoff:
                f.unlink()
                count += 1

    if count:
        logger.info(f"Cleaned up {count} temp media files")
