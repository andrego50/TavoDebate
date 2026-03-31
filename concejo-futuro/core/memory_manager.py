"""TavoDebate - Construcción del system prompt con memoria adaptativa."""

import json

from core.config import BANCADAS, ROLES
from core.voices import PROMPT_BASE, get_voice_prompt

# Extra instructions per role group
ROLE_INSTRUCTIONS = {
    "gobierno": (
        "Tu participante es parte del EQUIPO DE GOBIERNO que defiende el proyecto SIADR. "
        "Ayúdale a construir argumentos sólidos A FAVOR del proyecto. "
        "Puede pedirte que redactes comunicados, tweets de defensa, respuestas a críticas, "
        "o datos que fortalezcan la ponencia. Actúa como su asesor estratégico."
    ),
    "sociedad_civil": (
        "Tu participante representa a la SOCIEDAD CIVIL. "
        "Ayúdale a formular preguntas incisivas, denuncias, exigencias y propuestas desde su perspectiva comunitaria. "
        "Puede pedirte que redactes tweets, comunicados de prensa, o argumentos para presionar a los concejales."
    ),
    "empresa": (
        "Tu participante representa al SECTOR PRIVADO/EMPRESARIAL. "
        "Ayúdale a defender intereses empresariales, presentar beneficios económicos, "
        "o responder a acusaciones de conflicto de interés. Puede pedirte tweets o comunicados."
    ),
    "control": (
        "Tu participante es un ÓRGANO DE CONTROL (Contraloría, Personería, Veeduría). "
        "Ayúdale a formular alertas, advertencias legales, exigencias de transparencia "
        "y fiscalización. Sé riguroso con datos y normatividad."
    ),
    "concejo": (
        "Tu participante es un CONCEJAL que votará el proyecto. "
        "Ayúdale a investigar, preparar su ponencia, formular preguntas y tomar una decisión informada."
    ),
}


async def build_system_prompt(user: dict, session=None) -> str:
    """Construye el system prompt personalizado para un participante."""
    bancada_id = user.get("bancada_id", 1)
    bancada = BANCADAS.get(bancada_id, BANCADAS[1])
    voice = user.get("active_voice", "ciudadano")
    rol_key = user.get("rol", "concejal") or "concejal"
    rol_info = ROLES.get(rol_key, ROLES["concejal"])

    # Build base prompt with user context
    base = PROMPT_BASE.format(
        nombre_concejal=user.get("nombre_completo", "Participante"),
        municipio=user.get("municipio", "Desconocido"),
        provincia=user.get("provincia", "Desconocida"),
        bancada_nombre=bancada["nombre"],
        bancada_posicion=bancada["posicion"],
        intereses_resumen=user.get("intereses_resumen", "No especificados"),
        temas_interes=", ".join(user.get("temas_interes", []) or []),
    )

    # Add role context
    role_section = (
        f"\n--- ROL EN EL EJERCICIO ---\n"
        f"Rol: {rol_info['nombre']}\n"
        f"Descripción: {rol_info['descripcion']}\n"
        f"{'Puede votar el proyecto.' if rol_info['puede_votar'] else 'NO vota, pero participa activamente en el debate.'}\n"
        f"\n{ROLE_INSTRUCTIONS.get(rol_info.get('grupo', 'concejo'), '')}"
    )

    # Add voice prompt
    voice_prompt = get_voice_prompt(voice)

    # Add live context if available
    live_context = ""
    if session:
        live_context = await _get_live_context(user, bancada_id, session)

    return f"{base}{role_section}\n\n--- VOZ ACTIVA ---\n{voice_prompt}\n\n{live_context}"


async def _get_live_context(user: dict, bancada_id: int, session) -> str:
    """Obtiene contexto en vivo del debate."""
    from sqlalchemy import text as sql_text

    parts = []

    # Get debate state
    try:
        result = await session.execute(
            sql_text("SELECT global_summary, temperature, hottest_topic FROM debate_state WHERE id = 1")
        )
        state = result.mappings().first()
        if state and state["global_summary"] != "El debate aún no ha comenzado.":
            parts.append(
                f"--- ESTADO DEL DEBATE ---\n"
                f"Resumen: {state['global_summary']}\n"
                f"Temperatura: {state['temperature']}\n"
                f"Tema más caliente: {state['hottest_topic']}"
            )
    except Exception:
        pass

    # Get bancada state
    try:
        result = await session.execute(
            sql_text("SELECT summary FROM bancada_state WHERE bancada_id = :bid"),
            {"bid": bancada_id},
        )
        bancada_state = result.scalar()
        if bancada_state and bancada_state != "Sin actividad aún.":
            parts.append(f"--- ESTADO DE TU BANCADA ---\n{bancada_state}")
    except Exception:
        pass

    # Get recent interactions count
    try:
        result = await session.execute(
            sql_text(
                "SELECT COUNT(*) FROM interactions "
                "WHERE user_id = :uid AND created_at > NOW() - INTERVAL '30 minutes'"
            ),
            {"uid": user.get("id")},
        )
        recent_count = result.scalar() or 0
        if recent_count > 0:
            parts.append(f"Este participante ha hecho {recent_count} consultas en los últimos 30 minutos.")
    except Exception:
        pass

    return "\n\n".join(parts)
