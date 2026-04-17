"""TavoDebate - Orquestador del equipo de asesores.

Cuando el usuario está en modo "equipo" (default), su pregunta se enruta
en paralelo a los asesores relevantes y se consolida en una respuesta
única con la voz de cada especialista + una síntesis final.
"""

import asyncio
import logging
import re

from core.advisors import ADVISORS, pick_relevant_advisors

logger = logging.getLogger("core.advisor_team")


SYNTHESIS_SYSTEM = (
    "Eres TAVO, jefe de gabinete del participante en el Concejo del "
    "Futuro (simulación SIADR/catastro rural, Cundinamarca). Tu trabajo es "
    "compilar las respuestas de los asesores especializados en una "
    "recomendación ejecutiva firmada por ti.\n\n"
    "REGLAS:\n"
    "- Mantén la identidad de cada asesor: preserva su formato y vocabulario "
    "propios (citas legales, cifras, tuits, jugadas políticas, componentes "
    "técnicos). No uniformes el estilo.\n"
    "- Si dos asesores se contradicen, señálalo explícitamente y propón una "
    "salida.\n"
    "- Cierra SIEMPRE con un bloque «🎯 TAVO — Recomendación del gabinete» "
    "de 2-4 líneas que integre los hallazgos y diga al participante su "
    "próxima acción concreta.\n"
    "- No inventes información que ningún asesor mencionó.\n"
)


async def _query_single_advisor(llm, base_system: str, advisor_key: str,
                                 question: str, voice: str) -> tuple[str, str]:
    """Llama al LLM con el system-prompt del asesor especificado.

    Devuelve (advisor_key, respuesta). Maneja <<<BUSCAR>>> si el asesor
    la pide.
    """
    adv = ADVISORS[advisor_key]
    specialized_system = (
        base_system
        + "\n\n--- ASESOR ACTIVO ---\n"
        + adv["prompt"]
        + "\n\nBÚSQUEDA WEB: si necesitas información actualizada para "
        "responder, escribe en tu respuesta <<<BUSCAR>>>consulta<<<FIN_BUSCAR>>>."
    )
    cache_voice = f"{voice}_{advisor_key}_team"

    try:
        response = await llm.generate(
            specialized_system, question,
            cache_voice=cache_voice, max_tokens=500,
        )
    except Exception as e:
        logger.warning(f"Advisor {advisor_key} failed: {e}")
        return (advisor_key, f"_({adv['nombre']} no disponible en este turno)_")

    # Honor one web-search round per advisor, just like the single-advisor path
    match = re.search(r'<<<BUSCAR>>>(.*?)<<<FIN_BUSCAR>>>', response, re.DOTALL)
    if match:
        try:
            from core.web_search import search_web
            query = match.group(1).strip()
            results = await search_web(query, max_results=3)
            augmented = (
                f"{question}\n\n--- RESULTADOS DE BÚSQUEDA WEB ---\n"
                f"{results}\n\nUsa estos resultados y RESPONDE con tu formato."
            )
            response = await llm.generate(
                specialized_system, augmented,
                use_cache=False, max_tokens=500,
                cache_voice=f"{cache_voice}_search",
            )
        except Exception as e:
            logger.warning(f"Web search for {advisor_key} failed: {e}")

    # Strip any remaining tags
    response = re.sub(r'<<<[^>]+>>>', '', response).strip()
    return (advisor_key, response)


async def consult_team(llm, base_system: str, question: str,
                        voice: str) -> str:
    """Consulta a los asesores relevantes y devuelve la respuesta
    consolidada lista para enviar al usuario.
    """
    relevant = pick_relevant_advisors(question, max_advisors=3)
    logger.info(f"Equipo: consultando {relevant} para '{question[:60]}'")

    # Parallel fan-out
    tasks = [
        _query_single_advisor(llm, base_system, key, question, voice)
        for key in relevant
    ]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    # Build per-advisor sections with clear visual separation
    sections = []
    raw_compendium = []
    for key, resp in results:
        adv = ADVISORS[key]
        header = f"━━━ {adv['emoji']} *{adv['nombre']}* ━━━"
        sections.append(f"{header}\n\n{resp}")
        raw_compendium.append(f"{adv['nombre']}:\n{resp}")

    advisors_block = "\n\n".join(sections)

    # Final synthesis
    synthesis_user = (
        f"Pregunta del participante:\n{question}\n\n"
        f"Respuestas de sus asesores:\n\n"
        + "\n\n---\n\n".join(raw_compendium)
        + "\n\nCompila la recomendación ejecutiva del gabinete "
        "(solo el bloque «🎯 RECOMENDACIÓN DEL GABINETE», 2-4 líneas)."
    )
    try:
        synthesis = await llm.generate(
            SYNTHESIS_SYSTEM, synthesis_user,
            temperature=0.5, max_tokens=220, use_cache=False,
        )
        synthesis = synthesis.strip()
    except Exception as e:
        logger.warning(f"Synthesis failed: {e}")
        synthesis = ""

    header = (
        "🧠 *Tavo — respuesta del gabinete*\n"
        f"_Consultados: {', '.join(ADVISORS[k]['nombre'] for k in relevant)}_\n"
    )
    final = f"{header}\n{advisors_block}"
    if synthesis:
        final += f"\n\n━━━━━━━━━━━━━━\n{synthesis}"

    return final
