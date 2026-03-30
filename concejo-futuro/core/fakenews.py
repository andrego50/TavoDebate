"""TavoDebate - 6 fake news prediseñadas."""

FAKE_NEWS = {
    1: {
        "text": (
            "📰 *ÚLTIMA HORA — El Espectador:*\n\n"
            "'El Ministerio TIC confirmó que asignará $5.000M adicionales "
            "al SIADR si Cundinamarca lo aprueba antes del 30 de junio. "
            "Sería el proyecto de IA más grande de un departamento en "
            "Colombia.'\n\n"
            "_Fuente: El Espectador, sección Tecnología_"
        ),
        "is_fake": True,
        "reveal_text": (
            "❌ *FAKE NEWS REVELADA:*\n\n"
            "El Ministerio TIC NO ha ofrecido $5.000M adicionales. "
            "Esta noticia fue fabricada para presionar la votación. "
            "El único presupuesto real son los $2.400M del proyecto original."
        ),
        "keywords": ["presupuesto", "mintic"],
    },
    2: {
        "text": (
            "📰 *URGENTE — Semana:*\n\n"
            "'La Universidad Nacional advierte que el algoritmo del SIADR "
            "tiene un sesgo del 40% contra municipios de mayoría indígena. "
            "Un estudio de la Facultad de Ingeniería encontró que las "
            "variables del Art. 2 subvaloran territorios étnicos.'\n\n"
            "_Fuente: Semana, sección Nación_"
        ),
        "is_fake": True,
        "reveal_text": (
            "❌ *FAKE NEWS REVELADA:*\n\n"
            "La Universidad Nacional NO ha publicado ningún estudio sobre "
            "el SIADR. El sesgo del 40% es inventado. Sin embargo, "
            "el riesgo de sesgo algorítmico en datos rurales SÍ es real "
            "— solo que no hay estudio que lo cuantifique así."
        ),
        "keywords": ["indigena", "sesgo", "universidad"],
    },
    3: {
        "text": (
            "📰 *EXCLUSIVA — Caracol Radio:*\n\n"
            "'Tres concejales de la Bancada de Oposición ya confirmaron "
            "en privado que votarán A FAVOR del SIADR a cambio de que "
            "sus municipios sean incluidos en la Fase 1. La negociación "
            "se habría cerrado anoche en un restaurante de Zipaquirá.'\n\n"
            "_Fuente: Caracol Radio, programa 6AM_"
        ),
        "is_fake": True,
        "reveal_text": (
            "❌ *FAKE NEWS REVELADA:*\n\n"
            "No existe tal negociación secreta. Esta noticia fue diseñada "
            "para generar desconfianza DENTRO de la Bancada de Oposición "
            "y acusar a compañeros de traición."
        ),
        "keywords": ["negociacion", "traicion", "oposicion"],
    },
    4: {
        "text": (
            "📰 *ALERTA — RCN Noticias:*\n\n"
            "'La Procuraduría General abrió investigación preliminar contra "
            "el Gobernador de Cundinamarca por presunto peculado en los "
            "recursos destinados al SIADR. Se habrían desviado $800M "
            "hacia contratos de publicidad.'\n\n"
            "_Fuente: RCN Noticias_"
        ),
        "is_fake": True,
        "reveal_text": (
            "❌ *FAKE NEWS REVELADA:*\n\n"
            "La Procuraduría NO ha abierto ninguna investigación sobre "
            "el SIADR. Esta noticia fue fabricada para generar pánico "
            "y que los concejales voten en contra por miedo a verse "
            "involucrados."
        ),
        "keywords": ["procuraduria", "peculado", "gobernador"],
    },
    5: {
        "text": (
            "📰 *NOTICIA — Blu Radio:*\n\n"
            "'Google y Microsoft expresaron interés en aportar tecnología "
            "gratuita al SIADR si Cundinamarca lo aprueba. Un vocero de "
            "Google Cloud dijo: Es exactamente el tipo de proyecto que "
            "buscamos apoyar en Latinoamérica.'\n\n"
            "_Fuente: Blu Radio, sección Economía_"
        ),
        "is_fake": True,
        "reveal_text": (
            "❌ *FAKE NEWS REVELADA:*\n\n"
            "Ni Google ni Microsoft han expresado interés en el SIADR. "
            "Esta noticia fue fabricada para generar entusiasmo artificial "
            "y presionar el voto a favor."
        ),
        "keywords": ["google", "microsoft", "tecnologia"],
    },
    6: {
        "text": (
            "📰 *BREAKING — W Radio:*\n\n"
            "'El Banco Mundial clasificó el SIADR de Cundinamarca como "
            "'modelo replicable' para América Latina. Si se aprueba, "
            "Colombia recibiría $20M USD en cooperación técnica para "
            "expandirlo a 5 departamentos más.'\n\n"
            "_Fuente: W Radio, corresponsal en Washington_"
        ),
        "is_fake": True,
        "reveal_text": (
            "❌ *FAKE NEWS REVELADA:*\n\n"
            "El Banco Mundial NO ha evaluado el SIADR. Los $20M USD "
            "son inventados. Aunque el BM sí financia proyectos GovTech, "
            "este proyecto no existe en su portafolio."
        ),
        "keywords": ["banco_mundial", "cooperacion", "internacional"],
    },
}
