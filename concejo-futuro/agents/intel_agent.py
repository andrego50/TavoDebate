"""TavoDebate - Agente Intel (clasificación, briefings, análisis proactivo)."""

import asyncio
import json
import logging
from datetime import datetime

from agents.base_agent import BaseAgent
from core.config import settings
from core.llm_client import LLMClient
from db.database import get_session

logger = logging.getLogger("agent.intel")

CLASSIFICATION_PROMPT = """Eres un analista político experto en Colombia. Clasifica esta interacción de un concejal
en el debate sobre el proyecto SIADR (IA para alumbrado rural y agricultura de precisión en Cundinamarca).

Responde SOLO con JSON válido:
{
  "sentiment": "a_favor" | "en_contra" | "indeciso" | "neutral",
  "topics": ["lista", "de", "temas"],
  "position_strength": 1-5,
  "key_argument": "resumen de 1 línea del argumento principal",
  "notable": true/false,
  "notable_reason": "por qué es notable (si aplica)"
}

Temas posibles: costos, privacidad, empleo, corrupcion, beneficios, implementacion,
legal, ambiental, educacion, seguridad, participacion, transparencia, tecnologia."""


class IntelAgent(BaseAgent):
    name = "intel"

    def __init__(self):
        super().__init__()
        self.llm: LLMClient | None = None

    async def setup(self):
        await super().setup()
        self.llm = LLMClient(redis_client=self.bus.raw)

    async def start(self):
        # Start briefing loop
        asyncio.create_task(self._briefing_loop())

        # Listen to interaction:new stream
        logger.info("Intel agent listening for interactions")
        while self._running:
            try:
                messages = await self.bus.stream_read_group(
                    "interaction:new",
                    "intel_agents",
                    count=10,
                    block=5000,
                )
                for entry_id, data in messages:
                    try:
                        await self._classify(data)
                    except Exception as e:
                        logger.error(f"Classification error: {e}", exc_info=True)
                    finally:
                        await self.bus.stream_ack("interaction:new", "intel_agents", entry_id)
            except Exception as e:
                logger.error(f"Intel stream error: {e}")
                await asyncio.sleep(2)

    async def _classify(self, interaction: dict):
        """Clasifica una interacción con LLM."""
        prompt_input = (
            f"Bancada: {interaction.get('bancada_id', '?')}\n"
            f"Voz activa: {interaction.get('voice', '?')}\n"
            f"Pregunta: {interaction['question']}\n"
            f"Respuesta: {interaction['response']}"
        )

        classification_text = await self.llm.generate(
            CLASSIFICATION_PROMPT,
            prompt_input,
            temperature=0.3,
            max_tokens=300,
            use_cache=False,
        )

        try:
            # Strip markdown code fences that LLMs sometimes add
            import re
            clean = re.sub(r'^```(?:json)?\s*', '', classification_text.strip())
            clean = re.sub(r'\s*```$', '', clean)
            classification = json.loads(clean)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse classification: {classification_text[:200]}")
            return

        # Save to DB
        async with get_session() as session:
            from sqlalchemy import text as sql_text
            await session.execute(
                sql_text(
                    "UPDATE interactions SET "
                    "sentiment = :sent, topics = :topics, "
                    "position_strength = :pos, key_argument = :arg, "
                    "classified_at = NOW() "
                    "WHERE id = :id"
                ),
                {
                    "id": interaction["id"],
                    "sent": classification.get("sentiment", "neutral"),
                    "topics": json.dumps(classification.get("topics", [])),
                    "pos": classification.get("position_strength", 3),
                    "arg": classification.get("key_argument", ""),
                },
            )

        # Check position change
        await self._check_position_change(interaction, classification)

        # If notable, alert
        if classification.get("notable"):
            logger.info(
                f"Notable interaction from user {interaction.get('user_id')}: "
                f"{classification.get('notable_reason')}"
            )

    async def _check_position_change(self, interaction: dict, classification: dict):
        """Detecta cambios de posición."""
        async with get_session() as session:
            from sqlalchemy import text as sql_text
            result = await session.execute(
                sql_text(
                    "SELECT sentiment FROM interactions "
                    "WHERE user_id = :uid AND id != :id "
                    "ORDER BY created_at DESC LIMIT 1"
                ),
                {"uid": interaction.get("user_id"), "id": interaction["id"]},
            )
            prev = result.scalar()

        new_sentiment = classification.get("sentiment")
        if prev and prev != new_sentiment and new_sentiment in ("a_favor", "en_contra"):
            await self.bus.publish("position:changed", {
                "user_id": interaction.get("user_id"),
                "bancada_id": interaction.get("bancada_id"),
                "old_position": prev,
                "new_position": new_sentiment,
                "timestamp": datetime.now().isoformat(),
            })

    async def _briefing_loop(self):
        """Genera briefings cada N segundos."""
        while self._running:
            await asyncio.sleep(settings.briefing_interval_seconds)
            try:
                await self._generate_briefing()
            except Exception as e:
                logger.error(f"Briefing generation error: {e}", exc_info=True)

    async def _generate_briefing(self):
        """Genera un briefing para Andrés."""
        async with get_session() as session:
            from sqlalchemy import text as sql_text

            # Get recent stats
            stats = await session.execute(
                sql_text(
                    "SELECT "
                    "  COUNT(*) as total, "
                    "  COUNT(*) FILTER (WHERE sentiment = 'a_favor') as favor, "
                    "  COUNT(*) FILTER (WHERE sentiment = 'en_contra') as contra, "
                    "  COUNT(*) FILTER (WHERE sentiment = 'indeciso') as indeciso "
                    "FROM interactions "
                    "WHERE created_at > NOW() - INTERVAL '5 minutes'"
                )
            )
            row = stats.mappings().first()

            # Get recent topics
            topics = await session.execute(
                sql_text(
                    "SELECT topics FROM interactions "
                    "WHERE topics IS NOT NULL AND created_at > NOW() - INTERVAL '5 minutes'"
                )
            )
            all_topics = []
            for r in topics.mappings():
                try:
                    all_topics.extend(json.loads(r["topics"]))
                except (json.JSONDecodeError, TypeError):
                    pass

        if not row or row["total"] == 0:
            return

        # Count topics
        from collections import Counter
        topic_counts = Counter(all_topics).most_common(5)

        briefing_input = (
            f"Últimos 5 minutos:\n"
            f"- Interacciones: {row['total']}\n"
            f"- A favor: {row['favor']}, En contra: {row['contra']}, Indecisos: {row['indeciso']}\n"
            f"- Temas principales: {', '.join(f'{t}({c})' for t, c in topic_counts)}\n"
        )

        briefing_prompt = (
            "Eres el asistente de inteligencia de Andrés, facilitador del taller legislativo "
            "TavoDebate sobre el proyecto SIADR en Cundinamarca. Genera un briefing ejecutivo "
            "de 3-5 líneas con: estado del debate, posiciones dominantes, recomendación de "
            "acción para Andrés. Sé directo y conciso."
        )

        briefing_text = await self.llm.generate(
            briefing_prompt,
            briefing_input,
            temperature=0.5,
            max_tokens=500,
        )

        # Publish briefing
        await self.bus.publish("briefing:new", {
            "text": f"📊 *BRIEFING*\n\n{briefing_text}",
            "stats": {
                "total": row["total"],
                "favor": row["favor"],
                "contra": row["contra"],
                "indeciso": row["indeciso"],
            },
            "timestamp": datetime.now().isoformat(),
        })

        # Generate proactive proposals
        await self._generate_proposals(briefing_input)

    async def _generate_proposals(self, context: str):
        """Genera propuestas proactivas para Andrés."""
        proposal_prompt = (
            "Basándote en el estado actual del debate, sugiere 1-2 acciones que Andrés "
            "podría tomar para dinamizar la discusión. Formato JSON:\n"
            '[{"type": "broadcast|bomb|fakenews|pressure", "target": "all|bancada_N", '
            '"message": "texto sugerido", "reason": "por qué"}]'
        )

        proposal_text = await self.llm.generate(
            proposal_prompt, context, temperature=0.7, max_tokens=500
        )

        try:
            clean_prop = re.sub(r'^```(?:json)?\s*', '', proposal_text.strip())
            clean_prop = re.sub(r'\s*```$', '', clean_prop)
            proposals = json.loads(clean_prop)
            await self.bus.publish("proposal:proactive", {
                "proposals": proposals,
                "timestamp": datetime.now().isoformat(),
            })
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse proposals: {proposal_text[:200]}")

    async def shutdown(self):
        if self.llm:
            await self.llm.close()
        await super().shutdown()
