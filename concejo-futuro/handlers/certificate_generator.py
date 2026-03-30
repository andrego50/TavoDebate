"""TavoDebate - Generación de certificados PDF."""

import logging
from datetime import datetime

from core.config import BANCADAS
from db.database import get_session

logger = logging.getLogger("handlers.certificate")

CERTIFICATE_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
@page {{ size: A4 landscape; margin: 2cm; }}
body {{ font-family: 'Georgia', serif; text-align: center; color: #333; }}
.border {{ border: 3px double #1a4d2e; padding: 40px; margin: 20px; }}
h1 {{ color: #1a4d2e; font-size: 28px; margin-bottom: 5px; }}
h2 {{ color: #666; font-size: 18px; font-weight: normal; margin-top: 5px; }}
.name {{ font-size: 32px; color: #1a4d2e; font-weight: bold; margin: 30px 0 10px; }}
.municipio {{ font-size: 18px; color: #555; }}
.body-text {{ font-size: 14px; line-height: 1.8; margin: 25px 40px; text-align: justify; }}
.metrics {{ font-size: 13px; color: #666; margin: 20px 0; }}
.footer {{ font-size: 12px; color: #999; margin-top: 30px; }}
.signature {{ margin-top: 40px; font-size: 14px; }}
.signature-line {{ border-top: 1px solid #333; width: 250px; margin: 0 auto; padding-top: 5px; }}
</style>
</head>
<body>
<div class="border">
    <h1>TavoDebate — El Concejo del Futuro</h1>
    <h2>Simulación Legislativa sobre Inteligencia Artificial</h2>

    <p style="font-size: 16px; margin-top: 30px;">Certifica que</p>

    <div class="name">{nombre}</div>
    <div class="municipio">Concejal de {municipio} ({provincia}) — {bancada}</div>

    <div class="body-text">
        Participó activamente en el Taller de Simulación Legislativa
        "El Concejo del Futuro" sobre el Proyecto de Acuerdo 001-2026:
        Sistema de Inteligencia Artificial para la Priorización del
        Alumbrado Público Rural y la Agricultura de Precisión (SIADR)
        en el Departamento de Cundinamarca.
    </div>

    <div class="metrics">
        Consultas realizadas: {total_consultas} |
        Propuestas presentadas: {propuestas} |
        Voto emitido: {voto}
    </div>

    <div class="signature">
        <div class="signature-line">
            Andrés Pérez Coronado, PhD<br>
            CEO FastAnalytics | Profesor U. Rosario<br>
            Facilitador del Taller
        </div>
    </div>

    <div class="footer">
        Fecha: {fecha} | Cundinamarca, Colombia
    </div>
</div>
</body>
</html>
"""


async def handle_certificado(agent, user_id: int, chat_id: int):
    """Genera y envía certificado PDF personalizado."""
    async with get_session() as session:
        from sqlalchemy import text as sql_text

        result = await session.execute(
            sql_text("SELECT * FROM users WHERE telegram_id = :tid"),
            {"tid": user_id},
        )
        user = result.mappings().first()
        if not user:
            await agent._send_response(chat_id, "No estás registrado. Usa /start")
            return

        # Count interactions
        result = await session.execute(
            sql_text("SELECT COUNT(*) FROM interactions WHERE user_id = :uid"),
            {"uid": user["id"]},
        )
        total = result.scalar() or 0

    bancada = BANCADAS.get(user["bancada_id"], {})

    html = CERTIFICATE_HTML.format(
        nombre=user["nombre_completo"],
        municipio=user["municipio"],
        provincia=user["provincia"],
        bancada=bancada.get("nombre", ""),
        total_consultas=total,
        propuestas=user.get("propuestas_count", 0),
        voto=user.get("voto_proyecto", "No emitido"),
        fecha=datetime.now().strftime("%d de %B de %Y"),
    )

    await agent._send_response(
        chat_id,
        "Generando tu certificado... (esta función requiere Playwright en el servidor)",
    )
    logger.info(f"Certificate requested by {user['nombre_completo']}")
