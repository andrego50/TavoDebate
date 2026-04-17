# TavoDebate — Arquitectura del Sistema

## Descripción General

**TavoDebate** es un sistema multi-agente para simulaciones legislativas interactivas. Diseñado para un taller donde 150 concejales reales de Cundinamarca debaten un proyecto de ordenanza ficticio: el **SIADR** (Sistema Inteligente de Asignación de Recursos para el Desarrollo Rural).

Los participantes interactúan vía **Telegram** con un bot que simula un debate legislativo completo, incluyendo fases de ponencia, preguntas, investigación, debate, enmiendas y votación.

---

## Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Bot | python-telegram-bot v21 (webhooks) |
| API/Orquestación | FastAPI + Uvicorn |
| Base de datos | PostgreSQL 16 + SQLAlchemy 2.0 async |
| Message bus | Redis 7 (Streams + Pub/Sub) |
| LLM primario | DeepSeek Chat |
| LLM fallback | Kimi / Moonshot |
| Transcripción | OpenAI Whisper API |
| Text-to-Speech | Edge-TTS (voces colombianas) |
| Dashboard | Streamlit |
| Pantalla proyector | HTML + WebSocket |
| Geodashboard | HTML + Leaflet + Chart.js |
| Contenedores | Docker Compose |

---

## Arquitectura Multi-Agente

```
┌─────────────────────────────────────────────────┐
│                  TELEGRAM                        │
│            (150 concejales)                      │
└──────────────────┬──────────────────────────────┘
                   │ webhook
          ┌────────▼────────┐
          │   ORCHESTRATOR  │  FastAPI :8000
          │  (enrutador)    │
          └───┬─────────┬───┘
              │ Redis    │
    ┌─────────▼───┐ ┌───▼──────────┐
    │ CHAT AGENT  │ │ CHAT AGENT   │  ← Consumer Group (2+ réplicas)
    │ (réplica 1) │ │ (réplica 2)  │
    └──────┬──────┘ └──────┬───────┘
           │               │
    ┌──────▼───────────────▼───────┐
    │         REDIS BUS            │
    │  Streams: telegram:incoming  │
    │           telegram:outgoing  │
    │           interaction:new    │
    │  Pub/Sub: timer:update       │
    │           layout:change      │
    │           pantalla:*         │
    └──┬────┬────┬────┬────┬──────┘
       │    │    │    │    │
   ┌───▼┐┌──▼┐┌─▼──┐┌▼──┐┌▼────────┐
   │INTEL││CTL││SIM ││AUD││PANTALLA │
   │agent││   ││    ││IO ││  agent  │
   └─────┘└───┘└────┘└───┘└─────────┘
```

### Agentes

| Agente | Archivo | Puerto | Función |
|---|---|---|---|
| **Orchestrator** | `agents/orchestrator.py` | 8000 | Recibe webhooks de Telegram, enruta mensajes, envía respuestas |
| **Chat Agent** | `agents/chat_agent.py` | — | Procesa mensajes, corre **Tavo** (orquestador de asesores en `core/advisor_team.py`), maneja comandos y memoria persistente |
| **Intel Agent** | `agents/intel_agent.py` | — | Clasifica interacciones, genera briefings, detecta cambios de posición |
| **Control Agent** | `agents/control_agent.py` | — | Ejecuta broadcasts, bombas, fake news, presión, gabinete |
| **Simulation Agent** | `agents/simulation_agent.py` | — | Timer, fases del taller, timeline de eventos automáticos |
| **Audio Agent** | `agents/audio_agent.py` | — | Transcripción Whisper, generación TTS Edge-TTS |
| **Pantalla Agent** | `agents/pantalla_agent.py` | 8080 | Sirve pantalla de proyector + WebSocket para actualizaciones |

### Comunicación Redis

**Streams** (persistentes, con consumer groups y ACK):
- `telegram:incoming` — Mensajes entrantes de Telegram
- `telegram:outgoing` — Mensajes para enviar por Telegram
- `interaction:new` — Interacciones clasificadas para Intel

**Pub/Sub** (efímeros, broadcast):
- `timer:update` — Actualización del temporizador cada segundo
- `layout:change` — Cambio de layout de la pantalla
- `pantalla:tweet` — Tweets para la pantalla
- `pantalla:news` — Noticias para la pantalla
- `pantalla:ticker` — Texto para el ticker
- `simulation:control` — Pausa/resume simulación
- `audio:generate_tts` — Solicitudes de generación TTS

---

## Estructura de Directorios

```
concejo-futuro/
├── agents/                    # Agentes del sistema
│   ├── base_agent.py          # Clase base con Redis + health
│   ├── runner.py              # Entry point (selecciona agente por AGENT_TYPE)
│   ├── orchestrator.py        # FastAPI + webhook Telegram
│   ├── chat_agent.py          # Procesamiento de mensajes
│   ├── intel_agent.py         # Inteligencia y briefings
│   ├── control_agent.py       # Control de facilitador
│   ├── simulation_agent.py    # Timer + timeline
│   ├── audio_agent.py         # Whisper + Edge-TTS
│   └── pantalla_agent.py      # Pantalla proyector + WebSocket
├── core/                      # Lógica de negocio y datos
│   ├── config.py              # Configuración (Pydantic Settings)
│   ├── redis_bus.py           # RedisBus dual (Streams + Pub/Sub)
│   ├── llm_client.py          # Cliente LLM con circuit breaker
│   ├── voices.py              # 5 voces IA con system prompts
│   ├── bombs.py               # 8 bombas informativas
│   ├── fakenews.py            # 6 fake news para debriefing
│   ├── gabinete.py            # Gabinete del alcalde (11 entidades)
│   ├── dossiers.py            # Dossiers privados por bancada
│   ├── stakeholders.py        # 16 stakeholders de Cundinamarca
│   ├── timeline.py            # ~22 eventos automáticos por minuto
│   └── memory_manager.py      # Gestión de contexto adaptativo
├── db/                        # Base de datos
│   ├── schema.sql             # 18+ tablas PostgreSQL
│   └── database.py            # SQLAlchemy async engine
├── handlers/                  # Handlers de comandos Telegram
│   ├── onboarding.py          # Registro en 4 pasos
│   ├── admin_handlers.py      # Comandos de administrador
│   ├── proposal_handlers.py   # /proponer, /apoyar
│   ├── voting_handlers.py     # Votación con inline keyboards
│   ├── negotiation_handlers.py # Negociación entre bancadas
│   ├── phase_handlers.py      # /estado
│   ├── pressure_handlers.py   # Tipos de presión política
│   ├── gabinete_handlers.py   # Gabinete del alcalde
│   ├── voice_handler.py       # Notas de voz
│   └── certificate_generator.py # Certificados PDF
├── services/                  # Servicios reutilizables
│   ├── tts_engine.py          # Motor Edge-TTS
│   ├── classifier.py          # Clasificación con LLM
│   ├── briefing.py            # Generación de briefings
│   ├── ponencia.py            # Análisis de ponencias
│   ├── alert_generator.py     # Alertas visuales (Playwright)
│   ├── media_manager.py       # Gestión de archivos multimedia
│   └── proactive_engine.py    # Motor proactivo de intervenciones
├── dashboard/                 # Panel de control
│   └── streamlit_app.py       # Dashboard Streamlit (5 pestañas)
├── geodashboard/              # Mapa interactivo
│   ├── index.html             # Leaflet + Chart.js
│   └── data/
│       └── datos_municipales.json  # 30 municipios piloto
├── web/                       # Pantalla de proyector
│   └── pantalla.html          # Split-screen HTML + WebSocket
├── docker-compose.yml         # Orquestación de servicios
├── Dockerfile                 # Imagen única multi-agente
├── requirements.txt           # Dependencias Python
└── .env.example               # Variables de entorno
```

---

## Mecánica del Taller

### 6 Bancadas

| Bancada | Posición | Concejales |
|---|---|---|
| Alianza Verde | A FAVOR CON RESERVAS | ~25 |
| Centro Democrático | EN CONTRA | ~25 |
| Pacto Histórico | NEUTRO-ESCÉPTICO | ~25 |
| Partido Liberal | A FAVOR | ~25 |
| Partido Conservador | A FAVOR PARCIAL | ~25 |
| Colombia Humana - UP | EN CONTRA | ~25 |

Cada bancada tiene un **dossier privado** con información confidencial, vulnerabilidades y estrategias.

### 5 Voces IA

| Voz | Comando | Personalidad |
|---|---|---|
| Ciudadano Rural | `/voz_rural` | Campesino de vereda, desconfiado de la tecnología |
| Experto Tech | `/voz_experto` | Analista con datos, favorable al SIADR |
| Contraloría | `/voz_contraloria` | Fiscalizador, enfocado en anticorrupción |
| Empresa Tech | `/voz_empresa` | TechCundi, defiende la propuesta técnica |
| Alcalde | `/voz_alcalde` | Político pragmático, busca consenso |

### 8 Fases del Taller

1. **Registro** — Onboarding por Telegram (5 pasos, todo por botones salvo el nombre)
2. **Ponencia** — Presentación del proyecto; para el **rol alcalde**, `/preparar_ponencia` dispara una entrevista guiada de 8 preguntas antes de compilar la pieza
3. **Preguntas** — Tavo coordina al equipo de asesores según la pregunta
4. **Investigación** — Consulta de dossiers y datos (con búsqueda web DuckDuckGo)
5. **Debate** — Debate abierto entre bancadas
6. **Enmiendas** — Propuestas de modificación al articulado
7. **Votación** — Timer fresco de 5 min por cada `/fase votacion`; al cerrarse, resultado automático con trazabilidad de votaciones previas
8. **Debriefing** — Revelación de fake news, certificados

### Elementos Dramáticos

- **8 bombas informativas**: datos reales de corrupción, presupuesto, medio ambiente
- **6 fake news**: noticias falsas que se revelan en el debriefing
- **16 stakeholders**: actores reales de Cundinamarca con posiciones definidas
- **~22 eventos de timeline**: tweets y acciones de stakeholders programados por minuto
- **Gabinete del alcalde**: 11 entidades como herramienta de presión política
- **Sistema de presión**: 10 tipos de presión con niveles de gravedad

---

## Tavo + 10 Asesores Especializados

La principal interfaz del participante con el sistema es **🧠 Tavo**, un jefe de gabinete virtual (`core/advisor_team.py`) que por defecto recibe cada pregunta y:

1. **Triage por keywords** (`pick_relevant_advisors` en `core/advisors.py`) selecciona hasta 3 de 10 especialistas.
2. **Fan-out paralelo** con `asyncio.gather` — cada asesor usa su system prompt estricto (dominio, vocabulario, formato, prohibiciones) y puede hacer una búsqueda web individual (`<<<BUSCAR>>>…<<<FIN_BUSCAR>>>`).
3. **Síntesis ejecutiva** — Tavo compila las respuestas preservando la voz de cada asesor y cierra con un bloque `🎯 TAVO — Recomendación del gabinete`.

Los 10 dominios (cada uno con formato propio):

| # | Asesor | Formato | Prohibiciones explícitas |
|---|---|---|---|
| 1 | ⚖️ Jurídico | Marco normativo → Riesgo → Precedente → Recomendación | No cifras, no tuits, no bancadas |
| 2 | 📢 Comunicaciones | Tuit / Mensaje-clave + Titular + Soundbite + Réplica | No leyes, no cifras exactas |
| 3 | 📊 Económico | Cifra-clave → Fuente → Comparativo → Impacto fiscal | No tuits, no bancadas, no leyes |
| 4 | 🏛️ Político | Objetivo → Mapa de fuerzas → Jugada → Contrapartida → Riesgo | No cifras, no tuits, no leyes |
| 5 | 💻 Tecnológico | Stack → Infraestructura → Riesgo → Alternativa | No catastro metodológico, no bancadas |
| 6 | 🗺️ Catastral | Hallazgo → Marco CONPES/Ley → Riesgo catastral → Salida técnica | No tarifas (eso es fiscal) |
| 7 | 🌾 Agrario/Rural | Perfil productor → Impacto familia → Efecto territorial → Protección | No macro, no tuits |
| 8 | 💰 Fiscal/Tributario | Tarifa → Norma → Instrumento de alivio → Efecto recaudo | No métodos de avalúo |
| 9 | 🤝 Participación ciudadana | Actor social → Mecanismo → Cronograma → Riesgo de conflicto | No medios, no bancadas |
| 10 | 📐 Gerencia pública | Cadena de valor → Indicadores → Arreglo institucional → Hitos | No normas, no tuits |

Cada asesor rechaza explícitamente los dominios de los demás (redirige al especialista correcto) para que la diferenciación sea visible en la respuesta.

---

## Memoria y Contexto en Tiempo Real

Cada mensaje al chat injecta un bloque de contexto en vivo (en `core/memory_manager._get_live_context`) para que Tavo y los asesores nunca respondan a ciegas:

- **Fase actual** del ejercicio (escrita a Redis por `simulation_agent`).
- **Votación en curso o última cerrada** (desde `voting_sessions`).
- **Últimos 6 tuits** de la pantalla con marcadores de reply/quote (`tavodebate:recent_tweets`).
- **Últimos 8 eventos** de la pantalla: bombas, fake news, alertas, presiones, comunicados (`tavodebate:pantalla_history`).
- **Últimas 5 consultas** del participante con el tag del asesor usado.
- **Resumen persistente de sesión** (`users.session_summary`) refrescado en background cada 5 interacciones por un LLM que lee las últimas 15 Q&A.

Un preámbulo explícito instruye al LLM a cruzar-referenciar ese bloque antes de responder: *"NUNCA respondas como si no estuvieras al tanto de lo que acaba de pasar."*

---

## Base de Datos

18+ tablas en PostgreSQL 16:

- `users` — Concejales registrados (nombre, bancada, provincia, municipio, voz)
- `interactions` — Todas las interacciones con clasificación LLM
- `proposals` — Enmiendas propuestas por concejales
- `votes` / `voting_sessions` — Votaciones nominales
- `bancada_state` — Estado por bancada (cohesión, posición, actividad)
- `debate_state` — Estado global del debate (fase, temperatura, tema)
- `intelligence_reports` — Briefings generados por Intel Agent
- `proactive_proposals` — Propuestas proactivas del sistema
- `ponencias` — Ponencias transcritas y analizadas
- `negotiations` — Negociaciones entre bancadas
- `pressure_events` — Eventos de presión política
- `gabinete_events` — Intervenciones del gabinete
- `fakenews_impact` — Impacto de fake news por usuario

Vistas: `bancada_summary`, `active_users`, `vote_results`, `tema_distribution`

---

## Patrones Técnicos

### Circuit Breaker (LLM)
- Proveedor primario: DeepSeek
- Fallback: Kimi/Moonshot
- 3 fallos consecutivos → circuito abierto por 60s
- Respuestas de emergencia hardcoded como último recurso

### Caché de Respuestas
- Redis con TTL de 5 minutos
- Key: MD5(voice + question)
- Evita llamadas duplicadas al LLM

### Consumer Groups (Chat Agent)
- 2+ réplicas del Chat Agent
- Cada réplica consume del stream `telegram:incoming` como grupo "chat_agents"
- Redis garantiza que cada mensaje se procese exactamente una vez

### Memoria Adaptativa
- **Nivel 1**: Prompt inmediato (~4200 tokens) con contexto de bancada y debate
- **Nivel 2**: Resúmenes rolling en PostgreSQL
- **Nivel 3**: Historial completo para analytics post-taller

---

## Visualización

### Pantalla de Proyector (`web/pantalla.html`)
- Split-screen fullscreen con CSS Grid
- 3 paneles: Twitter (feed simulado), Noticias, Dashboard
- Header con fase + timer + barra de progreso
- Ticker inferior con texto scrolling
- Overlay de crisis para momentos dramáticos
- 6 modos de layout: normal, ponencia, votación, twitter, crisis, oscura
- WebSocket para actualizaciones en tiempo real

### Geodashboard (`geodashboard/index.html`)
- Mapa Leaflet de Cundinamarca con 30 municipios piloto
- 10 capas toggleables (provincias, piloto, alumbrado, agro, IoT, NBI, votación...)
- Panel lateral con datos detallados por municipio
- Gráfico radar de impacto en 5 dimensiones
- Modo ponencia con navegación provincia por provincia
- Panel de votación en vivo con animación de confetti
- KPIs en barra superior

### Dashboard Streamlit (`dashboard/streamlit_app.py`)
- 5 pestañas: Monitor, Control, Medios, Concejales, Sala de Crisis
- Auto-refresh cada 5 segundos
- Control directo de broadcasts, bombas, fake news, fases, votación
- Tabla filtrable de concejales
- Timeline y revelación de fake news

---

## Despliegue

### Variables de Entorno (ver `.env.example`)

```
TELEGRAM_BOT_TOKEN=       # Token del bot de Telegram
TELEGRAM_WEBHOOK_URL=     # URL pública del webhook
DEEPSEEK_API_KEY=         # API key de DeepSeek
KIMI_API_KEY=             # API key de Kimi/Moonshot
OPENAI_API_KEY=           # API key de OpenAI (Whisper)
DATABASE_URL=             # postgresql+asyncpg://...
REDIS_URL=                # redis://redis:6379
ADMIN_IDS=                # IDs de Telegram de administradores
```

### Docker Compose

```bash
# Iniciar todos los servicios
docker compose up -d

# Ver logs
docker compose logs -f orchestrator
docker compose logs -f agent-chat

# Escalar chat agents
docker compose up -d --scale agent-chat=4
```

### Servicios

| Servicio | Puerto | Replicas |
|---|---|---|
| PostgreSQL | 5432 | 1 |
| Redis | 6379 | 1 |
| Orchestrator | 8000 | 1 |
| Chat Agent | — | 2+ |
| Intel Agent | — | 1 |
| Control Agent | — | 1 |
| Simulation Agent | — | 1 |
| Audio Agent | — | 1 |
| Pantalla Agent | 8080 | 1 |
| Streamlit Dashboard | 8501 | 1 (manual) |

### Inicio Manual del Dashboard

```bash
cd dashboard
streamlit run streamlit_app.py --server.port 8501
```

### Geodashboard

```bash
# Abrir directamente en el navegador
open geodashboard/index.html

# O servir con cualquier servidor HTTP
python -m http.server 8082 --directory geodashboard
```
