"""TavoDebate - Dossiers privados por bancada (información asimétrica)."""

DOSSIERS = {
    1: {  # Gobierno
        "bancada": "🏛️ Gobierno",
        "posicion": "A FAVOR",
        "dossier": (
            "🔒 *DOSSIER CONFIDENCIAL — BANCADA DE GOBIERNO*\n\n"
            "Tu bancada apoya el proyecto SIADR. El alcalde cuenta con ustedes.\n\n"
            "*Lo que SABES y otros no:*\n"
            "• El Secretario de Planeación (Carlos Mendoza) es tu aliado directo. "
            "Él coordinó el estudio de viabilidad.\n"
            "• La Gobernación ya tiene $1.200M de regalías asignados. Si el Concejo "
            "no aprueba antes de junio, ese dinero se pierde.\n"
            "• El alcalde prometió que los primeros 10 municipios piloto serán "
            "elegidos por el algoritmo, NO por presión política.\n\n"
            "*Tu vulnerabilidad:*\n"
            "• Si se filtra que la empresa del estudio de viabilidad es la misma "
            "que ejecutará, tu bancada queda expuesta.\n"
            "• La oposición tiene datos sobre donaciones de campaña.\n\n"
            "*Estrategia sugerida:*\n"
            "Defiende el Art. 4 (transparencia) como escudo anticorrupción. "
            "Si te atacan con Centros Poblados, responde: 'Por eso pusimos "
            "auditoría externa en el Art. 4.'"
        ),
    },
    2: {  # Oposición
        "bancada": "⚖️ Oposición",
        "posicion": "EN CONTRA",
        "dossier": (
            "🔒 *DOSSIER CONFIDENCIAL — BANCADA DE OPOSICIÓN*\n\n"
            "Tu bancada se opone al proyecto SIADR. Creen que es otro "
            "elefante blanco tecnológico.\n\n"
            "*Lo que SABES y otros no:*\n"
            "• La Secretaria de Ambiente (María Clara Ríos) es tu aliada. "
            "Ella tiene reparos técnicos sobre los sensores IoT.\n"
            "• El gerente de la empresa ejecutora donó $45M a la campaña "
            "del gobernador. Tienes el registro del CNE.\n"
            "• Solo el 32% de las veredas tiene internet. Sin conectividad, "
            "el SIADR no puede funcionar.\n\n"
            "*Tu vulnerabilidad:*\n"
            "• Si votas en contra de TODO, te acusan de obstruir el progreso.\n"
            "• Algunos de tus concejales defienden tecnología — pueden desertar.\n\n"
            "*Estrategia sugerida:*\n"
            "No te opongas al concepto de IA. Oponte a ESTE proyecto específico "
            "por falta de garantías. Exige: consulta previa, datos actualizados, "
            "y separar consultor de ejecutor."
        ),
    },
    3: {  # Rural
        "bancada": "🌾 Rural",
        "posicion": "CONDICIONAL",
        "dossier": (
            "🔒 *DOSSIER CONFIDENCIAL — BANCADA RURAL*\n\n"
            "Tu bancada podría votar a favor SI se incluyen condiciones "
            "específicas para el campo.\n\n"
            "*Lo que SABES y otros no:*\n"
            "• La Secretaria de Agricultura (Patricia Vargas) es tu aliada "
            "principal. Ella ejecutaría el componente agrícola.\n"
            "• El componente de agricultura de precisión podría beneficiar "
            "a 480 familias por municipio piloto.\n"
            "• PERO: solo hay 2 extensionistas para 116 municipios. "
            "¿Quién capacita a los campesinos?\n\n"
            "*Tu vulnerabilidad:*\n"
            "• El alcalde puede amenazar con quitar a Vargas de Agricultura "
            "si votan en contra.\n"
            "• 86 municipios NO son piloto. Los concejales de esos municipios "
            "no tienen incentivo para votar a favor.\n\n"
            "*Estrategia sugerida:*\n"
            "Negocia la inclusión de más municipios rurales en Fase 1. "
            "Exige que la UMATA sea el puente con campesinos. Pide "
            "capacitación ANTES de implementación."
        ),
    },
    4: {  # Urbana
        "bancada": "🏙️ Urbana",
        "posicion": "PRAGMÁTICOS",
        "dossier": (
            "🔒 *DOSSIER CONFIDENCIAL — BANCADA URBANA*\n\n"
            "Tu bancada es pragmática. Votan según costo-beneficio.\n\n"
            "*Lo que SABES y otros no:*\n"
            "• El Secretario de Infraestructura (Roberto Díaz) es tu aliado. "
            "Él ejecuta el alumbrado público.\n"
            "• PERO: Infraestructura ya tiene contrato vigente de alumbrado "
            "con otra empresa. El SIADR podría romper ese contrato.\n"
            "• Los municipios de Sabana Centro y Sabana Occidente ya tienen "
            "buena cobertura de alumbrado. ¿Para qué necesitan SIADR?\n\n"
            "*Tu vulnerabilidad:*\n"
            "• Si el SIADR prioriza municipios rurales pobres (como debería), "
            "los municipios urbanos ricos quedan al final.\n"
            "• Tu base electoral puede preguntarse: '¿Por qué voté a favor "
            "de algo que beneficia a otros?'\n\n"
            "*Estrategia sugerida:*\n"
            "Exige que el Art. 2 incluya variables urbanas (densidad, "
            "seguridad nocturna, zonas comerciales). Negocia que Sabana "
            "Centro y Occidente estén en Fase 1."
        ),
    },
    5: {  # Presupuesto
        "bancada": "💰 Presupuesto",
        "posicion": "FISCALIZACIÓN",
        "dossier": (
            "🔒 *DOSSIER CONFIDENCIAL — BANCADA DE PRESUPUESTO*\n\n"
            "Tu bancada es el perro guardián del dinero público.\n\n"
            "*Lo que SABES y otros no:*\n"
            "• El Secretario de Hacienda (Fernando Castillo) es tu aliado. "
            "Él debe certificar la disponibilidad presupuestal.\n"
            "• Los $1.200M de regalías VENCEN en 24 meses. Si no se "
            "ejecutan, se reasignan a Bogotá.\n"
            "• El costo de mantenimiento anual del SIADR no está en el "
            "presupuesto. ¿Quién paga año 2, 3, 4?\n\n"
            "*Tu vulnerabilidad:*\n"
            "• Si bloqueas el presupuesto, pierdes los $1.200M de regalías "
            "para siempre.\n"
            "• La Gobernación puede presionar con otros proyectos.\n\n"
            "*Estrategia sugerida:*\n"
            "Exige que el Art. 3 incluya plan de sostenibilidad financiera "
            "a 5 años. Pide cláusula de reversión si el costo supera "
            "el 20% del presupuesto estimado. No bloquees — condiciona."
        ),
    },
    6: {  # Veeduría
        "bancada": "👁️ Veeduría",
        "posicion": "CONTROL SOCIAL",
        "dossier": (
            "🔒 *DOSSIER CONFIDENCIAL — BANCADA DE VEEDURÍA*\n\n"
            "Tu bancada representa la ciudadanía que vigila.\n\n"
            "*Lo que SABES y otros no:*\n"
            "• La Secretaria de Gobierno (Liliana Parra) es tu aliada. "
            "Ella debe organizar las consultas del Art. 5.\n"
            "• PERO: no tiene presupuesto para consultas presenciales "
            "en 116 municipios. Solo puede hacer digitales.\n"
            "• El 68% rural no tiene internet. Consulta 'digital' = "
            "excluir a la mayoría.\n\n"
            "*Tu vulnerabilidad:*\n"
            "• Si exiges consulta presencial, el proyecto se retrasa "
            "6 meses y se pierden las regalías.\n"
            "• Si aceptas consulta digital, traicionas a la gente "
            "sin internet.\n\n"
            "*Estrategia sugerida:*\n"
            "Exige que el Art. 5 incluya consulta MIXTA (digital + "
            "presencial en cabeceras). Propone que la UMATA facilite "
            "las consultas rurales. Pide veeduría ciudadana con "
            "acceso al código del algoritmo."
        ),
    },
}


def get_dossier(bancada_id: int) -> str:
    """Retorna el dossier de una bancada."""
    dossier = DOSSIERS.get(bancada_id)
    if dossier:
        return dossier["dossier"]
    return "Dossier no disponible."
