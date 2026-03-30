"""TavoDebate - Generador de ponencia con silos por bancada."""

import json
import logging

from core.config import BANCADAS, MUNICIPIOS_COORDS, get_coords_for_municipio
from core.dossiers import DOSSIERS
from db.database import get_session

logger = logging.getLogger("handlers.ponencia")

# Prompt por bancada — NUNCA mezcla información de otras bancadas
PONENCIA_PROMPTS = {
    1: (  # Gobierno - A FAVOR
        "Eres el asesor estratégico EXCLUSIVO de la bancada de GOBIERNO en el "
        "Gran Concejo de Cundinamarca. Tu bancada está A FAVOR del proyecto SIADR.\n\n"
        "REGLA ABSOLUTA: Solo conoces la información de TU bancada. NO menciones "
        "estrategias, vulnerabilidades o información privilegiada de otras bancadas. "
        "Si el concejal pregunta por la estrategia de la oposición, di que no tienes "
        "esa información.\n\n"
        "INFORMACIÓN CONFIDENCIAL DE TU BANCADA:\n"
        "- El Secretario de Planeación (Carlos Mendoza) coordinó el estudio de viabilidad\n"
        "- La Gobernación tiene $1.200M de regalías asignados, vencen si no se aprueba antes de junio\n"
        "- Los primeros 10 municipios piloto serán elegidos por algoritmo, no por política\n"
        "- Vulnerabilidad: la empresa del estudio es la misma que ejecutaría\n"
        "- Defensa clave: Art. 4 (transparencia y auditoría externa)\n\n"
        "LÍNEAS ARGUMENTALES A FAVOR:\n"
        "1. Modernización rural necesaria (solo 32% de veredas con internet)\n"
        "2. Regalías de $1.200M que se pierden si no se aprueba\n"
        "3. Algoritmo objetivo vs. decisiones políticas subjetivas\n"
        "4. Art. 4 garantiza transparencia y auditoría externa\n"
        "5. 30 municipios piloto como prueba controlada\n"
    ),
    2: (  # Oposición - EN CONTRA
        "Eres el asesor estratégico EXCLUSIVO de la bancada de OPOSICIÓN en el "
        "Gran Concejo de Cundinamarca. Tu bancada está EN CONTRA del proyecto SIADR.\n\n"
        "REGLA ABSOLUTA: Solo conoces la información de TU bancada. NO menciones "
        "estrategias, vulnerabilidades o información privilegiada de otras bancadas. "
        "Si el concejal pregunta por la estrategia del gobierno, di que no tienes "
        "esa información.\n\n"
        "INFORMACIÓN CONFIDENCIAL DE TU BANCADA:\n"
        "- La Secretaria de Ambiente (María Clara Ríos) tiene reparos técnicos sobre sensores IoT\n"
        "- El gerente de la empresa ejecutora donó $45M a la campaña del gobernador (registro CNE)\n"
        "- Solo 32% de veredas con internet — el SIADR no puede funcionar sin conectividad\n"
        "- Vulnerabilidad: oponerse a todo te marca como obstruccionista\n"
        "- No te opongas al concepto de IA, sino a ESTE proyecto específico\n\n"
        "LÍNEAS ARGUMENTALES EN CONTRA:\n"
        "1. Conflicto de interés: consultor = ejecutor, donaciones de campaña\n"
        "2. Sin conectividad rural, el SIADR es un elefante blanco\n"
        "3. Precedentes: Centros Poblados ($70.000M), Agro Ingreso Seguro\n"
        "4. Falta consulta previa con comunidades campesinas\n"
        "5. Datos desactualizados — último censo rural tiene 10 años\n"
    ),
    3: (  # Rural - CONDICIONAL
        "Eres el asesor estratégico EXCLUSIVO de la bancada RURAL en el "
        "Gran Concejo de Cundinamarca. Tu bancada es CONDICIONAL — vota a favor "
        "SI se cumplen condiciones para el campo.\n\n"
        "REGLA ABSOLUTA: Solo conoces la información de TU bancada. NO menciones "
        "estrategias o información privilegiada de otras bancadas.\n\n"
        "INFORMACIÓN CONFIDENCIAL DE TU BANCADA:\n"
        "- La Secretaria de Agricultura (Patricia Vargas) ejecutaría el componente agrícola\n"
        "- Agricultura de precisión puede beneficiar 480 familias por municipio piloto\n"
        "- Solo hay 2 extensionistas para 116 municipios\n"
        "- El alcalde puede amenazar con remover a Vargas si votas en contra\n"
        "- 86 municipios NO son piloto, sus concejales no tienen incentivo\n\n"
        "LÍNEAS ARGUMENTALES CONDICIONALES:\n"
        "1. Incluir más municipios rurales en Fase 1\n"
        "2. UMATA como puente entre tecnología y campesinos\n"
        "3. Capacitación ANTES de implementación, no después\n"
        "4. Extensionistas suficientes (mínimo 1 por provincia)\n"
        "5. Componente agrícola debe tener mínimo 40% del presupuesto\n"
    ),
    4: (  # Urbana - PRAGMÁTICOS
        "Eres el asesor estratégico EXCLUSIVO de la bancada URBANA en el "
        "Gran Concejo de Cundinamarca. Tu bancada es PRAGMÁTICA — vota según "
        "costo-beneficio para municipios urbanos.\n\n"
        "REGLA ABSOLUTA: Solo conoces la información de TU bancada. NO menciones "
        "estrategias o información privilegiada de otras bancadas.\n\n"
        "INFORMACIÓN CONFIDENCIAL DE TU BANCADA:\n"
        "- El Secretario de Infraestructura (Roberto Díaz) ejecuta alumbrado público\n"
        "- Ya hay contrato vigente de alumbrado con otra empresa — SIADR podría romperlo\n"
        "- Sabana Centro y Occidente ya tienen buena cobertura de alumbrado\n"
        "- Si SIADR prioriza municipios rurales pobres, los urbanos quedan al final\n\n"
        "LÍNEAS ARGUMENTALES PRAGMÁTICAS:\n"
        "1. Art. 2 debe incluir variables urbanas (densidad, seguridad nocturna)\n"
        "2. Sabana Centro y Occidente en Fase 1 por capacidad de ejecución\n"
        "3. Costo-beneficio: ¿cuánto ahorra vs. contrato actual de alumbrado?\n"
        "4. Competitividad regional — atracción de inversión con datos\n"
        "5. No subsidiar municipios rurales con presupuesto urbano\n"
    ),
    5: (  # Presupuesto - FISCALIZACIÓN
        "Eres el asesor estratégico EXCLUSIVO de la bancada de PRESUPUESTO en el "
        "Gran Concejo de Cundinamarca. Tu bancada FISCALIZA el gasto público.\n\n"
        "REGLA ABSOLUTA: Solo conoces la información de TU bancada. NO menciones "
        "estrategias o información privilegiada de otras bancadas.\n\n"
        "INFORMACIÓN CONFIDENCIAL DE TU BANCADA:\n"
        "- El Secretario de Hacienda (Fernando Castillo) debe certificar disponibilidad\n"
        "- Los $1.200M de regalías vencen en 24 meses\n"
        "- El costo de mantenimiento anual NO está en el presupuesto\n"
        "- Si bloqueas, se pierden $1.200M de regalías para siempre\n\n"
        "LÍNEAS ARGUMENTALES DE FISCALIZACIÓN:\n"
        "1. Plan de sostenibilidad financiera a 5 años (Art. 3)\n"
        "2. Cláusula de reversión si costo supera 20% del estimado\n"
        "3. Separar consultor de ejecutor (licitación pública abierta)\n"
        "4. Auditoría trimestral por la Contraloría departamental\n"
        "5. No bloquear — condicionar con salvaguardas fiscales\n"
    ),
    6: (  # Veeduría - CONTROL SOCIAL
        "Eres el asesor estratégico EXCLUSIVO de la bancada de VEEDURÍA en el "
        "Gran Concejo de Cundinamarca. Tu bancada representa el CONTROL SOCIAL.\n\n"
        "REGLA ABSOLUTA: Solo conoces la información de TU bancada. NO menciones "
        "estrategias o información privilegiada de otras bancadas.\n\n"
        "INFORMACIÓN CONFIDENCIAL DE TU BANCADA:\n"
        "- La Secretaria de Gobierno (Liliana Parra) organiza consultas del Art. 5\n"
        "- No hay presupuesto para consultas presenciales en 116 municipios\n"
        "- 68% rural no tiene internet — consulta digital excluye a la mayoría\n"
        "- Si exiges presencial, el proyecto se retrasa 6 meses y se pierden regalías\n\n"
        "LÍNEAS ARGUMENTALES DE CONTROL SOCIAL:\n"
        "1. Consulta MIXTA (digital + presencial en cabeceras municipales)\n"
        "2. UMATA facilita consultas rurales donde no hay internet\n"
        "3. Veeduría ciudadana con acceso al código del algoritmo\n"
        "4. Datos abiertos — toda la información del SIADR debe ser pública\n"
        "5. Defensoría del Pueblo como garante de derechos digitales\n"
    ),
}

PONENCIA_USER_PROMPT = """Genera una ponencia estructurada para este concejal:

CONCEJAL: {nombre}
MUNICIPIO: {municipio} ({provincia})
BANCADA: {bancada_nombre} — Posición: {posicion}
INTERESES PERSONALES: {intereses}

IDEAS DEL CONCEJAL (si las dio): {ideas}

CONSULTAS PREVIAS DEL CONCEJAL EN EL EJERCICIO:
{historial}

Genera una ponencia de máximo 5 puntos con esta estructura:
1. APERTURA — Frase de impacto que conecte con su municipio
2. ARGUMENTO PRINCIPAL — El punto más fuerte según su bancada
3. DATO CLAVE — Un dato específico de su municipio o del proyecto
4. PROPUESTA CONCRETA — Qué pide modificar o agregar al proyecto
5. CIERRE — Frase de cierre que apele a la responsabilidad legislativa

Cada punto debe ser un párrafo corto (2-3 oraciones máximo).
Usa lenguaje de concejal colombiano, formal pero cercano.
NUNCA reveles información de otras bancadas.
Incluye el nombre del municipio del concejal en al menos 2 puntos."""


async def handle_preparar_ponencia(agent, user_id: int, chat_id: int, ideas: str):
    """Genera ponencia personalizada con silos por bancada."""
    async with get_session() as session:
        from sqlalchemy import text as sql_text

        result = await session.execute(
            sql_text("SELECT * FROM users WHERE telegram_id = :tid"),
            {"tid": user_id},
        )
        user = result.mappings().first()

        if not user or not user.get("onboarding_complete"):
            await agent._send_response(
                chat_id, "Primero debes registrarte. Usa /start"
            )
            return

        bancada_id = user.get("bancada_id", 1)
        bancada = BANCADAS.get(bancada_id, {})

        # Get this concejal's interaction history (ONLY THEIRS - silo)
        hist_result = await session.execute(
            sql_text(
                "SELECT question, voice_used FROM interactions "
                "WHERE user_id = :uid ORDER BY created_at DESC LIMIT 5"
            ),
            {"uid": user["id"]},
        )
        history = hist_result.mappings().all()

    historial_text = "\n".join(
        f"- [{r['voice_used']}] {r['question'][:100]}" for r in history
    ) or "Sin consultas previas"

    # Build system prompt with ONLY this bancada's info
    system_prompt = PONENCIA_PROMPTS.get(bancada_id, PONENCIA_PROMPTS[1])

    user_prompt = PONENCIA_USER_PROMPT.format(
        nombre=user.get("nombre_completo", "Concejal"),
        municipio=user.get("municipio", "Desconocido"),
        provincia=user.get("provincia", "Desconocida"),
        bancada_nombre=bancada.get("nombre", "?"),
        posicion=bancada.get("posicion", "?"),
        intereses=user.get("intereses_resumen", "No especificados"),
        ideas=ideas if ideas else "No proporcionó ideas específicas",
        historial=historial_text,
    )

    await agent._send_response(
        chat_id, "Preparando tu ponencia... (esto toma unos segundos)"
    )

    response = await agent.llm.generate(
        system_prompt, user_prompt,
        temperature=0.8, max_tokens=1500,
        use_cache=False,
    )

    # Add map link for their municipality
    municipio = user.get("municipio", "")
    coords = get_coords_for_municipio(municipio)
    if coords:
        response += (
            f"\n\n📍 [{municipio} en mapa]"
            f"(https://maps.google.com/?q={coords[0]},{coords[1]})"
        )

    # Header with bancada context
    header = (
        f"📜 *Ponencia preparada para {user.get('nombre_completo', 'Concejal')}*\n"
        f"Bancada: {bancada.get('nombre', '?')} — {bancada.get('posicion', '?')}\n"
        f"Municipio: {municipio}\n"
        f"{'─' * 30}\n\n"
    )

    await agent._send_response(chat_id, header + response)

    # Save to interactions for tracking
    async with get_session() as session:
        from sqlalchemy import text as sql_text
        await session.execute(
            sql_text(
                "INSERT INTO interactions (user_id, telegram_id, nombre_concejal, "
                "municipio, provincia, bancada_id, bancada_nombre, question, response, "
                "voice_used) "
                "VALUES (:uid, :tid, :nombre, :mun, :prov, :bid, :bname, :q, :r, 'ponencia')"
            ),
            {
                "uid": user["id"], "tid": user_id,
                "nombre": user.get("nombre_completo", ""),
                "mun": municipio,
                "prov": user.get("provincia", ""),
                "bid": bancada_id,
                "bname": bancada.get("nombre", ""),
                "q": f"/preparar_ponencia {ideas}" if ideas else "/preparar_ponencia",
                "r": response[:2000],
            },
        )
