"""TavoDebate - Motor proactivo de intervenciones."""

import logging
from datetime import datetime

logger = logging.getLogger("services.proactive")

# Reglas de intervención proactiva basadas en estado del debate
PROACTIVE_RULES = [
    {
        "condition": "silence",
        "threshold": 120,  # segundos sin actividad
        "action": "broadcast",
        "message": "El debate parece haberse enfriado. ¿Alguna bancada quiere intervenir?",
    },
    {
        "condition": "polarization",
        "threshold": 0.8,  # índice de polarización
        "action": "negotiation_suggest",
        "message": "Se detecta alta polarización. Se sugiere abrir mesa de negociación.",
    },
    {
        "condition": "low_participation",
        "threshold": 0.3,  # % de concejales activos
        "action": "broadcast",
        "message": "Solo {active}% de los concejales han participado. ¡Queremos escuchar a todos!",
    },
    {
        "condition": "single_topic",
        "threshold": 5,  # mensajes consecutivos sobre el mismo tema
        "action": "topic_redirect",
        "message": "Se ha discutido mucho sobre {topic}. ¿Qué opinan sobre los demás artículos?",
    },
]


def evaluate_rules(state: dict) -> list[dict]:
    """Evalúa las reglas proactivas contra el estado actual del debate."""
    triggered = []

    # Silencio
    last_activity = state.get("last_activity")
    if last_activity:
        silence = (datetime.now() - last_activity).total_seconds()
        if silence > 120:
            triggered.append({
                "rule": "silence",
                "action": "broadcast",
                "message": PROACTIVE_RULES[0]["message"],
            })

    # Baja participación
    total_users = state.get("total_users", 150)
    active_users = state.get("active_users", 0)
    if total_users > 0:
        participation = active_users / total_users
        if participation < 0.3:
            triggered.append({
                "rule": "low_participation",
                "action": "broadcast",
                "message": PROACTIVE_RULES[2]["message"].format(
                    active=int(participation * 100)
                ),
            })

    # Polarización
    favor = state.get("positions", {}).get("a_favor", 0)
    contra = state.get("positions", {}).get("en_contra", 0)
    total_pos = favor + contra
    if total_pos > 10:
        balance = min(favor, contra) / max(favor, contra) if max(favor, contra) > 0 else 0
        if balance > 0.8:  # Muy equilibrado = alta polarización
            triggered.append({
                "rule": "polarization",
                "action": "negotiation_suggest",
                "message": PROACTIVE_RULES[1]["message"],
            })

    return triggered
