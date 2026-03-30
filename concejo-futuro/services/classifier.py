"""TavoDebate - Clasificador de interacciones con LLM."""

import logging
import json

from core.llm_client import LLMClient

logger = logging.getLogger("services.classifier")

CLASSIFY_PROMPT = """Analiza esta interacción de un concejal en el debate del SIADR.

Concejal: {user_name} | Bancada: {bancada} | Voz: {voice}
Mensaje: "{message}"

Responde SOLO en JSON con:
{{
  "sentimiento": "positivo|negativo|neutral|mixto",
  "temas": ["lista", "de", "temas"],
  "posicion_siadr": "a_favor|en_contra|neutral|ambiguo",
  "intensidad": 0.0-1.0,
  "resumen": "resumen en 1 línea"
}}

Temas válidos: alumbrado, agro_precision, iot, presupuesto, corrupcion,
consulta_previa, brecha_digital, datos_personales, gobernacion, contraloria,
medioambiente, seguridad, participacion, transparencia, empleo, salud,
educacion, vias, turismo, ganaderia, mineria, agua, vivienda, genero, juventud
"""


async def classify_interaction(
    llm: LLMClient,
    message: str,
    user_name: str = "",
    bancada: str = "",
    voice: str = "",
) -> dict:
    """Clasifica una interacción usando el LLM."""
    prompt = CLASSIFY_PROMPT.format(
        user_name=user_name,
        bancada=bancada,
        voice=voice,
        message=message,
    )

    response = await llm.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # Intentar extraer JSON del response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
        logger.warning(f"Could not parse classification: {response[:100]}")
        return {
            "sentimiento": "neutral",
            "temas": [],
            "posicion_siadr": "neutral",
            "intensidad": 0.5,
            "resumen": message[:80],
        }


INTERESTS_PROMPT = """Clasifica los intereses de este concejal basado en su descripción libre.

Descripción: "{text}"

Responde SOLO con un JSON array de máximo 5 temas de esta lista:
["alumbrado", "agro_precision", "iot", "presupuesto", "corrupcion",
"consulta_previa", "brecha_digital", "datos_personales", "gobernacion",
"contraloria", "medioambiente", "seguridad", "participacion", "transparencia",
"empleo", "salud", "educacion", "vias", "turismo", "ganaderia", "mineria",
"agua", "vivienda", "genero", "juventud"]
"""


async def classify_interests(llm: LLMClient, text: str) -> list[str]:
    """Clasifica intereses de texto libre en categorías."""
    prompt = INTERESTS_PROMPT.format(text=text)
    response = await llm.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    try:
        result = json.loads(response)
        if isinstance(result, list):
            return result[:5]
    except json.JSONDecodeError:
        pass
    return ["participacion"]
