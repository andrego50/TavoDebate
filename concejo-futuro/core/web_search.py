"""TavoDebate - Búsqueda web via DuckDuckGo (gratis)."""

import asyncio
import logging

logger = logging.getLogger("core.web_search")


async def search_web(query: str, max_results: int = 3) -> str:
    """Busca en DuckDuckGo y retorna resultados formateados."""
    def _search():
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, region="wt-wt", max_results=max_results))
            if not results:
                return "No se encontraron resultados."
            lines = []
            for r in results:
                title = r.get("title", "")
                body = r.get("body", "")[:200]
                href = r.get("href", "")
                lines.append(f"- {title}: {body} ({href})")
            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")
            return f"Error en búsqueda: {e}"

    return await asyncio.get_event_loop().run_in_executor(None, _search)
