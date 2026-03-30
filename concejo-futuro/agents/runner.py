"""TavoDebate - Punto de entrada multiagente."""

import asyncio
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

AGENT_TYPE = os.getenv("AGENT_TYPE", "orchestrator")

logger = logging.getLogger(f"runner.{AGENT_TYPE}")


async def main():
    logger.info(f"Starting TavoDebate agent: {AGENT_TYPE}")

    if AGENT_TYPE == "orchestrator":
        from agents.orchestrator import Orchestrator
        agent = Orchestrator()
    elif AGENT_TYPE == "chat":
        from agents.chat_agent import ChatAgent
        agent = ChatAgent()
    elif AGENT_TYPE == "intel":
        from agents.intel_agent import IntelAgent
        agent = IntelAgent()
    elif AGENT_TYPE == "control":
        from agents.control_agent import ControlAgent
        agent = ControlAgent()
    elif AGENT_TYPE == "pantalla":
        from agents.pantalla_agent import PantallaAgent
        agent = PantallaAgent()
    elif AGENT_TYPE == "audio":
        from agents.audio_agent import AudioAgent
        agent = AudioAgent()
    elif AGENT_TYPE == "simulation":
        from agents.simulation_agent import SimulationAgent
        agent = SimulationAgent()
    else:
        logger.error(f"Unknown agent type: {AGENT_TYPE}")
        sys.exit(1)

    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
