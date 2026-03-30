"""TavoDebate - Tweets predefinidos y reacciones a bombas/fakenews."""

# Tweets de reacción automática cuando se lanza una bomba
BOMB_TWEETS = {
    1: [
        {"author": "@VeedurCundi", "text": "La misma empresa que hizo el estudio de viabilidad ejecutará el SIADR? Eso huele a Centros Poblados 2.0. Concejales: exijan licitación transparente ANTES de votar. No repitamos la historia del MinTIC. #ConcejoDelFuturo #SIADR"},
        {"author": "@PeriodistaCundi", "text": "HILO: Revisé el contrato de consultoría del SIADR. La empresa TechCundi SAS fue creada hace 14 meses, su único contrato anterior fue... el estudio de viabilidad del mismo SIADR. Coincidencia? #Transparencia #Cundinamarca"},
    ],
    2: [
        {"author": "@EconomistaCundi", "text": "$1.200 millones en regalías que se pierden si no se aprueba antes de junio? Eso no es argumento técnico, es chantaje. Un buen proyecto se defiende solo, no necesita fecha de vencimiento para presionar votos. #SIADR"},
        {"author": "@ConcejalaIndep", "text": "Que nos digan que perdemos plata si no votamos YA es la definición de presión indebida. Señor Gobernador: si el proyecto es bueno, dénos tiempo de estudiarlo bien. La plata no justifica malas decisiones. #ConcejoDelFuturo"},
    ],
    3: [
        {"author": "@AmbientalistasCundi", "text": "Baterías de litio en zonas de recarga hídrica! El SIADR quiere modernizar el campo pero a costa del AGUA? 12 de 30 municipios piloto están en riesgo. Exigimos estudio de impacto ambiental YA. #AguaEsVida #SIADR"},
        {"author": "@CampesinoSumapaz", "text": "Nos quieren poner sensores con baterías contaminantes al lado de nuestros nacederos de agua. Nosotros cuidamos estas montañas hace 200 años. Que la CAR investigue antes de que sea tarde. #Sumapaz #NoAlRiesgo"},
    ],
    4: [
        {"author": "@ProfesorUNAL", "text": "Un sistema de IA que necesita internet para funcionar en un departamento donde el 68% rural NO tiene conectividad. Es como vender carros en un pueblo sin carreteras. Primero lo primero, señores. #BrechaDigital #SIADR"},
        {"author": "@AlcaldeRural", "text": "En mi municipio ni siquiera tenemos señal de celular estable. Me van a decir que un algoritmo de IA va a funcionar aquí? Inviertan primero en conectividad básica, después hablamos de inteligencia artificial."},
    ],
    5: [
        {"author": "@TransparenciaCO", "text": "El gerente de la empresa del SIADR donó $45M a la campaña del gobernador según el CNE. No es ilegal, pero SÍ es un conflicto de interés que los concejales deben evaluar. Quién realmente se beneficia? #SigaLaPlata"},
        {"author": "@OpinionCundi", "text": "Donaciones de campaña y contratos públicos: la combinación perfecta para la corrupción legal en Colombia. El SIADR puede ser un buen proyecto, pero este conflicto de interés debe resolverse ANTES de votar."},
    ],
    6: [
        {"author": "@DefensoriaPueblo", "text": "ALERTA: El SISBEN rural de Cundinamarca tiene 30-40% de subregistro. Si el SIADR prioriza con estos datos, los municipios más pobres y aislados serán INVISIBLES para el algoritmo. La IA no puede ser ciega a la pobreza. #SIADR"},
        {"author": "@LiderComunitario", "text": "En mi vereda ni siquiera nos censaron. Si el SIADR usa datos del SISBEN para decidir dónde invertir, nosotros no existimos. Otra vez nos dejan por fuera. Actualicen los datos primero! #CundinamarcaRural"},
    ],
    7: [
        {"author": "@DataScientistCO", "text": "El estudio de viabilidad del SIADR usa datos de 2019. Desde entonces: pandemia, migraciones, desastres naturales. El censo agropecuario es de 2014! Esto no es inteligencia artificial, es adivinanza con datos viejos. #SIADR #DatosObsoletos"},
        {"author": "@ConcejalesCundi", "text": "Pregunta legítima: cómo puede un algoritmo de IA tomar buenas decisiones si los datos que usa tienen 5-10 años de desactualización? Esto no es innovación, es automatizar la ignorancia. #ConcejoDelFuturo"},
    ],
    8: [
        {"author": "@VozCampesina", "text": "50 campesinos de Sumapaz lo dijeron claro: 'No sabemos qué es un algoritmo pero sí sabemos qué vereda no tiene luz.' En 2018 prometieron internet, en 2020 agua, en 2022 vías. NADA llegó. Ahora prometen IA. #NoMasElefantesBlancos"},
        {"author": "@LiderJAC_Sumapaz", "text": "Llevamos décadas esperando lo básico: luz, agua, vías. Ahora quieren saltarse todo eso e ir directo a la inteligencia artificial? Los campesinos no comemos sensores IoT. Primero lo básico, señores concejales."},
    ],
}

# Tweets de reacción automática cuando se lanza una fakenews
FAKENEWS_TWEETS = {
    1: [
        {"author": "@GobCundinamarca", "text": "Excelente noticia! $5.000M adicionales del MinTIC para el SIADR si lo aprobamos antes de junio. Cundinamarca será referente nacional en innovación rural. Los concejales tienen una oportunidad histórica! #SIADR #Innovacion"},
    ],
    2: [
        {"author": "@IndigenaCundi", "text": "Si la Universidad Nacional confirma sesgo del 40% contra comunidades indígenas, el SIADR es discriminatorio. Exigimos que se retire el proyecto hasta que se corrija. Los territorios étnicos no son datos, son pueblos. #ConsultaPrevia"},
    ],
    3: [
        {"author": "@OposicionCundi", "text": "ESCÁNDALO: si es cierto que 3 concejales de nuestra bancada negociaron su voto a cambio de municipios en Fase 1, deben renunciar. La Oposición no se vende. Exigimos nombres y transparencia. #ConcejoDelFuturo"},
    ],
    4: [
        {"author": "@AntiCorrupcionCO", "text": "La Procuraduría investiga al Gobernador por peculado en fondos del SIADR? $800M desviados a publicidad? Concejales: votar a favor de este proyecto los hace CÓMPLICES de un posible delito. Piénsenlo bien. #SIADR #Corrupcion"},
    ],
    5: [
        {"author": "@TechEnthusiast", "text": "Google y Microsoft interesados en apoyar el SIADR con tecnología GRATUITA! Esto confirma que Cundinamarca está haciendo algo bien. Los concejales que voten en contra le están cerrando la puerta al futuro del campo. #SIADR #GoogleCloud"},
    ],
    6: [
        {"author": "@DiplomatiaCO", "text": "El Banco Mundial clasifica al SIADR como 'modelo replicable'! $20M USD en cooperación si se aprueba. Cundinamarca puede liderar la transformación digital rural en toda América Latina. Histórico. #BancoMundial #SIADR"},
    ],
}

# Tweets predefinidos para el timeline del evento (el admin usa /tweet 1, /tweet 2, etc.)
TIMELINE_TWEETS = {
    1: {"author": "@ConcejoCund", "text": "Arranca la sesión del Gran Concejo del Futuro de Cundinamarca! 116 municipios representados. Hoy se debate el proyecto SIADR: inteligencia artificial para priorizar inversión rural. Sigan el debate en vivo. #ConcejoDelFuturo #Cundinamarca"},
    2: {"author": "@AlcaldeCundi", "text": "Presento ante el Concejo el Proyecto de Acuerdo 001-2026: el SIADR. Un sistema de IA para que las decisiones de inversión rural se tomen con datos, no con clientelismo. $2.400M, 30 municipios piloto, 10.200 familias. #SIADR"},
    3: {"author": "@CampesinosGirardot", "text": "Desde Girardot exigimos que el SIADR incluya monitoreo de calidad del agua en el Alto Magdalena. De qué sirve tecnología agrícola si el río está contaminado? Los sensores deben medir lo que importa. #RíoMagdalena #SIADR"},
    4: {"author": "@JovenesChia", "text": "Como jóvenes rurales de Chía apoyamos la tecnología en el campo PERO exigimos que nos capaciten. No queremos sensores que solo los ingenieros de Bogotá entiendan. Inclusión digital real, no cosmética. #JuventudRural #SIADR"},
    5: {"author": "@MujeresRuralesCundi", "text": "Las mujeres campesinas producimos el 40% de los alimentos de Cundinamarca pero no aparecemos en las estadísticas. Si el SIADR no nos cuenta, su algoritmo estará ciego. Exigimos datos con enfoque de género! #MujeresRurales"},
    6: {"author": "@ContraloriaCundi", "text": "Recordamos a los concejales: la aprobación del SIADR implica $2.400M de recursos públicos. Cada peso debe tener trazabilidad completa. Exigimos cláusula de auditoría trimestral en el articulado final. #FiscalizaciónResponsable"},
    7: {"author": "@UNALCundi", "text": "Desde la Universidad Nacional ofrecemos acompañamiento técnico gratuito para auditar el algoritmo del SIADR. La transparencia algorítmica no es opcional: es un derecho. Código abierto o nada. #CienciaAbierta #SIADR"},
    8: {"author": "@GremioAgro", "text": "Los agricultores de Cundinamarca necesitamos herramientas modernas para competir. El SIADR puede ser la diferencia entre seguir adivinando el clima y tener datos reales. Pero necesitamos capacitación, no solo tecnología. #AgroCundi"},
    9: {"author": "@VeeduriaCiudadana", "text": "Hemos revisado los 5 artículos del proyecto SIADR. El Art. 4 sobre transparencia es bueno pero insuficiente: la auditoría externa debe ser PERMANENTE, no solo trimestral. Y el código debe ser auditable por cualquier ciudadano. #ControlSocial"},
    10: {"author": "@AlcaldeZipa", "text": "Zipaquirá está lista para ser municipio piloto del SIADR. Ya tenemos cobertura de internet del 78% y red de fibra óptica en cabecera. Pero los municipios sin conectividad no pueden quedarse atrás. #SabanaCentro #SIADR"},
    11: {"author": "@PadresCundi", "text": "Como padres de familia rurales preguntamos: el SIADR va a llegar a las escuelas veredales? Nuestros hijos merecen aprender sobre tecnología donde viven, no solo en las ciudades. Incluyan educación digital en el proyecto! #EducaciónRural"},
    12: {"author": "@ConcejoCund", "text": "La votación del proyecto SIADR está por comenzar. Cada concejal representa miles de familias cundinamarquesas. Voten con responsabilidad, voten con datos, voten pensando en el campo. #VotaciónSIADR #ConcejoDelFuturo"},
}
