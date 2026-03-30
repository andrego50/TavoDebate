"""TavoDebate - 16 stakeholders de Cundinamarca."""

STAKEHOLDERS = {
    "gobernacion": {
        "nombre": "🏢 Gobernación de Cundinamarca",
        "actor": "Gobernador Jorge Emilio Rey",
        "posicion": "A FAVOR",
        "poder": "alto",
        "mensaje_default": (
            "La Gobernación respalda el SIADR como pilar del Plan de Desarrollo. "
            "Ya tenemos $1.200M de cofinanciación aprobados. Si no se aprueba antes "
            "del 30 de junio, esos recursos se pierden."
        ),
    },
    "sec_agricultura": {
        "nombre": "🌿 Secretaría de Agricultura de Cundinamarca",
        "actor": "Marcos Alberto Barreto García",
        "posicion": "A FAVOR",
        "poder": "alto",
        "mensaje_default": (
            "Ya invertimos $4.673M en extensión rural para 5.312 campesinos en 56 municipios. "
            "Cundinamarca aporta 594.106 ton/año de alimentos a Bogotá (39.1% del total). "
            "El SIADR complementa nuestra estrategia."
        ),
    },
    "techcundi": {
        "nombre": "💻 Consorcio TechCundi S.A.S.",
        "actor": "TechCundi S.A.S.",
        "posicion": "A FAVOR",
        "poder": "medio",
        "mensaje_default": (
            "Proponemos código abierto y capacitación gratuita para los municipios piloto. "
            "10 años de experiencia en GovTech. ROI estimado: 25-35% en 3 años."
        ),
    },
    "unal": {
        "nombre": "🎓 Universidad Nacional — Sede Bogotá",
        "actor": "Universidad Nacional de Colombia",
        "posicion": "A FAVOR CON RESERVAS",
        "poder": "medio",
        "mensaje_default": (
            "Ofrecemos auditoría gratuita del Art. 4 a cambio de acceso a datos "
            "anonimizados para investigación. El SIADR tiene potencial pero necesita "
            "transparencia algorítmica real."
        ),
    },
    "asohofrucol": {
        "nombre": "🏭 Asohofrucol + Región Metropolitana",
        "actor": "Asohofrucol Cundinamarca",
        "posicion": "A FAVOR",
        "poder": "medio",
        "mensaje_default": (
            "Proyecto 'Somos Agricultura Tropical': $4.200M para 1.000 familias campesinas. "
            "El SIADR complementa nuestro programa de fortalecimiento técnico."
        ),
    },
    "enel": {
        "nombre": "⚡ ENEL Colombia",
        "actor": "ENEL Colombia",
        "posicion": "A FAVOR",
        "poder": "medio",
        "mensaje_default": (
            "Inversión conjunta de $1.516M con la Gobernación para conectar 65 hogares "
            "en Topaipí y Viotá. Cundinamarca tiene 99.3% cobertura pero persisten hogares "
            "rurales desconectados."
        ),
    },
    "asocundi": {
        "nombre": "🌾 ASOCUNDI — Campesinos de Cundinamarca",
        "actor": "ASOCUNDI",
        "posicion": "EN CONTRA",
        "poder": "medio-alto",
        "mensaje_default": (
            "38% de nuestros municipios no tienen internet. Agro Ingreso Seguro prometió "
            "lo mismo. Si aprueban sin consulta previa, 200 campesinos marcharemos "
            "frente a la Gobernación."
        ),
    },
    "defensoria": {
        "nombre": "🛡️ Defensoría del Pueblo — Regional",
        "actor": "Defensoría del Pueblo",
        "posicion": "EN CONTRA PARCIAL",
        "poder": "medio",
        "mensaje_default": (
            "Datos geolocalizados de familias vulnerables representan un riesgo de seguridad. "
            "Exigimos audiencia pública por provincia antes de cualquier votación."
        ),
    },
    "renaf": {
        "nombre": "🌱 RENAF — Agricultura Familiar",
        "actor": "RENAF Cundinamarca",
        "posicion": "EN CONTRA",
        "poder": "medio",
        "mensaje_default": (
            "Los campesinos, indígenas y afrodescendientes producen el 70% de los alimentos "
            "del país. El SIADR no debe favorecer a grandes productores sobre pequeños."
        ),
    },
    "muisca": {
        "nombre": "🏔️ Comunidades Muisca de Sesquilé y Cota",
        "actor": "Cabildo Muisca",
        "posicion": "EN CONTRA",
        "poder": "bajo-medio",
        "mensaje_default": (
            "Nuestras tierras no son datos en un servidor. Exigimos consulta previa "
            "según Convenio 169 OIT. Acción de tutela en preparación."
        ),
    },
    "contraloria": {
        "nombre": "📋 Contraloría de Cundinamarca",
        "actor": "Contraloría Departamental",
        "posicion": "NEUTRAL",
        "poder": "alto",
        "mensaje_default": (
            "95.4% de impunidad en corrupción en Cundinamarca. Exigimos cláusula "
            "anticorrupción, verificación de beneficiarios finales y auditoría preventiva."
        ),
    },
    "medios": {
        "nombre": "📺 Medios (W Radio / El Tiempo)",
        "actor": "Medios de comunicación",
        "posicion": "NEUTRAL",
        "poder": "alto",
        "mensaje_default": (
            "Estamos investigando los vínculos del proveedor TechCundi con el caso "
            "de alumbrado de Bucaramanga."
        ),
    },
    "federacion": {
        "nombre": "🏛️ Federación de Concejales del Centro",
        "actor": "Federación de Concejales",
        "posicion": "NEUTRAL",
        "poder": "bajo",
        "mensaje_default": (
            "Si Cundinamarca aprueba, nos presionan en Boyacá y Tolima. "
            "Estamos observando con atención."
        ),
    },
    "diocesis": {
        "nombre": "⛪ Diócesis de Facatativá",
        "actor": "Diócesis de Facatativá",
        "posicion": "CONDICIONAL",
        "poder": "medio",
        "mensaje_default": (
            "Comunicado pastoral: 'La tecnología debe servir al pueblo, no al revés. "
            "Pedimos discernimiento y prudencia en esta decisión.'"
        ),
    },
    "fedegan": {
        "nombre": "🐄 Fedegán Cundinamarca — Ganaderos",
        "actor": "Fedegán Cundinamarca",
        "posicion": "A FAVOR PARCIAL",
        "poder": "medio",
        "mensaje_default": (
            "Queremos datos de pastos para optimizar ganadería lechera. "
            "Pero los costos de IoT son altos para pequeños ganaderos de Ubaté."
        ),
    },
    "fenalco": {
        "nombre": "🏪 Fenalco Cundinamarca — Comerciantes",
        "actor": "Fenalco Cundinamarca",
        "posicion": "A FAVOR",
        "poder": "bajo",
        "mensaje_default": (
            "Mejor alumbrado en vías rurales reduce accidentes de transporte de mercancía. "
            "Las vías terciarias de La Calera están en condiciones deplorables."
        ),
    },
}
