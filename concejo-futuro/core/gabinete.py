"""TavoDebate - Estructura de poder del alcalde (gabinete + institutos)."""

GABINETE = {
    "planeacion": {
        "tipo": "secretaria",
        "nombre": "🏗️ Secretaría de Planeación",
        "titular": "Ing. Carlos Mendoza",
        "presupuesto_millones": 800,
        "competencias": ["ordenamiento territorial", "datos", "proyectos de inversión"],
        "rol_siadr": "Coordinador técnico del proyecto. Tiene el estudio de viabilidad.",
        "aliado_bancada": 1,
        "aliado_tema": "infraestructura",
        "vulnerabilidad": "El estudio de viabilidad lo hizo la misma empresa que va a ejecutar",
    },
    "agricultura": {
        "tipo": "secretaria",
        "nombre": "🌾 Secretaría de Agricultura y Desarrollo Rural",
        "titular": "Dra. Patricia Vargas",
        "presupuesto_millones": 450,
        "competencias": ["agro", "extensión rural", "asistencia técnica"],
        "rol_siadr": "Ejecutora del componente de agricultura de precisión.",
        "aliado_bancada": 3,
        "aliado_tema": "agro",
        "vulnerabilidad": "Solo tiene 2 extensionistas para 116 municipios",
    },
    "infraestructura": {
        "tipo": "secretaria",
        "nombre": "🔧 Secretaría de Infraestructura y Obras Públicas",
        "titular": "Ing. Roberto Díaz",
        "presupuesto_millones": 1200,
        "competencias": ["alumbrado público", "vías", "obras civiles"],
        "rol_siadr": "Ejecutora del componente de alumbrado público.",
        "aliado_bancada": 4,
        "aliado_tema": "infraestructura",
        "vulnerabilidad": "Ya tiene contrato vigente de alumbrado con otra empresa",
    },
    "hacienda": {
        "tipo": "secretaria",
        "nombre": "💰 Secretaría de Hacienda",
        "titular": "Dr. Fernando Castillo",
        "presupuesto_millones": 0,
        "competencias": ["presupuesto", "impuestos", "tesorería", "regalías"],
        "rol_siadr": "Debe certificar disponibilidad presupuestal de $2.400M.",
        "aliado_bancada": 5,
        "aliado_tema": "hacienda",
        "vulnerabilidad": "Advirtió en privado que los recursos de regalías vencen en 24 meses",
    },
    "gobierno": {
        "tipo": "secretaria",
        "nombre": "🏛️ Secretaría de Gobierno",
        "titular": "Dra. Liliana Parra",
        "presupuesto_millones": 300,
        "competencias": ["participación ciudadana", "comunidades", "seguridad"],
        "rol_siadr": "Responsable de las consultas ciudadanas del Art. 5.",
        "aliado_bancada": 6,
        "aliado_tema": "participacion",
        "vulnerabilidad": "No tiene presupuesto para consultas presenciales en 116 municipios",
    },
    "tic": {
        "tipo": "secretaria",
        "nombre": "💻 Oficina TIC Municipal",
        "titular": "Ing. Andrés Moreno",
        "presupuesto_millones": 150,
        "competencias": ["tecnología", "conectividad", "gobierno digital"],
        "rol_siadr": "Responsable técnico de la plataforma y los servidores.",
        "aliado_bancada": 1,
        "aliado_tema": "tecnologia",
        "vulnerabilidad": "Solo tiene 3 ingenieros para todo el departamento",
    },
    "ambiente": {
        "tipo": "secretaria",
        "nombre": "🌿 Secretaría de Ambiente",
        "titular": "Bióloga María Clara Ríos",
        "presupuesto_millones": 200,
        "competencias": ["ambiente", "agua", "recursos naturales", "CAR"],
        "rol_siadr": "Debe emitir concepto ambiental sobre los sensores IoT.",
        "aliado_bancada": 2,
        "aliado_tema": "ambiente",
        "vulnerabilidad": "La CAR ya tiene reparos sobre sensores en zonas de recarga hídrica",
    },
    "educacion": {
        "tipo": "secretaria",
        "nombre": "📚 Secretaría de Educación",
        "titular": "Lic. Jorge Bernal",
        "presupuesto_millones": 600,
        "competencias": ["educación", "colegios rurales", "formación"],
        "rol_siadr": "Componente de capacitación digital a campesinos.",
        "aliado_bancada": 3,
        "aliado_tema": "educacion",
        "vulnerabilidad": "Teme que el SIADR absorba presupuesto de Computadores para Educar",
    },
}

INSTITUTOS = {
    "empumunicipal": {
        "tipo": "instituto",
        "nombre": "⚡ Empresa de Servicios Públicos Municipal",
        "titular": "Ing. Óscar Espinel",
        "presupuesto_millones": 0,
        "competencias": ["alumbrado público", "energía", "acueducto"],
        "rol_siadr": "Operadora del alumbrado. Puede resistirse si pierde control.",
        "aliado_tema": "infraestructura",
    },
    "umata": {
        "tipo": "instituto",
        "nombre": "🌱 UMATA — Unidad de Asistencia Técnica Agropecuaria",
        "titular": "Agrónomo Luis Herrera",
        "presupuesto_millones": 0,
        "competencias": ["extensión rural", "asistencia técnica", "campesinos"],
        "rol_siadr": "Puente entre el SIADR y los campesinos. Tiene la confianza del campo.",
        "aliado_tema": "agro",
    },
    "turismo": {
        "tipo": "instituto",
        "nombre": "🏔️ Instituto de Turismo y Cultura",
        "titular": "Comunicadora Andrea Suárez",
        "presupuesto_millones": 0,
        "competencias": ["turismo", "cultura", "rutas rurales"],
        "rol_siadr": "Alumbrado en rutas turísticas rurales como beneficio secundario.",
        "aliado_tema": "turismo",
    },
}

ALL_ENTITIES = {**GABINETE, **INSTITUTOS}


def get_allies_for_user(bancada_id: int, temas_interes: list[str]) -> list[tuple[str, dict]]:
    """Retorna aliados del gabinete por bancada y por tema."""
    allies = []
    for key, entity in ALL_ENTITIES.items():
        if entity.get("aliado_bancada") == bancada_id:
            allies.append(("bancada", entity))
        if entity.get("aliado_tema") and entity["aliado_tema"] in temas_interes:
            allies.append(("tema", entity))
    return allies


def format_power_map(bancada_id: int, temas_interes: list[str]) -> str:
    """Formatea el mapa de aliados para enviar al concejal."""
    allies = get_allies_for_user(bancada_id, temas_interes)
    if not allies:
        return ""

    msg = "🏛️ *TUS ALIADOS EN EL EJECUTIVO:*\n\n"
    msg += ("_Estos funcionarios del gabinete del Alcalde son cercanos a tu "
            "bancada o a los temas que defiendes._\n\n")

    seen = set()
    for tipo, entity in allies:
        name = entity["nombre"]
        if name in seen:
            continue
        seen.add(name)

        icon = "🤝" if tipo == "bancada" else "🎯"
        msg += f"{icon} *{name}*\n"
        msg += f"   {entity['titular']}\n"
        if entity.get("presupuesto_millones"):
            msg += f"   Presupuesto: ${entity['presupuesto_millones']}M COP\n"
        msg += f"   Rol en SIADR: {entity['rol_siadr']}\n"
        if entity.get("vulnerabilidad"):
            msg += f"   _{entity['vulnerabilidad']}_\n"
        msg += "\n"

    msg += ("🔒 _Si el alcalde remueve a tu aliado, pierdes tu conexión "
            "con esa cartera. Piensa bien cómo votas._")
    return msg
