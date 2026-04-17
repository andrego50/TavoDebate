# Manual del Dinamizador — TavoDebate

## Qué es TavoDebate

TavoDebate es un simulador legislativo por Telegram donde los participantes asumen el rol de concejales de Cundinamarca. Debaten un proyecto de acuerdo real (el SIADR — Sistema de IA para Desarrollo Rural) con ayuda de personajes de IA que responden según diferentes perspectivas.

Cada participante:
- Se registra en 5 pasos con botones (nombre, grupo, rol, provincia, municipio, posición/causa)
- Elige su grupo institucional: **Concejal**, **Gobierno/Alcaldía**, **Sociedad civil**, **Empresa/Gremio** o **Control/Veeduría**
- Consulta a **5 asesores especializados** (jurídico ⚖️, comunicaciones 📢, económico 📊, político 🏛️, tecnológico 💻) vía `/asesores` — todos buscan en DuckDuckGo
- Propone enmiendas, negocia con otras bancadas
- **Solo los concejales votan** el proyecto al final

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

### 2. Activar el PIN de acceso

Desde Telegram, envía:
```
/pin 1234
```
(Usa cualquier código de 4 dígitos). Esto impide que personas ajenas se registren. Solo quienes conozcan el PIN podrán completar el registro.

- `/pin` → Ver PIN actual
- `/pin off` → Desactivar PIN (registro abierto)

### 3. Abrir el bot en Telegram

Busca **@TavoDebate_bot** (o el nombre que tenga tu bot) en Telegram y envía `/start`. Deberías ver el Panel de Dinamizador con todos los comandos.

### 4. Verificar el geodashboard

Abre en el navegador: `https://pantalla.fastanalytics.co/pantalla`

(Red local: `https://pantalla.fastanalytics.co/pantalla`)

Este es el mapa interactivo que se proyecta en pantalla grande durante el ejercicio. Muestra:
- Los 30 municipios piloto del SIADR
- Actividad en tiempo real de los concejales
- Tweets simulados, alertas, votaciones

### 5. Prueba rápida personal

Desde tu Telegram como admin:

1. `/estado` → Debe mostrar el Panel de Dinamizador
2. `/pin 9999` → Activar PIN de prueba
3. `/fase` → Deben aparecer botones para elegir la fase + resumen de participantes
4. `/broadcast Esto es una prueba` → Envía mensaje a todos los registrados
5. `/pin off` → Desactivar PIN de prueba

### 6. Limpiar datos de pruebas anteriores

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

3. Abrir geodashboard en la pantalla del proyector: `https://pantalla.fastanalytics.co/pantalla`

4. Enviar `/estado` en Telegram para confirmar que responde

---

### Fase 1: Registro (15-20 min)

**Objetivo:** Que todos los participantes se registren en el bot.

**Qué hacer:**

1. Activar el PIN: `/pin 1234` (el que quieras)
2. Proyectar el QR o link del bot en pantalla + decir el PIN en voz alta
3. Explicar brevemente:
   > "Entren al bot y sigan los pasos con botones: (1) nombre, (2) rol institucional — concejal, gobierno, sociedad civil, empresa o control, (3) provincia y municipio, (4) si eres concejal: posición inicial (a favor, en contra o indeciso); los demás roles obtienen bancada automática, (5) causa principal. La IA les entregará un dossier personalizado y 5 asesores especializados."

4. Cambiar la fase (escribe `/fase` y aparecen los botones, o directamente):
   ```
   /fase registro
   ```
   Al cambiar de fase, recibes automáticamente un **resumen de participantes** con total, por bancada, por provincia y últimos registros.

5. Monitorear registros:
   ```
   /estado
   ```
   Esto muestra cuántos concejales hay registrados y por bancada.

**Tip:** Los concejales eligen entre 3 posiciones iniciales (internamente mapeadas a bancadas 1/2/4):
| Botón | Bancada interna | Posición |
|-------|-----------------|----------|
| ✅ A FAVOR | 1 Gobierno | Defiende el proyecto |
| ❌ EN CONTRA | 2 Oposición | Se opone |
| 🤔 INDECISO | 4 Pragmáticos | Condicional |

Los **no-concejales** obtienen bancada automática por grupo: Gobierno→1, Sociedad civil→3, Empresa→4, Control→5. **No hay límite** por rol: pueden registrarse varios alcaldes, contralores, etc.

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

**Objetivo:** Votar el proyecto final. **Solo concejales pueden votar** (roles `alcalde`, `contralor`, `lider_*`, etc. reciben mensaje de que no votan).

1. Cambiar fase:
   ```
   /fase votacion
   ```
   Esto **automáticamente**:
   - Cierra cualquier votación anterior abierta
   - Abre una nueva `voting_session`
   - Inicia un **timer fresco de 5 minutos** (reinicia cada vez que entras a la fase)
   - Envía aviso a todos los concejales

2. Monitorear votos con `/estado` mientras el timer corre.

3. Al llegar a 0 segundos, el sistema **automáticamente**:
   - Cierra la sesión en DB
   - Cuenta `si` / `no` / `abstención` de los votos emitidos en esa ventana
   - Determina **APROBADO** (si > no) o **RECHAZADO**
   - Envía a todos los participantes el resultado final + **trazabilidad de todas las votaciones anteriores**
   - Publica el evento en pantalla

4. Puedes repetir `/fase votacion` para abrir una nueva ronda — el contador se reinicia y el resultado anterior queda en el historial.

5. Consultar el historial en cualquier momento:
   ```
   /historial_votaciones
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
| `/fase` | Muestra botones para elegir fase + resumen de participantes |
| `/fase <nombre>` | Cambiar fase directamente + resumen |
| `/pin 1234` | Activar PIN de acceso (4 dígitos) |
| `/pin off` | Desactivar PIN (registro abierto) |
| `/pin` | Ver PIN actual |
| `/ronda <min>` | Timer de N minutos en pantalla |
| `/broadcast <msg>` | Mensaje manual a todos los concejales |
| `/broadcast` (sin texto) | **Genera borrador contextual** con LLM → preview con botones ✅ Aprobar / 🔄 Regenerar / ❌ Cancelar |
| `/bomba <N>` | Bomba informativa #N |
| `/fakenews <N>` | Fake news #N |
| `/presion <msg>` | Presión política simulada |
| `/tweet <texto>` | Tweet simulado en pantalla |
| `/historial_votaciones` | Lista todas las votaciones con resultado |
| `/asignar_rol <nombre> <rol>` | Asignar rol institucional a un usuario ya registrado |
| `/roles` | Lista de roles disponibles |
| `/briefing` | Forzar briefing de inteligencia |
| `/llm switch <proveedor>` | Cambiar proveedor LLM (deepseek/kimi) |
| `/help` | Lista completa de comandos |

### Para los concejales

| Comando | Qué hace |
|---------|----------|
| `/start` | Registrarse (5 pasos, todo por botones salvo el nombre) |
| `/help` | Ver comandos |
| `/estado` | Mi resumen personal |
| `/asesores` | Panel de 5 asesores especializados (⚖️📢📊🏛️💻) — todos con DuckDuckGo |
| `/ciudadano` | Voz: Líder campesino |
| `/experto` | Voz: Científico de datos |
| `/contralor` | Voz: Control fiscal |
| `/empresa` | Voz: Empresa tech |
| `/alcalde` | Voz: Alcalde proponente |
| `/preparar_ponencia` | La IA arma tu ponencia según tu rol y causa |
| `/preparar_ponencia <ideas>` | Ponencia basada en tus ideas |
| `/proponer <texto>` | Proponer enmienda |
| `/propuestas_todas` | Ver todas las propuestas |
| `/apoyar N` | Apoyar propuesta #N |
| `/negociar N` | Negociar con bancada N |
| `/tuitear <texto>` | (solo concejales) Publicar tuit en pantalla — soporta citar/responder |
| `/votar_proyecto <voto>` | (solo `rol = concejal`) Votar a_favor / en_contra / abstencion |
| `/mi_certificado` | Descargar certificado PDF |
| Texto libre | Preguntar al asesor activo (responde según asesor + voz activa, puede buscar en web) |

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
1. Abre `https://pantalla.fastanalytics.co/pantalla` en pantalla
2. Envía `/tweet Prueba de tweet en pantalla`
3. Verifica que aparece en el dashboard

### Prueba 5: Votación
1. Cambia a fase votación: `/fase votacion`
2. Pide a voluntarios que voten: `/votar_proyecto a_favor`
3. Verifica con `/estado` que se registran los votos
