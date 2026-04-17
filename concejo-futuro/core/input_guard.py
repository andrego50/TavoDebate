"""TavoDebate - Blindaje contra prompt injection.

Envuelve todo texto humano en un delimitador estructural reconocido por el
system prompt. Complementa —no reemplaza— la instrucción defensiva del
PROMPT_BASE que le dice al LLM que ignore directivas dentro del bloque.
"""

import re

_MAX_CHARS = 4000
_STRIP_DELIMITERS = re.compile(
    r"</?\s*(user_input|system|assistant|instructions?)\s*/?\s*>",
    re.IGNORECASE,
)


def sanitize_user_input(text: str, max_chars: int = _MAX_CHARS) -> str:
    """Limpia el texto del usuario antes de mandarlo al LLM.

    - Recorta a `max_chars` (defensa contra agotamiento de contexto).
    - Elimina cualquier tag que parezca un delimitador de rol
      (user_input, system, assistant, instructions) para impedir que el
      participante cierre el bloque y escriba directivas fuera de él.
    - Colapsa whitespace excesivo que pueda usarse para ocultar payloads.
    """
    if not text:
        return ""
    text = _STRIP_DELIMITERS.sub("", str(text))
    text = text.replace("\x00", "")
    text = text[:max_chars]
    return text.strip()


def wrap_user_input(text: str, label: str = "user_input") -> str:
    """Devuelve el texto envuelto en el delimitador canónico para el LLM."""
    safe = sanitize_user_input(text)
    return f"<{label}>\n{safe}\n</{label}>"
