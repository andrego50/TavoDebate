"""TavoDebate Mini App — endpoints FastAPI para Telegram Web App."""

import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import text

import redis.asyncio as aioredis

from core.config import BANCADAS, ROLES, settings
from db.database import get_session

logger = logging.getLogger(__name__)

router = APIRouter()

BANCADA_COLORS = {
    1: "#1565C0",
    2: "#B71C1C",
    3: "#2E7D32",
    4: "#6A1B9A",
    5: "#E65100",
    6: "#37474F",
}


def _validate_init_data(init_data: str, bot_token: str) -> dict | None:
    """Valida HMAC de Telegram WebApp initData. Retorna user dict o None."""
    try:
        params = dict(p.split("=", 1) for p in init_data.split("&") if "=" in p)
        hash_val = params.pop("hash", "")
        data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
        secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        computed = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed, hash_val):
            return None
        return json.loads(params.get("user", "{}"))
    except Exception:
        return None


@router.get("/miniapp")
async def serve_miniapp():
    return FileResponse("static/miniapp/index.html")


@router.get("/miniapp/data")
async def miniapp_data(request: Request):
    init_data = request.headers.get("X-Telegram-Init-Data", "")

    if init_data:
        tg_user = _validate_init_data(init_data, settings.telegram_bot_token)
        if tg_user is None:
            raise HTTPException(status_code=401, detail="Invalid initData")
    elif settings.is_dev:
        # Dev: devuelve datos del primer admin sin validar
        tg_user = {"id": settings.admin_ids[0] if settings.admin_ids else 0}
    else:
        raise HTTPException(status_code=401, detail="Missing initData")

    telegram_id = int(tg_user.get("id", 0))
    is_admin = telegram_id in settings.admin_ids

    async with get_session() as db:
        result = await db.execute(
            text("SELECT * FROM users WHERE telegram_id = :tid"),
            {"tid": telegram_id},
        )
        user = result.mappings().first()

        if not user:
            return {"registered": False, "is_admin": is_admin}

        # Fase desde Redis
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        fase_actual = await r.get("debate:fase") or "registro"
        await r.aclose()

        # Nombre del evento
        evento_nombre = "Concejo Futuro"
        if user.get("evento_id"):
            ev = await db.execute(
                text("SELECT nombre FROM eventos WHERE id = :eid"),
                {"eid": user["evento_id"]},
            )
            ev_row = ev.first()
            if ev_row:
                evento_nombre = ev_row[0]

        if is_admin:
            bdata = []
            for bid, binfo in BANCADAS.items():
                cnt = await db.execute(
                    text(
                        "SELECT COUNT(*) FROM users "
                        "WHERE bancada_id = :bid AND onboarding_complete = true"
                    ),
                    {"bid": bid},
                )
                bdata.append(
                    {
                        "id": bid,
                        "nombre": binfo["nombre"],
                        "posicion": binfo["posicion"],
                        "color": BANCADA_COLORS.get(bid, "#888"),
                        "count": cnt.scalar() or 0,
                    }
                )

            total_part = await db.execute(
                text("SELECT COUNT(*) FROM users WHERE onboarding_complete = true")
            )
            total_props = await db.execute(text("SELECT COUNT(*) FROM proposals"))
            total_votos = await db.execute(text("SELECT COUNT(*) FROM votes"))

            return {
                "registered": True,
                "is_admin": True,
                "nombre": user.get("nombre_completo", "Facilitador"),
                "evento_nombre": evento_nombre,
                "fase_actual": fase_actual,
                "stats": {
                    "participantes": total_part.scalar() or 0,
                    "bancadas": sum(1 for b in bdata if b["count"] > 0),
                    "propuestas": total_props.scalar() or 0,
                    "votos": total_votos.scalar() or 0,
                },
                "bancadas": bdata,
            }

        # Usuario regular
        rol_info = ROLES.get(user.get("rol", ""), {})
        bancada_id = user.get("bancada_id") or 0
        bancada_info = BANCADAS.get(bancada_id, {})

        n_consultas_row = await db.execute(
            text("SELECT COUNT(*) FROM messages WHERE telegram_id = :tid"),
            {"tid": telegram_id},
        )
        n_consultas = n_consultas_row.scalar() or 0

        n_props_row = await db.execute(
            text("SELECT COUNT(*) FROM proposals WHERE user_id = :uid"),
            {"uid": user["id"]},
        )
        n_propuestas = n_props_row.scalar() or 0

        bancada_count_row = await db.execute(
            text(
                "SELECT COUNT(*) FROM users "
                "WHERE bancada_id = :bid AND onboarding_complete = true"
            ),
            {"bid": bancada_id},
        )

        return {
            "registered": True,
            "is_admin": False,
            "nombre": user.get("nombre_completo", ""),
            "rol": user.get("rol", ""),
            "rol_nombre": rol_info.get("nombre", "Participante"),
            "grupo": rol_info.get("grupo", ""),
            "puede_votar": rol_info.get("puede_votar", False),
            "bancada_id": bancada_id,
            "bancada_nombre": bancada_info.get("nombre", ""),
            "bancada_posicion": bancada_info.get("posicion", ""),
            "bancada_color": BANCADA_COLORS.get(bancada_id, "#888"),
            "bancada_count": bancada_count_row.scalar() or 0,
            "municipio": user.get("municipio", ""),
            "provincia": user.get("provincia", ""),
            "evento_nombre": evento_nombre,
            "fase_actual": fase_actual,
            "stats": {
                "consultas": n_consultas,
                "propuestas": n_propuestas,
            },
        }
