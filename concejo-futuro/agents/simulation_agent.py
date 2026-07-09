"""TavoDebate - Agente Simulación (timeline + timer)."""

import asyncio
import json
import logging
from datetime import datetime, timedelta

from agents.base_agent import BaseAgent
from core.timeline import TIMELINE
from core.stakeholders import STAKEHOLDERS

logger = logging.getLogger("agent.simulation")


class SimulationAgent(BaseAgent):
    name = "simulation"

    def __init__(self):
        super().__init__()
        self.start_time = None
        self.paused = False
        self.current_timer = None
        self.current_phase = None
        self.fired_events = set()  # indices of TIMELINE events already fired

    async def start(self):
        self.start_time = datetime.now()

        # Start loops
        asyncio.create_task(self._timer_loop())
        asyncio.create_task(self._timeline_loop())

        # Listen for commands
        pubsub = self.bus.pubsub()
        await pubsub.subscribe("simulation:control", "simulation:command")

        logger.info("Simulation agent running")
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                channel = message["channel"]
                if isinstance(channel, bytes):
                    channel = channel.decode()
                data = json.loads(
                    message["data"] if isinstance(message["data"], str)
                    else message["data"].decode()
                )

                if channel == "simulation:control":
                    await self._handle_control(data)
                elif channel == "simulation:command":
                    await self._handle_command(data)
            except Exception as e:
                logger.error(f"Simulation error: {e}", exc_info=True)

    async def _handle_control(self, data: dict):
        action = data.get("action")
        if action == "pause":
            self.paused = True
            logger.info("Simulation paused")
        elif action == "resume":
            self.paused = False
            logger.info("Simulation resumed")
        elif action == "reset":
            self.start_time = datetime.now()
            self.fired_events.clear()
            self.current_timer = None
            self.current_phase = None
            logger.info("Simulation reset: timeline and phase cleared")

    async def _handle_command(self, data: dict):
        action = data.get("action")
        args = data.get("args", {})

        if action == "phase_change":
            await self._change_phase(args)
        elif action == "start_timer":
            await self._start_timer(args)

    async def _change_phase(self, args: dict):
        """Cambia la fase de la sesión legislativa."""
        phase = args.get("phase", "")
        duration_min = args.get("duration", 0)

        # Votación siempre arranca con timer de 5 min (reinicia en cada entrada a la fase)
        if phase == "votacion" and duration_min == 0:
            duration_min = 5

        self.current_phase = phase
        # Expose phase in Redis so asesores / handlers can read it without IPC
        try:
            await self.bus.raw.set("current_phase", phase)
        except Exception as e:
            logger.warning(f"Could not persist current_phase: {e}")

        if duration_min > 0:
            self.current_timer = {
                "name": phase,
                "end": datetime.now() + timedelta(minutes=duration_min),
                "total": duration_min * 60,
            }
        else:
            # Cualquier cambio de fase sin duración limpia el timer previo
            self.current_timer = None

        await self.bus.publish("layout:change", {
            "phase": phase,
            "duration": duration_min,
        })

        logger.info(f"Phase changed to: {phase} ({duration_min} min)")

    async def _start_timer(self, args: dict):
        """Inicia un temporizador."""
        name = args.get("name", "Ronda")
        minutes = args.get("minutes", 5)

        self.current_timer = {
            "name": name,
            "end": datetime.now() + timedelta(minutes=minutes),
            "total": minutes * 60,
        }

        logger.info(f"Timer started: {name} ({minutes} min)")

    async def _timer_loop(self):
        """Publica timer:update cada segundo."""
        while self._running:
            if self.current_timer and not self.paused:
                remaining = (self.current_timer["end"] - datetime.now()).total_seconds()
                remaining = max(0, remaining)

                await self.bus.publish("timer:update", {
                    "phase": self.current_timer["name"],
                    "remaining_seconds": remaining,
                    "total_seconds": self.current_timer["total"],
                })

                # Timer warnings
                if 299 < remaining <= 300:
                    await self.bus.publish("audio:generate_tts", {
                        "text": "", "voice": "broadcast",
                        "pregenerated": "timer_5min", "send_to": [],
                    })
                elif 59 < remaining <= 60:
                    await self.bus.publish("audio:generate_tts", {
                        "text": "", "voice": "broadcast",
                        "pregenerated": "timer_1min", "send_to": [],
                    })
                elif remaining <= 0:
                    expired_name = self.current_timer["name"]
                    self.current_timer = None
                    if expired_name == "votacion":
                        try:
                            await self._close_voting_session()
                        except Exception as e:
                            logger.error(f"Error closing voting: {e}", exc_info=True)
                    elif expired_name.startswith("votacion_articulo_"):
                        try:
                            num = int(expired_name.rsplit("_", 1)[1])
                            await self._close_articulo_session(num)
                        except Exception as e:
                            logger.error(f"Error closing articulo: {e}", exc_info=True)

            await asyncio.sleep(1)

    async def _close_articulo_session(self, numero: int):
        """Cierra la votación del artículo N, publica resultados, y abre el
        siguiente automáticamente. Al cerrar el último, publica un resumen
        global y sugiere al Presidente usar /compilar_acuerdo."""
        from db.database import get_session
        from sqlalchemy import text as sql_text
        from core.articulado import ARTICULOS, get_articulo

        async with get_session() as session:
            result = await session.execute(sql_text(
                "SELECT id, description, opened_at FROM voting_sessions "
                "WHERE type = 'articulo' AND target_id = :n AND is_open = true "
                "ORDER BY id DESC LIMIT 1"
            ), {"n": numero})
            vs = result.mappings().first()
            if not vs:
                logger.warning(f"No open articulo session for {numero}")
                return

            result = await session.execute(sql_text(
                "SELECT vote, COUNT(*) as n FROM votes "
                "WHERE vote_type = 'articulo' AND target_id = :n "
                "AND created_at >= :opened GROUP BY vote"
            ), {"n": numero, "opened": vs["opened_at"]})
            counts = {row["vote"]: row["n"] for row in result.mappings()}
            si = counts.get("si", 0)
            no = counts.get("no", 0)
            abst = counts.get("abstencion", 0)
            aprobado = si > no
            results_json = {
                "articulo": numero, "si": si, "no": no, "abstencion": abst,
                "aprobado": aprobado,
                "resultado": "APROBADO" if aprobado else "RECHAZADO",
            }
            await session.execute(sql_text(
                "UPDATE voting_sessions SET is_open = false, closed_at = NOW(), "
                "results = CAST(:r AS jsonb) WHERE id = :sid"
            ), {"r": json.dumps(results_json), "sid": vs["id"]})

            # Recipients
            result = await session.execute(sql_text(
                "SELECT telegram_id FROM users WHERE onboarding_complete = true"
            ))
            tids = [row[0] for row in result.fetchall()]

        art = get_articulo(numero) or {"titulo": "?"}
        emoji = "✅" if aprobado else "❌"
        msg = (
            f"{emoji} *Art. {numero} — {art['titulo']}*\n"
            f"Resultado: *{results_json['resultado']}*\n"
            f"Sí {si} / No {no} / Abs {abst}"
        )
        for tid in tids:
            await self.bus.stream_add("telegram:outgoing", {
                "chat_id": str(tid),
                "text": msg,
                "parse_mode": "Markdown",
            })
        await self.bus.publish("voting:ended", results_json)

        # Next article or finish
        if numero < len(ARTICULOS):
            from handlers.presidencia_handler import _open_articulo_vote
            await _open_articulo_vote(self, numero + 1, None)
        else:
            # Find the presidente and prompt them to compile
            async with get_session() as session:
                result = await session.execute(sql_text(
                    "SELECT telegram_id FROM users "
                    "WHERE rol = 'presidente_concejo' LIMIT 1"
                ))
                presi_tid = result.scalar()
            if presi_tid:
                await self.bus.stream_add("telegram:outgoing", {
                    "chat_id": str(presi_tid),
                    "text": (
                        "🎖️ *Votación por artículos finalizada.*\n\n"
                        "Usa `/compilar_acuerdo` para que Tavo redacte el "
                        "texto final consolidado y puedas difundirlo."
                    ),
                    "parse_mode": "Markdown",
                })
        logger.info(f"Articulo {numero} closed: {results_json}")

    async def _close_voting_session(self):
        """Cierra la sesión de votación activa, calcula resultados y difunde."""
        from db.database import get_session
        from sqlalchemy import text as sql_text

        async with get_session() as session:
            result = await session.execute(
                sql_text(
                    "SELECT id, description, opened_at FROM voting_sessions "
                    "WHERE is_open = true AND type = 'proyecto' "
                    "ORDER BY id DESC LIMIT 1"
                )
            )
            vs = result.mappings().first()
            if not vs:
                logger.warning("No open voting session to close")
                return

            session_id = vs["id"]

            # Tally votes cast in this session window
            result = await session.execute(
                sql_text(
                    "SELECT vote, COUNT(*) as n FROM votes "
                    "WHERE vote_type = 'proyecto' AND created_at >= :opened "
                    "GROUP BY vote"
                ),
                {"opened": vs["opened_at"]},
            )
            counts = {row["vote"]: row["n"] for row in result.mappings()}

            si = counts.get("si", 0)
            no = counts.get("no", 0)
            abst = counts.get("abstencion", 0)
            total = si + no + abst
            aprobado = si > no
            resultado = "APROBADO" if aprobado else "RECHAZADO"

            results_json = {
                "si": si, "no": no, "abstencion": abst, "total": total,
                "resultado": resultado, "aprobado": aprobado,
            }

            await session.execute(
                sql_text(
                    "UPDATE voting_sessions SET is_open = false, closed_at = NOW(), "
                    "results = CAST(:r AS jsonb) WHERE id = :sid"
                ),
                {"r": json.dumps(results_json), "sid": session_id},
            )

            # Build historial
            result = await session.execute(
                sql_text(
                    "SELECT id, description, closed_at, results FROM voting_sessions "
                    "WHERE results IS NOT NULL ORDER BY id"
                )
            )
            history = list(result.mappings())

            # Recipients: all registered users
            result = await session.execute(
                sql_text("SELECT telegram_id FROM users WHERE onboarding_complete = true")
            )
            tids = [row[0] for row in result.fetchall()]

        emoji = "✅" if aprobado else "❌"
        lines = [
            f"{emoji} *VOTACIÓN CERRADA — {resultado}*",
            "",
            "*Resultados finales:*",
            f"• ✅ A favor: *{si}*",
            f"• ❌ En contra: *{no}*",
            f"• 🤷 Abstenciones: *{abst}*",
            f"• Total votos: {total}",
        ]
        if len(history) > 1:
            lines += ["", "*📜 Trazabilidad de votaciones:*"]
            for i, h in enumerate(history, 1):
                r = h["results"]
                if isinstance(r, str):
                    r = json.loads(r)
                marker = "✅" if r.get("aprobado") else "❌"
                lines.append(
                    f"{i}. {marker} {r.get('resultado', '?')} — "
                    f"{r.get('si', 0)}sí / {r.get('no', 0)}no / {r.get('abstencion', 0)}abs"
                )
        msg = "\n".join(lines)

        for tid in tids:
            await self.bus.stream_add("telegram:outgoing", {
                "chat_id": str(tid),
                "text": msg,
                "parse_mode": "Markdown",
            })

        await self.bus.publish("voting:ended", {
            "session_id": session_id,
            **results_json,
        })

        logger.info(f"Voting session {session_id} closed: {resultado} ({si}-{no}-{abst})")

    async def _timeline_loop(self):
        """Revisa TIMELINE cada 10s y dispara eventos cuyo minuto ya pasó."""
        while self._running:
            if self.paused or not self.start_time:
                await asyncio.sleep(5)
                continue

            elapsed_min = (datetime.now() - self.start_time).total_seconds() / 60

            for idx, event in enumerate(TIMELINE):
                if idx in self.fired_events:
                    continue
                if event["minute"] > elapsed_min:
                    continue

                self.fired_events.add(idx)
                await self._dispatch_timeline_event(event)

            await asyncio.sleep(10)

    async def _dispatch_timeline_event(self, event: dict):
        """Envia un evento de timeline al canal correspondiente."""
        etype = event["type"]
        data = event["data"]

        if etype == "tweet":
            await self.bus.publish("pantalla:tweet", data)
            logger.info(f"Timeline tweet from {data.get('handle')}")

        elif etype == "stakeholder":
            actor_key = data.get("actor", "")
            actor_info = STAKEHOLDERS.get(actor_key, {})
            await self.bus.publish("pantalla:news", {
                "title": f"{actor_info.get('nombre', actor_key)} — {data.get('action', '')}",
                "text": data.get("message", ""),
                "priority": "alta" if data.get("action") in ("tutela", "protesta", "ultimatum") else "media",
                "source": actor_info.get("nombre", actor_key),
            })
            # Also publish to control for potential broadcast
            await self.bus.publish("control:command", {
                "action": "stakeholder_event",
                "actor": actor_key,
                "event_action": data.get("action"),
                "message": data.get("message", ""),
            })
            logger.info(f"Timeline stakeholder: {actor_key} -> {data.get('action')}")
