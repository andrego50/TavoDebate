# Manual del Dinamizador — TavoDebate

## Qué es TavoDebate

TavoDebate es un simulador legislativo por Telegram donde los participantes asumen el rol de concejales de Cundinamarca. Debaten un proyecto de acuerdo real (el SIADR — Sistema de IA para Desarrollo Rural) con ayuda de personajes de IA que responden según diferentes perspectivas.

Cada concejal:
- Se registra eligiendo municipio y bancada
- Consulta a 5 personajes de IA (campesino, científico, contralor, empresa, alcalde)
- Propone enmiendas, negocia con otras bancadas
- Vota el proyecto al final

Tú como dinamizador controlas las fases, lanzas eventos sorpresa y monitoreas la actividad desde el bot y el geodashboard.

---

## Antes del evento

### 1. Verificar que el sistema está corriendo

Conéctate al servidor y verifica:

```bash
servidor
cd ~/TavoDebate/concejo-futuro
docker compose ps          # Los 10 contenedores deben estar "Up"
docker compose logs --tail=5 orchestrator  # Debe decir "Uvicorn running"
```

### 2. Abrir el bot en Telegram

Busca **@TavoDebate_bot** (o el nombre que tenga tu bot) en Telegram y envía `/start`. Deberías ver el Panel de Dinamizador con todos los comandos.

### 3. Verificar el geodashboard

Abre en el navegador: `http://192.168.0.221:8085/pantalla`

Este es el mapa interactivo que se proyecta en pantalla grande durante el ejercicio. Muestra:
- Los 30 municipios piloto del SIADR
- Actividad en tiempo real de los concejales
- Tweets simulados, alertas, votaciones

### 4. Prueba rápida personal

Desde tu Telegram como admin:

1. `/estado` → Debe mostrar el Panel de Dinamizador
2. Escribe: "Cuánto cuesta el proyecto SIADR?" → El bot debe responder con datos y enlaces de mapa
3. `/broadcast Esto es una prueba` → Envía mensaje a todos los registrados
4. `/fase registro` → Cambia la fase a registro

### 5. Limpiar datos de pruebas anteriores

Si hay datos viejos de pruebas:

```bash
servidor
cd ~/TavoDebate/concejo-futuro
docker exec concejo-futuro-postgres-1 psql -U concejo -d concejo_futuro -c "
  DELETE FROM votes;
  DELETE FROM proposals;
  DELETE FROM interactions;
  DELETE FROM users WHERE telegram_id NOT IN (5272332343);
"
```

(Esto borra todo excepto tu usuario admin)

---

## Día del evento

### Preparación (30 min antes)

1. Reiniciar contenedores frescos:
   ```bash
   servidor
   cd ~/TavoDebate/concejo-futuro
   docker compose restart
   ```

2. Verificar que todo arrancó:
   ```bash
   docker compose ps
   docker compose logs --tail=3 orchestrator | grep "Uvicorn running"
   ```

3. Abrir geodashboard en la pantalla del proyector: `http://192.168.0.221:8085/pantalla`

4. Enviar `/estado` en Telegram para confirmar que responde

---

### Fase 1: Registro (15-20 min)

**Objetivo:** Que todos los participantes se registren en el bot.

**Qué hacer:**

1. Proyectar el QR o link del bot en pantalla
2. Explicar brevemente:
   > "Van a ser concejales de Cundinamarca. Entren al bot, sigan los 4 pasos: nombre, provincia, municipio, bancada e intereses. La IA les va a dar un dossier personalizado según su bancada."

3. Cambiar la fase:
   ```
   /fase registro
   ```

4. Monitorear registros:
   ```
   /estado
   ```
   Esto muestra cuántos concejales hay registrados y por bancada.

**Tip:** Las 6 bancadas son:
| # | Bancada | Posición |
|---|---------|----------|
| 1 | Gobierno | A FAVOR |
| 2 | Oposición | EN CONTRA |
| 3 | Rural | CONDICIONAL |
| 4 | Urbana | PRAGMÁTICOS |
| 5 | Presupuesto | FISCALIZACIÓN |
| 6 | Veeduría | CONTROL SOCIAL |

Intenta que haya participantes en todas las bancadas. Si una queda vacía, puedes mencionarlo.

---

### Fase 2: Ponencia del Alcalde (10-15 min)

**Objetivo:** El "alcalde" (IA) presenta el proyecto SIADR.

1. Cambiar fase:
   ```
   /fase ponencia_alcalde
   ```

2. Lanzar un tweet simulado:
   ```
   /tweet El Alcalde de Cundinamarca presenta el proyecto SIADR ante el Gran Concejo del Futuro
   ```

3. Los concejales pueden escribir `/alcalde` para activar la voz del alcalde y hacerle preguntas.

4. Si quieres enviar un mensaje a todos:
   ```
   /broadcast El Alcalde ha terminado su exposición. Tienen 5 minutos para preguntas.
   ```

5. Poner timer:
   ```
   /ronda 10
   ```
   (Timer de 10 minutos visible en el geodashboard)

---

### Fase 3: Investigación (15-20 min)

**Objetivo:** Los concejales consultan a los 5 personajes de IA para preparar argumentos.

1. Cambiar fase:
   ```
   /fase investigacion
   ```

2. Explicar las voces disponibles:
   > "Tienen 5 asesores de IA. Cambien de voz con los comandos /ciudadano, /experto, /contralor, /empresa, /alcalde. Cada uno responde desde su perspectiva. Hagan preguntas para preparar sus argumentos."

3. Poner timer:
   ```
   /ronda 15
   ```

4. A mitad de la investigación, lanzar una bomba informativa:
   ```
   /bomba URGENTE: Se filtró un informe que revela que el 40% del presupuesto del SIADR iría a una sola empresa contratista vinculada al Gobernador.
   ```

5. Monitorear actividad con `/estado`

---

### Fase 4: Debate (20-30 min)

**Objetivo:** Los concejales debaten entre bancadas.

1. Cambiar fase:
   ```
   /fase debate
   ```

2. Explicar:
   > "Ahora pueden proponer enmiendas al proyecto con /proponer. Vean las propuestas de otros con /propuestas_todas. Apoyen propuestas con /apoyar N."

3. Poner timer:
   ```
   /ronda 20
   ```

4. Durante el debate, lanzar eventos para dinamizar:

   **Fake news (para que aprendan a verificar):**
   ```
   /fakenews Según fuentes anónimas, el sistema SIADR ya fue rechazado en 3 departamentos por problemas de privacidad
   ```

   **Presión política:**
   ```
   /presion El Gobernador amenaza con recortar transferencias a municipios que voten en contra del SIADR
   ```

   **Tweets de "ciudadanos":**
   ```
   /tweet Los campesinos de Chocontá dicen que prefieren inversión en vías antes que en tecnología
   /tweet Estudiantes de la UPTC apoyan el SIADR: "Es el futuro del campo colombiano"
   ```

5. Cada 5-10 min, revisar `/estado` para ver actividad

---

### Fase 5: Enmiendas (10-15 min)

1. Cambiar fase:
   ```
   /fase enmiendas
   ```

2. Explicar:
   > "Revisen las propuestas con /propuestas_todas. Pueden negociar con otras bancadas usando /negociar N (número de bancada). Tienen 10 minutos para consolidar enmiendas."

3. Timer:
   ```
   /ronda 10
   ```

---

### Fase 6: Votación (10 min)

**Objetivo:** Votar el proyecto final.

1. Cambiar fase:
   ```
   /fase votacion
   ```

2. Anunciar:
   ```
   /broadcast Ha llegado el momento de votar. Usen /votar_proyecto seguido de: a_favor, en_contra, o abstencion.
   ```

3. Timer:
   ```
   /ronda 5
   ```

4. Monitorear votos con `/estado`

5. Cuando termine el timer:
   ```
   /broadcast La votación ha cerrado. Resultados en pantalla.
   ```

---

### Fase 7: Debriefing (10-15 min)

1. Cambiar fase:
   ```
   /fase debriefing
   ```

2. Los participantes pueden descargar su certificado:
   ```
   /broadcast Felicidades! Pueden descargar su certificado de participación con /mi_certificado
   ```

3. Preguntas de reflexión para el grupo:
   - ¿Cómo influyeron las bombas informativas en su posición?
   - ¿Verificaron la fake news antes de cambiar de opinión?
   - ¿Las voces de IA les ayudaron a entender perspectivas diferentes?
   - ¿Qué aprendieron sobre el proceso legislativo real?

---

## Comandos rápidos de referencia

### Para el dinamizador (admin)

| Comando | Qué hace |
|---------|----------|
| `/start` | Panel de dinamizador |
| `/estado` | Stats del ejercicio (usuarios, interacciones, votos por bancada) |
| `/fase <nombre>` | Cambiar fase (registro, ponencia_alcalde, investigacion, debate, enmiendas, votacion, debriefing) |
| `/ronda <min>` | Timer de N minutos en pantalla |
| `/broadcast <msg>` | Mensaje a todos los concejales |
| `/bomba <msg>` | Bomba informativa (evento sorpresa) |
| `/fakenews <msg>` | Fake news (para ejercicio de verificación) |
| `/presion <msg>` | Presión política simulada |
| `/tweet <texto>` | Tweet simulado en pantalla |
| `/alerta <msg>` | Alerta visual en geodashboard |
| `/briefing` | Forzar briefing de inteligencia |
| `/llm deepseek` | Cambiar proveedor LLM |
| `/help` | Lista completa de comandos |

### Para los concejales

| Comando | Qué hace |
|---------|----------|
| `/start` | Registrarse (4 pasos) |
| `/help` | Ver comandos |
| `/estado` | Mi resumen personal |
| `/ciudadano` | Voz: Líder campesino |
| `/experto` | Voz: Científico de datos |
| `/contralor` | Voz: Control fiscal |
| `/empresa` | Voz: Empresa tech |
| `/alcalde` | Voz: Alcalde proponente |
| `/proponer <texto>` | Proponer enmienda |
| `/propuestas_todas` | Ver todas las propuestas |
| `/apoyar N` | Apoyar propuesta #N |
| `/negociar N` | Negociar con bancada N |
| `/votar_proyecto <voto>` | Votar (a_favor/en_contra/abstencion) |
| `/mi_certificado` | Descargar certificado PDF |
| Texto libre | Preguntar a la IA (responde según voz activa) |

---

## Solución de problemas

### El bot no responde
```bash
servidor
cd ~/TavoDebate/concejo-futuro
docker compose logs --tail=20 orchestrator   # Buscar errores
docker compose logs --tail=20 agent-chat     # Buscar errores
docker compose restart                       # Reiniciar todo
```

### Un concejal no puede registrarse
Decirle que envíe `/start` de nuevo. Si el problema persiste, resetear su usuario:
```bash
servidor
docker exec concejo-futuro-postgres-1 psql -U concejo -d concejo_futuro -c "
  DELETE FROM users WHERE telegram_id = <SU_ID>;
"
```

### Las respuestas tardan mucho (>20s)
El LLM (DeepSeek) puede estar saturado. Opciones:
- Cambiar a Kimi: `/llm kimi`
- Esperar — el sistema tiene cache, las preguntas repetidas son instantáneas

### El geodashboard no carga
Verificar que el contenedor pantalla está corriendo:
```bash
servidor
docker compose ps agent-pantalla
curl http://localhost:8085/pantalla
```

### Se llenó el disco del servidor
```bash
servidor
docker system prune -f    # Limpiar imágenes/contenedores viejos
```

---

## Cronograma sugerido (2 horas)

| Tiempo | Fase | Duración |
|--------|------|----------|
| 0:00 | Bienvenida + explicación | 10 min |
| 0:10 | Registro en el bot | 15 min |
| 0:25 | Ponencia del Alcalde | 15 min |
| 0:40 | Investigación (consultar IA) | 20 min |
| 1:00 | Debate + bombas | 25 min |
| 1:25 | Enmiendas + negociación | 15 min |
| 1:40 | Votación | 10 min |
| 1:50 | Debriefing + certificados | 10 min |

---

## Pruebas previas al evento

### Prueba 1: Registro completo
1. Pide a 2-3 personas que se registren en el bot
2. Verifica con `/estado` que aparecen
3. Que cada uno pruebe escribir una pregunta libre

### Prueba 2: Voces de IA
1. Un voluntario escribe `/experto` y luego pregunta sobre costos
2. Otro escribe `/ciudadano` y pregunta lo mismo
3. Verificar que las respuestas tienen perspectivas diferentes

### Prueba 3: Eventos del dinamizador
1. Envía `/broadcast Esto es una prueba`
2. Envía `/bomba Prueba de bomba informativa`
3. Verifica que los participantes de prueba recibieron ambos mensajes

### Prueba 4: Geodashboard
1. Abre `http://192.168.0.221:8085/pantalla` en pantalla
2. Envía `/tweet Prueba de tweet en pantalla`
3. Verifica que aparece en el dashboard

### Prueba 5: Votación
1. Cambia a fase votación: `/fase votacion`
2. Pide a voluntarios que voten: `/votar_proyecto a_favor`
3. Verifica con `/estado` que se registran los votos
