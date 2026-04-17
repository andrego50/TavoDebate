"""TavoDebate - Orquestador del equipo de asesores.

Cuando el usuario está en modo "equipo" (default), su pregunta se enruta
en paralelo a los asesores relevantes y se consolida en una respuesta
única con la voz de cada especialista + una síntesis final.
"""

import asyncio
import logging
import re
import uuid

from core.advisors import ADVISORS, pick_relevant_advisors


# Patterns that the advisors output when they propose an executable action.
TUIT_PATTERN = re.compile(
    r'🐦\s*TUIT PROPUESTO[:\s]*\n\s*[«"]?(.+?)[»"]?\s*(?=\n\n|\n[\*\-🎯📰🎙️⚔️━]|\Z)',
    re.DOTALL | re.IGNORECASE,
)
ENMIENDA_PATTERN = re.compile(
    r'📝\s*ENMIENDA PROPUESTA[:\s]+(.+?)(?=\n\n|\n[\*\-🎯━]|\Z)',
    re.DOTALL | re.IGNORECASE,
)


def extract_actions(response: str) -> list[dict]:
    """Devuelve acciones ejecutables (tuits, enmiendas) que los asesores
    hayan propuesto dentro de la respuesta consolidada.
    """
    actions: list[dict] = []
    for m in TUIT_PATTERN.finditer(response):
        text = m.group(1).strip().strip('"').strip("«»").strip()
        text = re.sub(r'\s+', ' ', text)[:280]
        if 10 < len(text) <= 280:
            actions.append({"type": "tuit", "text": text})
    for m in ENMIENDA_PATTERN.finditer(response):
        text = m.group(1).strip()
        text = re.sub(r'\s+', ' ', text)[:500]
        if 15 < len(text) <= 500:
            actions.append({"type": "enmienda", "text": text})
    # Deduplicate by (type, text)
    seen = set()
    out = []
    for a in actions:
        key = (a["type"], a["text"])
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out


async def store_pending_actions(redis, user_id: int, actions: list[dict]) -> str:
    """Guarda las acciones detectadas en Redis con ID efímero (10 min)."""
    action_id = uuid.uuid4().hex[:8]
    import json
    await redis.setex(
        f"tavo_actions:{user_id}:{action_id}",
        600,
        json.dumps(actions),
    )
    return action_id


async def load_pending_actions(redis, user_id: int, action_id: str) -> list[dict]:
    import json
    raw = await redis.get(f"tavo_actions:{user_id}:{action_id}")
    if not raw:
        return []
    if isinstance(raw, bytes):
        raw = raw.decode()
    try:
        return json.loads(raw)
    except Exception:
        return []


def build_action_buttons(action_id: str, actions: list[dict]) -> list:
    """Inline keyboard rows que proponen cada acción al usuario."""
    rows = []
    for i, act in enumerate(actions):
        if act["type"] == "tuit":
            label = f"🐦 Publicar tuit: {act['text'][:40]}…"
            rows.append([{
                "text": label,
                "callback_data": f"tavo_do_{action_id}_{i}",
            }])
        elif act["type"] == "enmienda":
            label = f"📝 Proponer enmienda: {act['text'][:40]}…"
            rows.append([{
                "text": label,
                "callback_data": f"tavo_do_{action_id}_{i}",
            }])
    if rows:
        rows.append([{
            "text": "❌ No ejecutar ninguna",
            "callback_data": "cancel_action",
        }])
    return rows

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
