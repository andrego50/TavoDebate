"""TavoDebate - Generador de briefings ejecutivos."""

import logging
import json

from core.llm_client import LLMClient

logger = logging.getLogger("services.briefing")

BRIEFING_PROMPT = """Eres un analista político generando un briefing ejecutivo para el facilitador
de la sesión legislativa sobre el SIADR en Cundinamarca.

Datos de las últimas interacciones:
- Total interacciones: {total}
- Sentimiento promedio: {sentimiento}
- Temas más discutidos: {temas}
- Posiciones: A favor={a_favor}, En contra={en_contra}, Neutral={neutral}
- Bancadas más activas: {bancadas}
- Cambios de posición recientes: {cambios}

Genera un briefing ejecutivo de máximo 5 líneas con:
1. Estado general del debate
2. Tensiones identificadas
3. Oportunidades de consenso
4. Recomendación de siguiente acción
"""


async def generate_briefing(
    llm: LLMClient,
    stats: dict,
) -> str:
    """Genera un briefing ejecutivo basado en estadísticas."""
    prompt = BRIEFING_PROMPT.format(
        total=stats.get("total", 0),
        sentimiento=stats.get("sentimiento", "neutral"),
        temas=", ".join(stats.get("temas", [])),
        a_favor=stats.get("a_favor", 0),
        en_contra=stats.get("en_contra", 0),
        neutral=stats.get("neutral", 0),
        bancadas=", ".join(stats.get("bancadas_activas", [])),
        cambios=stats.get("cambios", "ninguno"),
    )

    response = await llm.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )

    return response


PROACTIVE_PROMPT = """Basado en el estado del debate SIADR:
- Tensiones: {tensiones}
- Temas calientes: {temas}
- Bancadas polarizadas: {bancadas}

Propón UNA acción proactiva que el facilitador podría tomar.
Responde en JSON:
{{
  "tipo": "broadcast|bomb|pressure|negotiation",
  "target": "all|bancada_nombre",
  "mensaje": "el mensaje a enviar",
  "razon": "por qué esta acción"
}}
"""


async def generate_proactive_proposal(
    llm: LLMClient,
    context: dict,
) -> dict:
    """Genera una propuesta proactiva de acción."""
    prompt = PROACTIVE_PROMPT.format(
        tensiones=context.get("tensiones", "ninguna"),
        temas=", ".join(context.get("temas", [])),
        bancadas=", ".join(context.get("bancadas", [])),
    )

    response = await llm.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
        return {"tipo": "broadcast", "target": "all", "mensaje": response[:200], "razon": "generado automáticamente"}
