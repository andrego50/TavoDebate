# Brief — TavoDebate para presentación académica

Documento de referencia para diseñar la presentación. Úsalo para
explicar a los estudiantes qué es el sistema, cómo se registran y qué
puede hacer cada rol. El ejercicio simula una sesión plenaria del
Concejo Municipal debatiendo un Proyecto de Acuerdo sobre
**Actualización Catastral Multipropósito en Cundinamarca**.

---

## 1. Qué es TavoDebate

Plataforma multi-agente por Telegram (+ geodashboard proyectado en
sala). Cada participante tiene un agente de IA adaptado a su rol que
lo asesora en tiempo real, le permite investigar, redactar tuits,
proponer enmiendas y votar.

- Bot: **@TavoDebate_bot** (Telegram)
- Pantalla proyectada: `https://pantalla.fastanalytics.co/pantalla`
- Dinamizador: 1 profesor con panel admin
- Tema activo: *Proyecto de Acuerdo 001-2026 — Actualización Catastral Multipropósito*

---

## 2. Registro en 5 pasos (todo por botones salvo el nombre)

1. **Nombre completo** (texto libre)
2. **Grupo institucional** (botones): Concejo / Gobierno / Sociedad
   civil / Empresa / Control
3. **Sub-rol específico** (botones; los roles con cupo lleno aparecen
   bloqueados 🔒)
4. **Provincia y municipio** (botones)
5. Concejales eligen **posición inicial**: ✅ A favor · 🟡 A favor con
   condiciones · ❌ En contra · 🤔 Indeciso. Otros roles reciben
   bancada automática según su grupo.
6. **Causa/tema principal** (8 opciones)

---

## 3. Roles disponibles y cupos

| Grupo | Rol | Vota | Cupo máximo | Nota |
|---|---|---|---|---|
| **Concejo** | 🎖️ Presidente del Concejo | sí | **1** | Dirige sesiones, abre votación por artículo, oficializa acuerdo |
| | 🏛️ Concejal | sí | sin límite | Cuerpo colegiado (sugerido 10-15) |
| **Gobierno** | 👔 Alcalde | no | **1** | Proponente. Hace ponencia de apertura con entrevista guiada |
| | 📐 Sec. Planeación | no | 2 | Viabilidad y metodología |
| | 💰 Sec. Hacienda | no | 2 | Presupuesto y regalías |
| | 🌾 Sec. Agricultura | no | 2 | Componente agro |
| | 📡 Dir. TIC | no | 2 | Conectividad, IoT |
| | 🧑‍🌾 Dir. UMATA | no | 2 | Puente con comunidades rurales |
| **Sociedad civil** | 🧑‍🌾 Líder campesino | no | sin límite | |
| | 🪶 Líder indígena | no | sin límite | |
| | 🏘️ Líder JAC | no | sin límite | |
| | 🌿 Ambientalista | no | sin límite | |
| | 📰 Periodista | no | sin límite | |
| **Empresa** | 🏢 TechCundi | no | sin límite | Representante de la firma ejecutora |
| | 🌽 Gremio agrícola | no | sin límite | |
| **Control** | 📋 Contralor Departamental | no | **1** | |
| | ⚖️ Personero Municipal | no | sin límite | |
| | 👁️ Veedor Ciudadano | no | sin límite | |

El sistema impone los cupos automáticamente en el onboarding.

---

## 4. El agente: Tavo + 10 asesores especializados

Por defecto cada participante interactúa con 🧠 **Tavo**, su jefe de
gabinete. Tavo recibe la pregunta, **triage por palabras clave**
selecciona los 3 asesores más relevantes, los consulta **en
paralelo**, y compila una respuesta consolidada con la voz de cada
especialista + una **recomendación ejecutiva** final.

Cada asesor tiene dominio estricto, vocabulario obligatorio y formato
propio (no son intercambiables):

| # | Asesor | Especialidad |
|---|---|---|
| 1 | ⚖️ Jurídico | Leyes, artículos, sentencias, vicios, competencias |
| 2 | 📢 Comunicaciones | Tuits listos, titulares, soundbites, réplicas |
| 3 | 📊 Económico | Cifras macro, SGP, regalías, ROI, impacto fiscal |
| 4 | 🏛️ Político | Bancadas, quórum, contrapartidas, jugadas |
| 5 | 💻 Tecnológico | Stack, infraestructura, riesgo técnico |
| 6 | 🗺️ Catastral | Avalúos, métodos, CONPES 3958, ciclo catastral |
| 7 | 🌾 Agrario/Rural | Economía campesina, UAF, capacidad de pago |
| 8 | 💰 Fiscal/Tributario | Predial, tarifas, exenciones, fondo de alivio |
| 9 | 🤝 Participación ciudadana | Audiencias, veedurías, diálogo social |
| 10 | 📐 Gerencia pública | Cadena de valor, Sinergia, MGA, indicadores |

Todos pueden **buscar en internet** (DuckDuckGo) cuando necesitan datos frescos.

El usuario puede hablar con un especialista directo con `/asesores`.

---

## 5. Qué puede hacer cada rol (capacidades)

### Todos los participantes
- `/tutorial` — repaso contextual de su rol
- `/asesores` — cambiar entre Tavo y los 10 especialistas
- `/tuitear` — publicar tuit en pantalla (sin texto abre menú para citar/responder tuits anteriores por botón)
- `/estado` — resumen personal
- Preguntar cualquier cosa en texto libre → Tavo orquesta
- **Tavo propone acciones**: cuando un asesor redacta un tuit o
  enmienda, Tavo muestra botón "🐦 Publicar tuit" / "📝 Proponer
  enmienda" → el usuario aprueba con un toque y Tavo lo ejecuta en
  su nombre.

### Concejales (grupo Concejo)
- `/preparar_ponencia` — la IA arma su ponencia de 5 puntos
- `/proponer <texto>` — presentar enmienda al articulado
- `/propuestas_todas`, `/apoyar N`
- `/votar_proyecto a_favor | en_contra | abstencion` (votación global)
- `/votar_articulo N a_favor | en_contra | abstencion` (votación por artículo)

### Presidente del Concejo (además de lo de Concejal)
- `/votacion_articulos` — abre la votación secuencial de los 5
  artículos, timer 3 min cada uno, se encadenan automáticamente
- `/compilar_acuerdo` — Tavo redacta el texto final integrando
  artículos aprobados + enmiendas con mayor apoyo; preview con botones
  ✅ Oficializar / 🔄 Regenerar / ❌ Cancelar
- Al oficializar, el acuerdo se envía a todos firmado como
  "📜 **EL PRESIDENTE DEL CONCEJO COMUNICA** … Fdo: <nombre>"

### Alcalde
- `/preparar_ponencia` → dispara una **entrevista guiada de 8
  preguntas** (problema, dato contundente, pilotos, blindaje ético,
  consulta, concesiones, crisis, cierre). Al final Tavo compila la
  ponencia de apertura de 500-700 palabras usando SOLO sus respuestas.

### Dinamizador (admin — el profesor)
- `/fase <nombre>` — cambia la etapa del ejercicio (registro, ponencia, debate, enmiendas, votación, debriefing)
- `/broadcast` / `/presion` (sin texto) — genera un borrador contextual con IA; apruebas con botón
- `/bomba`, `/fakenews`, `/tweet` — menús con catálogo y preview
- `/ronda 3|5|10|15` — timer
- `/historial_votaciones` — trazabilidad completa
- `/asignar_rol <nombre> <rol>`, `/roles`
- `/modo_test`, `/briefing`, `/pantalla`

---

## 6. Visualización — qué ve cada audiencia

**Participantes (Telegram, pantalla personal):**
- Chat 1:1 con Tavo y los asesores
- Notificaciones de fase, votaciones, eventos
- Comunicados del Presidente

**Sala (pantalla proyectada — `pantalla.fastanalytics.co/pantalla`):**
- Mapa de Cundinamarca con pins en tiempo real
- Feed de tuits (con hilo de replies/citas)
- Gráficos de cohesión por bancada
- Resultados de votación en vivo (barras por sí/no/abstención)
- Cambios de fase con banners
- Alertas institucionales y bombas informativas

**Dinamizador (panel admin):**
- Estado (usuarios, interacciones, votos)
- Puede proyectar el geodashboard o el chat de cualquier participante
- Historial de votaciones consultable

---

## 7. Memoria y contexto en tiempo real (por qué el agente no "se pierde")

Cada mensaje que recibe un asesor trae automáticamente:

- Fase actual del ejercicio
- Última votación abierta o cerrada
- Últimos 6 tuits en pantalla (con marcadores de reply/quote)
- Últimos 8 eventos del debate (bombas, fake news, alertas, presiones)
- Últimas 5 consultas del participante con el asesor que usó
- Resumen persistente de sesión refrescado en background cada 5 interacciones

Resultado: aunque la conversación crezca, el asesor siempre responde
sabiendo qué acaba de pasar.

---

## 8. Flujo sugerido del taller (~90 min)

| Minuto | Fase | Comando dinamizador | Actividad |
|---|---|---|---|
| 0-10 | Registro | `/pin 1234` + instrucciones verbales | Todos se registran, eligen rol |
| 10-25 | Ponencia del Alcalde | `/fase ponencia_alcalde` | Alcalde usa `/preparar_ponencia` (entrevista guiada) y expone |
| 25-35 | Preguntas al alcalde | `/fase preguntas_alcalde` | Participantes preguntan; Tavo asiste |
| 35-50 | Investigación y debate | `/fase investigacion` → `/fase debate` | Consultas a asesores, tuits, fake news (`/fakenews`), bombas (`/bomba`) |
| 50-60 | Enmiendas | `/fase enmiendas` | Concejales usan `/proponer`; Tavo propone enmiendas con botones |
| 60-80 | Votación por artículo | Presidente usa `/votacion_articulos` | 5 votaciones secuenciales de 3 min cada una |
| 80-85 | Compilación y proclamación | Presidente usa `/compilar_acuerdo` → Oficializar | Tavo redacta el acuerdo final; se difunde como comunicado del Presidente |
| 85-90 | Debriefing | `/fase debriefing` | Revelación de fake news, reflexión |

---

## 9. Datos reales que alimentan el ejercicio

El articulado del proyecto (5 artículos), las cifras del contexto (76
municipios actualizados, 12.000 reclamaciones, incrementos 80-300%,
Ruta del Diálogo Catastral) y los asesores especializados están
afinados para este tema específico.

Asesores como 🗺️ Catastral, 🌾 Agrario, 💰 Fiscal y 🤝 Participación
manejan el marco normativo real (Ley 1955/2019 art. 23, CONPES 3958,
Ley 44/1990, Ley 134/1994) para que las respuestas sean rigurosas y
los estudiantes aprendan el lenguaje técnico-institucional real.
