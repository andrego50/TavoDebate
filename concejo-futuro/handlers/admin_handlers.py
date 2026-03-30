"""TavoDebate - Comandos admin de Telegram."""

import json
import logging

from core.config import settings
from db.database import get_session

logger = logging.getLogger("handlers.admin")


async def handle_admin_command(agent, command: str, args: str, chat_id: int):
    """Enruta comandos admin al orquestador via Redis."""
    cmd = command.lstrip("/")

    if cmd == "broadcast":
        await agent.bus.publish("control:command", {
            "action": "broadcast",
            "args": {"message": args, "target": "all"},
        })
        await agent._send_response(chat_id, "Broadcast enviado.")

    elif cmd == "bomba":
        try:
            bomb_id = int(args.strip())
        except ValueError:
            await agent._send_response(chat_id, "Uso: /bomba <1-8>")
            return
        await agent.bus.publish("control:command", {
            "action": "bomb",
            "args": {"bomb_id": bomb_id},
        })
        await agent._send_response(chat_id, f"Bomba #{bomb_id} enviada.")

    elif cmd == "fakenews":
        try:
            news_id = int(args.strip())
        except ValueError:
            await agent._send_response(chat_id, "Uso: /fakenews <1-6>")
            return
        await agent.bus.publish("control:command", {
            "action": "fakenews",
            "args": {"news_id": news_id},
        })
        await agent._send_response(chat_id, f"Fake news #{news_id} enviada.")

    elif cmd == "presion":
        # /presion <tipo> <tema> <actor> <mensaje>
        parts = args.split('"')
        if len(parts) >= 4:
            header = parts[0].strip().split()
            tipo = header[0] if len(header) > 0 else "comunicado"
            tema = header[1] if len(header) > 1 else "general"
            actor = parts[1]
            mensaje = parts[3] if len(parts) > 3 else parts[1]
        else:
            tipo, tema, actor, mensaje = "comunicado", "general", "Sistema", args
        await agent.bus.publish("control:command", {
            "action": "pressure",
            "args": {"type": tipo, "tema": tema, "actor": actor, "message": mensaje},
        })
        await agent._send_response(chat_id, f"Presión '{tipo}' enviada.")

    elif cmd == "gabinete_remover":
        gab_id = args.strip()
        await agent.bus.publish("control:command", {
            "action": "gabinete",
            "args": {"gabinete_action": "remover", "gabinete_id": gab_id},
        })
        await agent._send_response(chat_id, f"Gabinete: {gab_id} removido.")

    elif cmd == "gabinete_amenaza":
        parts = args.strip().split(" ", 2)
        gab_id = parts[0] if parts else ""
        bancada_id = int(parts[1]) if len(parts) > 1 else 0
        mensaje = parts[2] if len(parts) > 2 else ""
        await agent.bus.publish("control:command", {
            "action": "gabinete",
            "args": {
                "gabinete_action": "amenaza",
                "gabinete_id": gab_id,
                "bancada_id": bancada_id,
                "message": mensaje,
            },
        })
        await agent._send_response(chat_id, f"Amenaza de gabinete enviada a bancada {bancada_id}.")

    elif cmd == "alerta":
        await agent.bus.publish("control:command", {
            "action": "alert",
            "args": {"alert_type": "defensoria", "message": args},
        })
        await agent._send_response(chat_id, "Alerta enviada.")

    elif cmd == "fase":
        if not args.strip():
            # Show inline keyboard with phases
            from handlers.onboarding import FASES
            keyboard = []
            for fase_key, fase_info in FASES.items():
                keyboard.append([{
                    "text": f"{fase_info['nombre']}",
                    "callback_data": f"fase_{fase_key}",
                }])
            await agent.bus.stream_add("telegram:outgoing", {
                "chat_id": str(chat_id),
                "text": "🏛️ *Selecciona la fase del ejercicio:*",
                "parse_mode": "Markdown",
                "reply_markup": json.dumps({"inline_keyboard": keyboard}),
            })
        else:
            from handlers.onboarding import FASES
            fase_key = args.strip().lower()
            fase_info = FASES.get(fase_key)
            if not fase_info:
                await agent._send_response(chat_id, f"Fase '{fase_key}' no existe.")
                return
            await agent.bus.publish("simulation:command", {
                "action": "phase_change",
                "args": {"phase": fase_key},
            })
            await agent._send_response(chat_id, f"✅ Fase cambiada a: *{fase_info['nombre']}*")
            # Send participants summary
            from handlers.phase_handlers import get_participants_summary
            summary = await get_participants_summary()
            await agent._send_response(chat_id, summary)

    elif cmd == "ronda":
        try:
            minutes = int(args.strip())
        except ValueError:
            minutes = 5
        await agent.bus.publish("simulation:command", {
            "action": "start_timer",
            "args": {"name": "Ronda", "minutes": minutes},
        })
        await agent._send_response(chat_id, f"Timer de {minutes} min iniciado.")

    elif cmd == "tweet":
        await agent.bus.publish("tweet:new", {
            "author": "@ConcejoCund",
            "text": args,
            "is_manual": True,
        })
        await agent._send_response(chat_id, "Tweet publicado en pantalla.")

    elif cmd == "llm":
        parts = args.strip().split()
        if parts and parts[0] == "switch" and len(parts) > 1:
            provider = parts[1]
            if agent.llm:
                await agent.llm.switch_primary(provider)
            await agent._send_response(chat_id, f"LLM primario: {provider}")
        elif parts and parts[0] == "status":
            await agent._send_response(chat_id, "Estado LLM: operativo")
        else:
            await agent._send_response(chat_id, "Uso: /llm switch <deepseek|kimi> | /llm status")

    elif cmd == "modo_test":
        await _create_test_users(agent, chat_id)

    elif cmd == "briefing":
        await agent.bus.publish("intel:command", {
            "action": "force_briefing",
            "args": {},
        })
        await agent._send_response(chat_id, "Briefing forzado solicitado.")

    elif cmd == "pantalla":
        await agent.bus.publish("pantalla:command", {
            "action": "layout_change",
            "args": {"mode": args.strip()},
        })
        await agent._send_response(chat_id, f"Pantalla: modo {args.strip()}")

    else:
        await agent._send_response(chat_id, f"Comando admin no reconocido: {cmd}")


async def handle_approval_callback(agent, user_id: int, chat_id: int, data: str, callback_id: str):
    """Procesa callbacks de aprobación de propuestas proactivas."""
    if user_id not in settings.admin_ids:
        return

    parts = data.split("_")
    action = parts[1] if len(parts) > 1 else ""
    proposal_idx = parts[2] if len(parts) > 2 else "0"

    if action == "yes":
        await agent._send_response(chat_id, f"Propuesta #{proposal_idx} aprobada. Ejecutando...")
    elif action == "no":
        await agent._send_response(chat_id, f"Propuesta #{proposal_idx} rechazada.")


async def _create_test_users(agent, chat_id: int):
    """Crea 10 concejales ficticios para pruebas."""
    from core.config import BANCADAS, PROVINCIAS_MUNICIPIOS

    test_users = [
        ("Juan Pérez", "Fusagasugá", "Sumapaz", 1, ["agro", "infraestructura"]),
        ("María López", "Zipaquirá", "Sabana Centro", 2, ["ambiente", "agua"]),
        ("Carlos Gómez", "Girardot", "Alto Magdalena", 3, ["agro", "educacion"]),
        ("Ana Rodríguez", "Facatativá", "Sabana Occidente", 4, ["tecnologia", "comercio"]),
        ("Pedro Martínez", "Chía", "Sabana Centro", 5, ["hacienda", "infraestructura"]),
        ("Laura Torres", "Soacha", "Soacha", 6, ["derechos_humanos", "seguridad"]),
        ("Diego Hernández", "La Mesa", "Tequendama", 1, ["turismo", "cultura"]),
        ("Camila Vargas", "Pacho", "Rionegro", 2, ["salud", "mujer_genero"]),
        ("Andrés Castro", "Guaduas", "Bajo Magdalena", 3, ["transporte", "mineria"]),
        ("Sofía Ramírez", "Chocontá", "Almeidas", 4, ["juventud", "educacion"]),
    ]

    async with get_session() as session:
        from sqlalchemy import text as sql_text
        for i, (nombre, mun, prov, bid, temas) in enumerate(test_users):
            tid = 900000000 + i
            bancada = BANCADAS[bid]
            await session.execute(
                sql_text(
                    "INSERT INTO users (telegram_id, username, nombre_completo, municipio, "
                    "provincia, bancada_id, bancada_nombre, temas_interes, onboarding_complete) "
                    "VALUES (:tid, :un, :name, :mun, :prov, :bid, :bname, :temas, true) "
                    "ON CONFLICT (telegram_id) DO NOTHING"
                ),
                {
                    "tid": tid, "un": f"test_user_{i}",
                    "name": nombre, "mun": mun, "prov": prov,
                    "bid": bid, "bname": bancada["nombre"],
                    "temas": temas,
                },
            )

    await agent._send_response(chat_id, "10 usuarios de prueba creados.")
