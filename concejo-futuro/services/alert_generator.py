"""TavoDebate - Generador de alertas visuales con Playwright."""

import logging
from pathlib import Path
import tempfile

logger = logging.getLogger("services.alert")

ALERT_HTML_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
body {{ margin:0; background:{bg}; display:flex; align-items:center; justify-content:center;
  height:100vh; font-family:'Inter',sans-serif; }}
.alert {{ background:rgba(0,0,0,0.85); border:3px solid {border}; border-radius:16px;
  padding:40px 60px; max-width:700px; text-align:center; }}
.alert-icon {{ font-size:64px; margin-bottom:16px; }}
.alert-title {{ font-size:28px; font-weight:800; color:{border}; margin-bottom:12px; }}
.alert-text {{ font-size:18px; color:#e0e0e0; line-height:1.6; }}
.alert-source {{ margin-top:16px; font-size:14px; color:#7a8ab5; }}
</style></head>
<body><div class="alert">
<div class="alert-icon">{icon}</div>
<div class="alert-title">{title}</div>
<div class="alert-text">{text}</div>
<div class="alert-source">{source}</div>
</div></body></html>"""

ALERT_STYLES = {
    "bomb": {"bg": "#1a0a0a", "border": "#e53935", "icon": "💣"},
    "stakeholder": {"bg": "#0a1a1a", "border": "#4fc3f7", "icon": "📢"},
    "fakenews": {"bg": "#1a1a0a", "border": "#ffd54f", "icon": "📰"},
    "pressure": {"bg": "#1a0a1a", "border": "#ce93d8", "icon": "⚡"},
    "vote": {"bg": "#0a1a0a", "border": "#66bb6a", "icon": "🗳️"},
}


async def generate_alert_image(
    alert_type: str,
    title: str,
    text: str,
    source: str = "TavoDebate",
) -> Path | None:
    """Genera imagen PNG de alerta usando Playwright."""
    style = ALERT_STYLES.get(alert_type, ALERT_STYLES["stakeholder"])

    html = ALERT_HTML_TEMPLATE.format(
        bg=style["bg"],
        border=style["border"],
        icon=style["icon"],
        title=title,
        text=text,
        source=source,
    )

    out_path = Path(tempfile.gettempdir()) / f"alert_{alert_type}_{hash(title) & 0xFFFF:04x}.png"

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 800, "height": 500})
            await page.set_content(html)
            await page.screenshot(path=str(out_path))
            await browser.close()

        logger.info(f"Alert image generated: {out_path.name}")
        return out_path
    except Exception as e:
        logger.error(f"Failed to generate alert image: {e}")
        return None
