"""Handlers de Telegram para documentos legislativos PDF."""

import json
import logging
import os
import tempfile

from db.database import get_session

logger = logging.getLogger("handlers.documents")


async def _get_user_and_evento(user_id: int) -> tuple:
    """Retorna (user_dict, evento_dict) o (None, None) si el usuario no existe."""
    async with get_session() as session:
        from sqlalchemy import text as sql_text
        result = await session.execute(
            sql_text("""
                SELECT u.*, e.nombre as evento_nombre, e.tipo as evento_tipo,
                       e.proyecto_nombre, e.municipio as evento_municipio
                FROM users u
                LEFT JOIN eventos e ON e.id = u.evento_id
                WHERE u.telegram_id = :tid
            """),
            {"tid": user_id},
        )
        row = result.mappings().first()
    if not row:
        return None, None
    user = dict(row)
    evento = {
        "nombre": row.get("evento_nombre") or "Cuerpo Legislativo",
        "tipo": row.get("evento_tipo") or "concejo",
        "proyecto_nombre": row.get("proyecto_nombre") or "Proyecto de Acuerdo",
        "municipio": row.get("evento_municipio") or "",
    }
    return user, evento


async def _send_pdf(agent, chat_id: int, pdf_bytes: bytes, filename: str, caption: str = ""):
    """Escribe el PDF a un archivo temporal y lo encola en telegram:outgoing."""
    tmp = tempfile.NamedTemporaryFile(
        delete=False, suffix=".pdf", prefix="tavo_", dir="/tmp"
    )
    try:
        tmp.write(pdf_bytes)
        tmp.flush()
        tmp.close()
        await agent.bus.stream_add("telegram:outgoing", {
            "type": "document",
            "chat_id": str(chat_id),
            "file_path": tmp.name,
            "filename": filename,
            "caption": caption,
        })
    except Exception:
        os.unlink(tmp.name)
        raise


async def handle_documento_ponencia(agent, user_id: int, chat_id: int):
    """Genera y envía en PDF la última ponencia del usuario."""
    user, evento = await _get_user_and_evento(user_id)
    if not user:
        await agent._send_response(chat_id, "No estás registrado. Usa /start")
        return

    async with get_session() as session:
        from sqlalchemy import text as sql_text
        result = await session.execute(
            sql_text("""
                SELECT response FROM interactions
                WHERE user_id = :uid
                  AND question LIKE '/preparar_ponencia%'
                ORDER BY created_at DESC
                LIMIT 1
            """),
            {"uid": user["id"]},
        )
        row = result.fetchone()

    contenido = row[0] if row else None
    if not contenido:
        await agent._send_response(
            chat_id,
            "No tienes una ponencia registrada. Usa /preparar\\_ponencia para redactarla primero.",
        )
        return

    await agent._send_response(chat_id, "Generando documento PDF...")
    try:
        from services.document_generator import render_ponencia_pdf
        pdf_bytes = render_ponencia_pdf(user, evento, contenido)
        nombre_archivo = f"Ponencia_{user['nombre_completo'].replace(' ', '_')}.pdf"
        await _send_pdf(agent, chat_id, pdf_bytes, nombre_archivo,
                        caption=f"📄 Ponencia — {user['nombre_completo']}")
    except RuntimeError as e:
        await agent._send_response(chat_id, f"Error generando PDF: {e}")


async def handle_documento_propuesta(agent, user_id: int, chat_id: int, propuesta_id: int):
    """Genera y envía en PDF una propuesta de enmienda específica."""
    user, evento = await _get_user_and_evento(user_id)
    if not user:
        await agent._send_response(chat_id, "No estás registrado. Usa /start")
        return

    async with get_session() as session:
        from sqlalchemy import text as sql_text
        result = await session.execute(
            sql_text("""
                SELECT * FROM proposals
                WHERE id = :pid AND user_id = :uid
            """),
            {"pid": propuesta_id, "uid": user["id"]},
        )
        propuesta = result.mappings().first()

    if not propuesta:
        await agent._send_response(chat_id, f"Propuesta #{propuesta_id} no encontrada.")
        return

    await agent._send_response(chat_id, "Generando documento PDF...")
    try:
        from services.document_generator import render_propuesta_pdf
        pdf_bytes = render_propuesta_pdf(user, evento, dict(propuesta))
        nombre_archivo = f"Enmienda_{propuesta_id}_{user['nombre_completo'].replace(' ', '_')}.pdf"
        await _send_pdf(agent, chat_id, pdf_bytes, nombre_archivo,
                        caption=f"📄 Propuesta de Enmienda N.º {propuesta_id}")
    except RuntimeError as e:
        await agent._send_response(chat_id, f"Error generando PDF: {e}")


async def handle_mis_documentos(agent, user_id: int, chat_id: int):
    """Lista documentos disponibles del usuario con botones de descarga."""
    user, evento = await _get_user_and_evento(user_id)
    if not user:
        await agent._send_response(chat_id, "No estás registrado. Usa /start")
        return

    async with get_session() as session:
        from sqlalchemy import text as sql_text

        tiene_ponencia = await session.execute(
            sql_text("""
                SELECT 1 FROM interactions
                WHERE user_id = :uid AND question LIKE '/preparar_ponencia%'
                LIMIT 1
            """),
            {"uid": user["id"]},
        )
        hay_ponencia = tiene_ponencia.fetchone() is not None

        props_result = await session.execute(
            sql_text("""
                SELECT id, texto_propuesta, articulo_afectado, apoyos
                FROM proposals WHERE user_id = :uid
                ORDER BY created_at DESC
            """),
            {"uid": user["id"]},
        )
        propuestas = props_result.mappings().all()

    if not hay_ponencia and not propuestas:
        await agent._send_response(
            chat_id,
            "No tienes documentos disponibles aún.\n\n"
            "• Usa /preparar\\_ponencia para redactar tu ponencia\n"
            "• Usa /proponer para registrar propuestas de enmienda",
        )
        return

    keyboard = []
    if hay_ponencia:
        keyboard.append([{"text": "📜 Descargar mi ponencia", "callback_data": "doc_ponencia"}])
    for p in propuestas:
        preview = (p["texto_propuesta"] or "")[:40].strip()
        if len(p["texto_propuesta"] or "") > 40:
            preview += "…"
        keyboard.append([{
            "text": f"📄 Enmienda #{p['id']} — {preview}",
            "callback_data": f"doc_propuesta_{p['id']}",
        }])

    texto = f"*Mis documentos* — {user['nombre_completo']}\n\n"
    if hay_ponencia:
        texto += "📜 Ponencia registrada\n"
    texto += f"📄 {len(propuestas)} propuesta(s) de enmienda\n\n"
    texto += "Elige el documento que deseas descargar en PDF:"

    reply_markup = json.dumps({"inline_keyboard": keyboard})
    await agent._send_response(chat_id, texto, reply_markup=reply_markup)
