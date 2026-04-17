"""TavoDebate - Tutorial contextual por rol."""

from core.config import ROLES
from db.database import get_session


TUTORIAL_HEADER = (
    "🎓 *Tutorial rápido — Concejo del Futuro*\n\n"
    "Estás en una simulación legislativa del proyecto SIADR (Sistema "
    "Inteligente de Asignación de Recursos para el Desarrollo Rural) de "
    "Cundinamarca. Tu agente de IA se adapta a tu rol.\n"
)


ASESORES_BLOCK = (
    "*🤝 Tavo + equipo de asesores*\n"
    "Por defecto interactúas con 🧠 *Tavo*, tu jefe de gabinete. Él enruta "
    "tu pregunta a los asesores relevantes en paralelo y te entrega una "
    "respuesta consolidada con la voz de cada especialista más su propia "
    "recomendación ejecutiva.\n\n"
    "Si quieres hablar con un especialista específico, usa /asesores y "
    "elige entre 10 dominios:\n"
    "• ⚖️ *Jurídico* — marco normativo, vicios, precedentes\n"
    "• 📢 *Comunicaciones* — tuits, soundbites, titulares\n"
    "• 📊 *Económico* — cifras macro, ROI, SGP, regalías\n"
    "• 🏛️ *Político* — bancadas, correlación de fuerzas, jugadas\n"
    "• 💻 *Tecnológico* — IoT, arquitectura, riesgos técnicos\n"
    "• 🗺️ *Catastral* — avalúos, métodos, CONPES catastral\n"
    "• 🌾 *Agrario/Rural* — economía campesina, UAF, capacidad de pago\n"
    "• 💰 *Fiscal/Tributario* — predial, tarifas, exenciones, fondo alivio\n"
    "• 🤝 *Participación ciudadana* — audiencias, veedurías, diálogo social\n"
    "• 📐 *Gerencia pública* — cadena de valor, KPIs, Sinergia, CONPES\n"
    "Cada asesor puede *buscar en internet* cuando le falten datos frescos."
)


LIVE_CONTEXT_BLOCK = (
    "*📡 Contexto en tiempo real*\n"
    "Tu asesor siempre está al tanto de: fase actual, últimos tuits en "
    "pantalla, bombas informativas, fake news, alertas institucionales y "
    "votaciones. No hace falta recordárselo."
)


ROLE_GUIDES = {
    "concejo": (
        "*🏛️ Tu rol: Concejal*\n"
        "• Deliberas y *votas* el proyecto SIADR.\n"
        "• Usa `/preparar_ponencia` para que la IA arme tu intervención.\n"
        "• Usa `/tuitear` (sin texto) para ver los últimos tuits y "
        "responder/citar con botones.\n"
        "• Usa `/proponer <texto>` para presentar enmiendas.\n"
        "• En fase votación: `/votar_proyecto a_favor | en_contra | abstencion`."
    ),
    "gobierno": (
        "*👔 Tu rol: Equipo de Gobierno*\n"
        "• *Defiendes* el proyecto SIADR. No votas, pero debates.\n"
        "• Si eres *Alcalde*, `/preparar_ponencia` dispara una entrevista "
        "guiada de 8 preguntas para armar tu ponencia de apertura.\n"
        "• Tu asesor puede redactar respuestas a críticas, tuits oficiales "
        "y comunicados.\n"
        "• Usa `/tuitear` para intervenir en la pantalla."
    ),
    "sociedad_civil": (
        "*🧑‍🌾 Tu rol: Sociedad Civil*\n"
        "• *Presionas* al Concejo desde tu comunidad. No votas.\n"
        "• Tu asesor te ayuda a formular denuncias, exigencias y preguntas "
        "incisivas desde tu perspectiva comunitaria.\n"
        "• Usa `/tuitear` para amplificar tu voz en la pantalla."
    ),
    "empresa": (
        "*🏢 Tu rol: Sector Privado*\n"
        "• Defiendes intereses empresariales. No votas.\n"
        "• Tu asesor te ayuda a presentar beneficios económicos y responder "
        "a acusaciones de conflicto de interés.\n"
        "• Usa `/tuitear` para comunicar tu posición."
    ),
    "control": (
        "*⚖️ Tu rol: Órgano de Control*\n"
        "• Vigilas transparencia y legalidad. No votas el proyecto.\n"
        "• Tu asesor te ayuda con alertas, advertencias legales y "
        "exigencias de fiscalización rigurosas.\n"
        "• Usa `/tuitear` para pronunciamientos públicos."
    ),
}


ADMIN_GUIDE = (
    "*🎛️ Tu rol: Dinamizador (admin)*\n"
    "• `/fase` cambia la etapa del ejercicio (registro, ponencia, debate, "
    "votación, etc.). La fase votación arranca un timer de 5 min.\n"
    "• `/broadcast` y `/presion` sin texto generan un *borrador con IA* "
    "basado en lo que está pasando; tú apruebas, regeneras o cancelas.\n"
    "• `/bomba`, `/fakenews`, `/tweet` te muestran un catálogo con "
    "preview antes de enviar.\n"
    "• `/ronda`, `/pantalla`, `/gabinete_remover`, `/gabinete_amenaza` "
    "tienen botones para elegir sin escribir nada.\n"
    "• `/historial_votaciones` muestra trazabilidad de votaciones."
)


async def handle_tutorial(agent, user_id: int, chat_id: int):
    """Devuelve el tutorial apropiado al rol del usuario."""
    from core.config import settings

    # Admin/dinamizador
    if user_id in settings.admin_ids:
        msg = TUTORIAL_HEADER + "\n\n" + ADMIN_GUIDE + "\n\n" + LIVE_CONTEXT_BLOCK
        await agent._send_response(chat_id, msg)
        return

    async with get_session() as session:
        from sqlalchemy import text as sql_text
        result = await session.execute(
            sql_text("SELECT rol, onboarding_complete FROM users WHERE telegram_id = :tid"),
            {"tid": user_id},
        )
        row = result.mappings().first()

    if not row or not row["onboarding_complete"]:
        await agent._send_response(
            chat_id,
            TUTORIAL_HEADER
            + "\n\nAún no has completado tu registro. Envía /start para "
            "elegir tu rol y recibir el tutorial específico."
        )
        return

    rol_key = row["rol"] or "concejal"
    grupo = ROLES.get(rol_key, {}).get("grupo", "concejo")
    role_block = ROLE_GUIDES.get(grupo, ROLE_GUIDES["concejo"])

    msg = "\n\n".join([TUTORIAL_HEADER, role_block, ASESORES_BLOCK, LIVE_CONTEXT_BLOCK])
    await agent._send_response(chat_id, msg)
