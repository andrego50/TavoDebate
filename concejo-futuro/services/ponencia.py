"""TavoDebate - Servicio de análisis y gestión de ponencias."""

import logging
import json

from core.llm_client import LLMClient

logger = logging.getLogger("services.ponencia")

ANALYZE_PONENCIA_PROMPT = """Analiza esta ponencia presentada por un concejal en el debate del SIADR.

Ponencia (transcripción de audio):
"{text}"

Concejal: {user_name} | Bancada: {bancada}

Responde en JSON:
{{
  "resumen": "resumen ejecutivo en 3 líneas",
  "posicion": "a_favor|en_contra|ambiguo",
  "articulos_mencionados": [1, 2, 3],
  "propuestas_concretas": ["lista de propuestas"],
  "fortalezas": ["puntos fuertes del argumento"],
  "debilidades": ["puntos débiles o vacíos"],
  "preguntas_sugeridas": ["preguntas que otros concejales podrían hacer"]
}}
"""


async def analyze_ponencia(
    llm: LLMClient,
    transcription: str,
    user_name: str = "",
    bancada: str = "",
) -> dict:
    """Analiza una ponencia transcrita y genera análisis estructurado."""
    prompt = ANALYZE_PONENCIA_PROMPT.format(
        text=transcription[:3000],  # Limitar longitud
        user_name=user_name,
        bancada=bancada,
    )

    response = await llm.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
        return {
            "resumen": transcription[:200],
            "posicion": "ambiguo",
            "articulos_mencionados": [],
            "propuestas_concretas": [],
            "fortalezas": [],
            "debilidades": [],
            "preguntas_sugeridas": [],
        }
