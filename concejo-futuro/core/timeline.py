"""TavoDebate - Timeline de eventos automáticos del taller."""

TIMELINE = [
    {"minute": 5, "type": "tweet", "data": {
        "author": "@CundiEnLinea", "handle": "@CundiEnLinea", "verified": True,
        "text": "EN VIVO: 150 concejales debaten proyecto para usar IA en inversión rural en Cundinamarca #ConcejoDelFuturo #TavoDebate",
    }},
    {"minute": 7, "type": "tweet", "data": {
        "author": "Don Hernando 🌾", "handle": "@CampesinoSumapaz",
        "text": "Ojalá esta vez SÍ nos pregunten a los del campo antes de decidir",
        "reply_to": "@CundiEnLinea",
    }},
    {"minute": 8, "type": "tweet", "data": {
        "author": "TechDefensor", "handle": "@TechDefensor", "verified": True,
        "text": "Por fin! Cundinamarca avanzando en innovación para el campo",
        "reply_to": "@CundiEnLinea",
    }},
    {"minute": 9, "type": "tweet", "data": {
        "author": "Red Veedurías Cund.", "handle": "@VeedurCundi",
        "text": "Recordemos Centros Poblados. $70.000M robados con promesas de internet rural. #NoMásCorrupción",
        "reply_to": "@CundiEnLinea",
    }},
    {"minute": 18, "type": "stakeholder", "data": {
        "actor": "unal",
        "action": "carta",
        "message": "La Universidad Nacional envía carta de apoyo condicionado al SIADR, ofreciendo auditoría gratuita del algoritmo.",
    }},
    {"minute": 25, "type": "tweet", "data": {
        "author": "Don Hernando 🌾", "handle": "@CampesinoSumapaz",
        "text": "¿Alguien les preguntó a los de la vereda El Retiro si quieren que un algoritmo decida si les ponen luz?",
    }},
    {"minute": 27, "type": "tweet", "data": {
        "author": "María de Fusa", "handle": "@MariaFusa",
        "text": "En mi vereda 15 años pidiendo un poste de luz. Si la IA lo resuelve, bienvenida",
        "reply_to": "@CampesinoSumapaz",
    }},
    {"minute": 30, "type": "tweet", "data": {
        "author": "Don Hernando 🌾", "handle": "@CampesinoSumapaz",
        "text": "'Falta de datos' = no existimos para el Estado. Pero para cobrar impuestos sí existimos. #ConcejoDelFuturo",
        "viral": True,
    }},
    {"minute": 35, "type": "tweet", "data": {
        "author": "Red Veedurías Cund.", "handle": "@VeedurCundi",
        "text": "¿Quiénes son los dueños de TechCundi S.A.S.? Estamos buscando en RUES. Concejales: ¿ya preguntaron?",
    }},
    {"minute": 45, "type": "stakeholder", "data": {
        "actor": "asocundi",
        "action": "protesta",
        "message": "ASOCUNDI anuncia protesta de 200 campesinos frente a la Gobernación si se aprueba sin consulta previa.",
    }},
    {"minute": 48, "type": "tweet", "data": {
        "author": "Gob. Cundinamarca", "handle": "@GobCundinamarca", "verified": True,
        "text": "El proyecto SIADR incluye consultas presenciales (Art. 5). Invitamos a ASOCUNDI al diálogo. #ConcejoDelFuturo",
        "reply_to": "@ASOCUNDI_Oficial",
    }},
    {"minute": 51, "type": "tweet", "data": {
        "author": "Concejal Anón", "handle": "@ConcejalAnon",
        "text": "Esto se va a calentar. La bancada rural ya está nerviosa. Fuente: yo, que estoy adentro",
    }},
    {"minute": 65, "type": "stakeholder", "data": {
        "actor": "contraloria",
        "action": "comunicado",
        "message": "La Contraloría de Cundinamarca anuncia auditoría preventiva al proyecto SIADR.",
    }},
    {"minute": 75, "type": "tweet", "data": {
        "author": "Abuela de Chía", "handle": "@AbuelaChia",
        "text": "Yo ni tengo smartphone. ¿Cómo participo en la consulta digital del Art. 5? #BrechaDigital",
    }},
    {"minute": 85, "type": "stakeholder", "data": {
        "actor": "muisca",
        "action": "tutela",
        "message": "Comunidades Muisca de Sesquilé anuncian acción de tutela por vulneración del derecho a consulta previa (Convenio 169 OIT).",
    }},
    {"minute": 95, "type": "tweet", "data": {
        "author": "Periodista W", "handle": "@PeriodistaW", "verified": True,
        "text": "Estamos verificando la última noticia sobre el SIADR. Hasta ahora NO encontramos el radicado citado. Precaución. #FactCheck",
    }},
    {"minute": 97, "type": "tweet", "data": {
        "author": "Red Veedurías Cund.", "handle": "@VeedurCundi",
        "text": "Ojo concejales, no voten basados en noticias sin verificar. Esto huele a desinformación.",
        "reply_to": "@PeriodistaW",
    }},
    {"minute": 110, "type": "stakeholder", "data": {
        "actor": "diocesis",
        "action": "comunicado",
        "message": "Comunicado pastoral de la Diócesis de Facatativá: 'Pedimos discernimiento y prudencia. La tecnología debe servir al pueblo.'",
    }},
    {"minute": 120, "type": "tweet", "data": {
        "author": "Fedegán Cund.", "handle": "@FedeCundi",
        "text": "Los ganaderos de Ubaté apoyamos datos de pastos para optimizar lechería. Pero ¿quién paga los sensores IoT? #SIADR",
    }},
    {"minute": 135, "type": "stakeholder", "data": {
        "actor": "gobernacion",
        "action": "ultimatum",
        "message": "La Gobernación advierte: si el proyecto no se aprueba hoy, los $1.200M de regalías se reasignan a Bogotá. Quedan 45 minutos.",
    }},
    {"minute": 150, "type": "tweet", "data": {
        "author": "TechCundi", "handle": "@TechCundi", "verified": True,
        "text": "Anuncio: si el Concejo aprueba, liberamos el código fuente del SIADR bajo licencia GPL. Transparencia total. #OpenGov",
    }},
    {"minute": 160, "type": "tweet", "data": {
        "author": "Concejal Anón", "handle": "@ConcejalAnon",
        "text": "Ya se cerraron las enmiendas. El momento de la verdad se acerca. Las bancadas negocian a puerta cerrada.",
    }},
]
