"""TavoDebate - Handlers de presión por tema."""

import json
import logging

from db.database import get_session

logger = logging.getLogger("handlers.pressure")

TIPOS_PRESION = {
    "comunicado": {"emoji": "📋", "header": "COMUNICADO OFICIAL", "gravedad": "baja"},
    "carta": {"emoji": "✉️", "header": "CARTA ABIERTA", "gravedad": "baja"},
    "respaldo": {"emoji": "🤝", "header": "RESPALDO PÚBLICO", "gravedad": "positiva"},
    "protesta": {"emoji": "📢", "header": "AVISO DE PROTESTA", "gravedad": "media"},
    "huelga": {"emoji": "⛔", "header": "DECLARACIÓN DE HUELGA", "gravedad": "alta"},
    "demanda": {"emoji": "⚖️", "header": "ACCIÓN JUDICIAL", "gravedad": "alta"},
    "tutela": {"emoji": "🛡️", "header": "ACCIÓN DE TUTELA", "gravedad": "alta"},
    "bloqueo": {"emoji": "🚧", "header": "BLOQUEO DE VÍAS", "gravedad": "critica"},
    "retiro_apoyo": {"emoji": "🚪", "header": "RETIRO DE APOYO", "gravedad": "alta"},
    "ultimatum": {"emoji": "⏰", "header": "ULTIMÁTUM", "gravedad": "critica"},
}
