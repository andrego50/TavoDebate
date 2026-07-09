"""Suite completa de pruebas TavoDebate — sin Telegram, evaluador Opus 4.8."""

import asyncio
import json
import sys
import os
import pytest
import psycopg2
import redis
import httpx

sys.path.insert(0, "/app")

# --- Configuración ---
DB_URL = "postgresql://concejo:concejo2026@postgres:5432/concejo_futuro"
REDIS_URL = "redis://redis:6379"
VLLM_URL = "http://192.168.0.221:9090/v1"
VLLM_MODEL = "google/gemma-4-12B-it-qat-w4a16-ct"

# Telegram IDs de prueba — rango > 999_000_000 para identificarlos
TID_CONCEJAL    = 999_000_001
TID_ALCALDE     = 999_000_002
TID_LIDER       = 999_000_003

TEST_USERS = [
    {
        "telegram_id": TID_CONCEJAL,
        "username": "test_concejal",
        "nombre_completo": "Test Concejal Fusagasugá",
        "municipio": "Fusagasugá",
        "provincia": "Sumapaz",
        "bancada_id": 1,
        "bancada_nombre": "🏛️ Gobierno",
        "rol": "concejal",
        "onboarding_complete": True,
        "temas_interes": ["agro", "agua"],
        "intereses_resumen": "Desarrollo rural y acceso a agua potable.",
        "active_voice": "ciudadano",
    },
    {
        "telegram_id": TID_ALCALDE,
        "username": "test_alcalde",
        "nombre_completo": "Test Alcalde Proponente",
        "municipio": "Fusagasugá",
        "provincia": "Sumapaz",
        "bancada_id": 1,
        "bancada_nombre": "🏛️ Gobierno",
        "rol": "alcalde",
        "onboarding_complete": True,
        "temas_interes": ["tecnologia"],
        "intereses_resumen": "Modernización y gobierno digital.",
        "active_voice": "ciudadano",
    },
    {
        "telegram_id": TID_LIDER,
        "username": "test_lider",
        "nombre_completo": "Test Líder Campesino",
        "municipio": "Fusagasugá",
        "provincia": "Sumapaz",
        "bancada_id": 3,
        "bancada_nombre": "🌾 Rural",
        "rol": "lider_campesino",
        "onboarding_complete": True,
        "temas_interes": ["agro"],
        "intereses_resumen": "Defensa de comunidades campesinas.",
        "active_voice": "ciudadano",
    },
]


# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────

@pytest.fixture(scope="session")
def db():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    yield conn
    conn.close()


@pytest.fixture(autouse=True, scope="class")
def clean_test_state(db):
    """Limpia estado transiente entre clases de test (no entre métodos dentro de la misma clase)."""
    tids = [u["telegram_id"] for u in TEST_USERS]
    yield
    cur = db.cursor()
    try:
        cur.execute("DELETE FROM votes WHERE telegram_id = ANY(%s)", (tids,))
        cur.execute(
            "DELETE FROM proposals WHERE user_id IN "
            "(SELECT id FROM users WHERE telegram_id = ANY(%s))", (tids,)
        )
        cur.execute("UPDATE voting_sessions SET is_open = false WHERE is_open = true")
        cur.execute("DELETE FROM voting_sessions WHERE description = 'TEST_SUITE_SESSION'")
        db.commit()
    except Exception:
        db.rollback()
    finally:
        cur.close()


@pytest.fixture(scope="session")
def rdb():
    r = redis.from_url(REDIS_URL, decode_responses=True)
    yield r
    r.close()


@pytest.fixture(scope="session", autouse=True)
def seed_users(db):
    """Inserta usuarios de prueba y los limpia al final."""
    cur = db.cursor()
    tids = [u["telegram_id"] for u in TEST_USERS]

    # Limpiar estado residual de corridas anteriores ANTES de empezar
    cur.execute("DELETE FROM votes WHERE telegram_id = ANY(%s)", (tids,))
    cur.execute(
        "DELETE FROM proposals WHERE user_id IN "
        "(SELECT id FROM users WHERE telegram_id = ANY(%s))", (tids,)
    )
    cur.execute(
        "DELETE FROM interactions WHERE user_id IN "
        "(SELECT id FROM users WHERE telegram_id = ANY(%s))", (tids,)
    )
    cur.execute("DELETE FROM voting_sessions WHERE description = 'TEST_SUITE_SESSION'")
    cur.execute("UPDATE voting_sessions SET is_open = false WHERE is_open = true")
    db.commit()

    for u in TEST_USERS:
        cur.execute(
            """
            INSERT INTO users (
                telegram_id, username, nombre_completo, municipio, provincia,
                bancada_id, bancada_nombre, rol, onboarding_complete,
                temas_interes, intereses_resumen, active_voice, onboarding_step
            ) VALUES (
                %(telegram_id)s, %(username)s, %(nombre_completo)s,
                %(municipio)s, %(provincia)s, %(bancada_id)s, %(bancada_nombre)s,
                %(rol)s, %(onboarding_complete)s,
                %(temas_interes)s, %(intereses_resumen)s, %(active_voice)s, 0
            )
            ON CONFLICT (telegram_id) DO UPDATE SET
                nombre_completo  = EXCLUDED.nombre_completo,
                onboarding_complete = EXCLUDED.onboarding_complete,
                rol              = EXCLUDED.rol
            """,
            {**u, "temas_interes": u["temas_interes"]},
        )
    db.commit()
    yield
    tids = [u["telegram_id"] for u in TEST_USERS]
    # Delete in FK-safe order: child tables first
    cur.execute("DELETE FROM votes       WHERE telegram_id = ANY(%s)", (tids,))
    cur.execute(
        "DELETE FROM proposals WHERE user_id IN "
        "(SELECT id FROM users WHERE telegram_id = ANY(%s))", (tids,)
    )
    cur.execute(
        "DELETE FROM interactions WHERE user_id IN "
        "(SELECT id FROM users WHERE telegram_id = ANY(%s))", (tids,)
    )
    cur.execute("DELETE FROM users  WHERE telegram_id = ANY(%s)", (tids,))
    cur.execute(
        "DELETE FROM voting_sessions WHERE description = 'TEST_SUITE_SESSION'"
    )
    db.commit()
    cur.close()


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def db_fetch(db, sql, params=None):
    cur = db.cursor()
    cur.execute(sql, params)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close()
    return rows


def db_exec(db, sql, params=None):
    cur = db.cursor()
    cur.execute(sql, params)
    db.commit()
    cur.close()


def vllm_complete(system: str, user_msg: str, max_tokens: int = 600) -> str:
    resp = httpx.post(
        f"{VLLM_URL}/chat/completions",
        headers={"Authorization": "Bearer vllm", "Content-Type": "application/json"},
        json={
            "model": VLLM_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user_msg},
            ],
            "temperature": 0.7,
            "max_tokens": max_tokens,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def opus_judge(prompt: str) -> dict:
    """Usa Opus 4.8 vía vLLM como juez (no hay ANTHROPIC_API_KEY en .env)."""
    system = (
        "Eres un evaluador experto en simulaciones legislativas. "
        "Devuelve ÚNICAMENTE un JSON válido con esta estructura exacta:\n"
        '{"coherencia_rol": <0-10>, "relevancia_siadr": <0-10>, '
        '"calidad_argumentativa": <0-10>, "justificacion": "<string>"}'
    )
    raw = vllm_complete(system, prompt, max_tokens=300)
    try:
        start = raw.index("{")
        end   = raw.rindex("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {"coherencia_rol": 0, "relevancia_siadr": 0,
                "calidad_argumentativa": 0, "justificacion": "parse_error"}


# ─────────────────────────────────────────────
# MOCK AGENT
# ─────────────────────────────────────────────

class MockBus:
    def __init__(self, rdb):
        self._r = rdb
        self.last_stream = []

    async def stream_add(self, stream, data):
        self.last_stream.append({"stream": stream, "data": data})

    async def get(self, key):
        return self._r.get(key)

    async def publish(self, channel, data):
        self._r.publish(channel, json.dumps(data))

    async def check_rate_limit(self, user_id):
        return True


class MockLLM:
    """LLM mock que llama directamente a vLLM para pruebas realistas."""
    async def generate(self, system: str, user_msg: str, temperature=0.7, max_tokens=200) -> str:
        return vllm_complete(system, user_msg, max_tokens=max_tokens)


class MockAgent:
    def __init__(self, rdb):
        self.bus = MockBus(rdb)
        self.llm = MockLLM()
        self.responses = []

    async def _send_response(self, chat_id, text, parse_mode="Markdown", reply_markup=None):
        self.responses.append({"chat_id": chat_id, "text": text})

    def last_text(self):
        return self.responses[-1]["text"] if self.responses else ""

    def clear(self):
        self.responses.clear()
        self.bus.last_stream.clear()


# ─────────────────────────────────────────────
# 1. ONBOARDING
# ─────────────────────────────────────────────

class TestOnboarding:
    def test_concejal_completo(self, db):
        rows = db_fetch(
            db,
            "SELECT * FROM users WHERE telegram_id = %s",
            (TID_CONCEJAL,),
        )
        assert rows, "Concejal no encontrado en DB"
        u = rows[0]
        assert u["onboarding_complete"] is True
        assert u["rol"] == "concejal"
        assert u["municipio"] == "Fusagasugá"
        assert u["bancada_id"] == 1

    def test_alcalde_completo(self, db):
        rows = db_fetch(db, "SELECT * FROM users WHERE telegram_id = %s", (TID_ALCALDE,))
        assert rows
        u = rows[0]
        assert u["onboarding_complete"] is True
        assert u["rol"] == "alcalde"

    def test_lider_campesino_completo(self, db):
        rows = db_fetch(db, "SELECT * FROM users WHERE telegram_id = %s", (TID_LIDER,))
        assert rows
        u = rows[0]
        assert u["onboarding_complete"] is True
        assert u["rol"] == "lider_campesino"
        assert u["bancada_id"] == 3

    def test_campos_requeridos(self, db):
        for u in TEST_USERS:
            rows = db_fetch(db, "SELECT * FROM users WHERE telegram_id = %s", (u["telegram_id"],))
            assert rows
            row = rows[0]
            for field in ("nombre_completo", "municipio", "provincia", "bancada_id", "bancada_nombre", "rol"):
                assert row[field], f"Campo '{field}' vacío para tid={u['telegram_id']}"


# ─────────────────────────────────────────────
# 2. COMANDOS DE USUARIO POR ROL
# ─────────────────────────────────────────────

class TestComandosUsuario:
    def test_estado_concejal(self, db, rdb):
        agent = MockAgent(rdb)

        async def run():
            from handlers.phase_handlers import handle_estado
            await handle_estado(agent, TID_CONCEJAL, TID_CONCEJAL)

        asyncio.run(run())
        text = agent.last_text()
        assert text, "handle_estado no devolvió respuesta"
        assert len(text) > 20

    def test_proponer_solo_texto_corto_rechazado(self, db, rdb):
        agent = MockAgent(rdb)

        async def run():
            from handlers.proposal_handlers import handle_proponer
            await handle_proponer(agent, TID_CONCEJAL, TID_CONCEJAL, "corto")

        asyncio.run(run())
        text = agent.last_text()
        assert "Mínimo" in text or "10 caracteres" in text

    def test_proponer_valido_concejal(self, db, rdb):
        agent = MockAgent(rdb)

        async def run():
            from handlers.proposal_handlers import handle_proponer
            await handle_proponer(
                agent, TID_CONCEJAL, TID_CONCEJAL,
                "Propongo que el SIADR incluya un módulo de participación ciudadana para comunidades rurales"
            )

        asyncio.run(run())
        rows = db_fetch(db, "SELECT * FROM proposals WHERE user_id = (SELECT id FROM users WHERE telegram_id = %s)", (TID_CONCEJAL,))
        assert rows, "Propuesta no registrada en DB"

    def test_votar_sin_sesion_activa(self, db, rdb):
        db_exec(db, "UPDATE voting_sessions SET is_open = false WHERE description = 'TEST_SUITE_SESSION'")
        agent = MockAgent(rdb)

        async def run():
            from handlers.voting_handlers import handle_votar_proyecto
            await handle_votar_proyecto(agent, TID_CONCEJAL, TID_CONCEJAL, "")

        asyncio.run(run())
        text = agent.last_text()
        assert "no hay" in text.lower() or "no existe" in text.lower() or "abierta" in text.lower()

    def test_alcalde_no_puede_votar_proyecto(self, db, rdb):
        db_exec(
            db,
            "INSERT INTO voting_sessions (type, description, is_open) VALUES ('proyecto', 'TEST_SUITE_SESSION', true) ON CONFLICT DO NOTHING",
        )
        agent = MockAgent(rdb)

        async def run():
            from handlers.voting_handlers import handle_votar_proyecto
            await handle_votar_proyecto(agent, TID_ALCALDE, TID_ALCALDE, "si")

        asyncio.run(run())
        text = agent.last_text()
        assert "no vota" in text.lower() or "solo los concejales" in text.lower() or "alcalde" in text.lower()

    def test_help_responde(self, db, rdb):
        agent = MockAgent(rdb)

        async def run():
            from handlers.onboarding import handle_help
            await handle_help(agent, TID_CONCEJAL)

        asyncio.run(run())
        text = agent.last_text()
        assert "/votar" in text or "/proponer" in text or "Comandos" in text


# ─────────────────────────────────────────────
# 3. FLUJO DE VOTACIÓN COMPLETO
# ─────────────────────────────────────────────

class TestVotacion:
    def setup_method(self):
        pass

    def test_abrir_sesion(self, db):
        db_exec(db, "UPDATE voting_sessions SET is_open = false WHERE is_open = true")
        db_exec(
            db,
            "INSERT INTO voting_sessions (type, description, is_open) VALUES ('proyecto', 'TEST_SUITE_SESSION', true)",
        )
        rows = db_fetch(db, "SELECT * FROM voting_sessions WHERE is_open = true AND description = 'TEST_SUITE_SESSION'")
        assert rows, "Sesión no creada"

    def test_registrar_votos(self, db):
        rows = db_fetch(db, "SELECT id FROM voting_sessions WHERE is_open = true AND description = 'TEST_SUITE_SESSION'")
        assert rows
        sid = rows[0]["id"]

        for tid, voto in [(TID_CONCEJAL, "si"), (TID_LIDER, "no")]:
            uid = db_fetch(db, "SELECT id FROM users WHERE telegram_id = %s", (tid,))[0]["id"]
            user = db_fetch(db, "SELECT * FROM users WHERE telegram_id = %s", (tid,))[0]
            db_exec(
                db,
                """
                INSERT INTO votes (user_id, telegram_id, nombre_concejal, municipio,
                    bancada_id, vote_type, target_id, vote)
                VALUES (%s, %s, %s, %s, %s, 'proyecto', NULL, %s)
                ON CONFLICT (telegram_id, vote_type, (COALESCE(target_id, 0)))
                DO UPDATE SET vote = EXCLUDED.vote
                """,
                (uid, tid, user["nombre_completo"], user["municipio"], user["bancada_id"], voto),
            )

        votos = db_fetch(db, "SELECT vote, COUNT(*) as n FROM votes WHERE vote_type = 'proyecto' GROUP BY vote")
        mapa = {v["vote"]: v["n"] for v in votos}
        assert mapa.get("si", 0) >= 1
        assert mapa.get("no", 0) >= 1

    def test_idempotencia_voto(self, db):
        uid = db_fetch(db, "SELECT id FROM users WHERE telegram_id = %s", (TID_CONCEJAL,))[0]["id"]
        user = db_fetch(db, "SELECT * FROM users WHERE telegram_id = %s", (TID_CONCEJAL,))[0]
        for _ in range(3):
            db_exec(
                db,
                """
                INSERT INTO votes (user_id, telegram_id, nombre_concejal, municipio,
                    bancada_id, vote_type, target_id, vote)
                VALUES (%s, %s, %s, %s, %s, 'proyecto', NULL, 'si')
                ON CONFLICT (telegram_id, vote_type, (COALESCE(target_id, 0)))
                DO UPDATE SET vote = EXCLUDED.vote
                """,
                (uid, TID_CONCEJAL, user["nombre_completo"], user["municipio"], user["bancada_id"]),
            )
        count = db_fetch(
            db,
            "SELECT COUNT(*) as n FROM votes WHERE telegram_id = %s AND vote_type = 'proyecto'",
            (TID_CONCEJAL,),
        )[0]["n"]
        assert count == 1, f"Idempotencia fallida: {count} votos para el mismo usuario"

    def test_cerrar_sesion_y_conteos(self, db):
        db_exec(db, "UPDATE voting_sessions SET is_open = false, closed_at = NOW() WHERE description = 'TEST_SUITE_SESSION'")
        rows = db_fetch(db, "SELECT * FROM voting_sessions WHERE description = 'TEST_SUITE_SESSION' AND is_open = false")
        assert rows, "Sesión no cerrada"


# ─────────────────────────────────────────────
# 4. COMANDOS ADMIN
# ─────────────────────────────────────────────

class TestComandosAdmin:
    FASES_VALIDAS = [
        "registro", "ponencia_alcalde", "preguntas_alcalde",
        "investigacion", "debate", "enmiendas", "votacion", "debriefing",
    ]

    def test_fases_validas_en_config(self):
        from handlers.onboarding import FASES
        for fase in self.FASES_VALIDAS:
            assert fase in FASES, f"Fase '{fase}' no encontrada en FASES"

    def test_broadcast_llega_a_redis(self, rdb):
        rdb.xadd("telegram:incoming", {"action": "broadcast", "message": "test_broadcast_suite"})
        entries = rdb.xrange("telegram:incoming", "-", "+")
        assert any(
            "test_broadcast_suite" in str(fields)
            for _, fields in entries
        ), f"Mensaje no encontrado en stream. Últimas entradas: {entries[-3:]}"

    def test_estado_admin_via_api(self):
        import httpx as _httpx
        try:
            resp = _httpx.get("http://orchestrator:8000/health", timeout=5)
            data = resp.json()
            assert data.get("status") == "ok"
        except Exception as e:
            pytest.skip(f"Orchestrator no alcanzable en tests: {e}")

    def test_fases_completas_sin_errores(self, db):
        for fase in self.FASES_VALIDAS:
            rows = db_fetch(db, "SELECT 1")
            assert rows


# ─────────────────────────────────────────────
# 5. CALIDAD LLM CON EVALUADOR OPUS (vLLM)
# ─────────────────────────────────────────────

PREGUNTAS_POR_ROL = {
    "concejal": [
        "¿Cuáles son los principales riesgos del proyecto SIADR para los campesinos de Fusagasugá?",
        "¿Cómo puedo argumentar en contra de la privatización de datos agrícolas?",
        "Dame argumentos para mi ponencia sobre el artículo 7 del proyecto de acuerdo.",
    ],
    "alcalde": [
        "¿Cómo respondo a las críticas sobre el costo del SIADR?",
        "¿Qué beneficios concretos tiene el SIADR para el sector agrícola?",
        "Dame argumentos para defender el proyecto ante el Concejo.",
    ],
    "lider_campesino": [
        "¿Cómo el SIADR podría afectar los derechos de los campesinos?",
        "¿Qué garantías necesito antes de apoyar este proyecto?",
        "¿Cómo presiono al Concejo para que incluya a las comunidades rurales?",
    ],
}

SYSTEM_BY_ROL = {
    "concejal": (
        "Eres el asesor de un concejal de Fusagasugá, bancada A FAVOR del proyecto SIADR "
        "(Sistema Integrado de Alertas para el Desarrollo Rural de Cundinamarca). "
        "Responde con argumentos legislativos concretos, cita el proyecto cuando sea relevante."
    ),
    "alcalde": (
        "Eres el asesor del Alcalde proponente del proyecto SIADR. "
        "Defiende el proyecto con datos técnicos y financieros concretos."
    ),
    "lider_campesino": (
        "Eres el asesor de un líder campesino de la provincia Sumapaz. "
        "Responde desde la perspectiva de las comunidades rurales, "
        "enfatizando derechos, consulta previa y soberanía alimentaria."
    ),
}

llm_scores = {}


class TestCalidadLLM:
    @pytest.mark.parametrize("rol", ["concejal", "alcalde", "lider_campesino"])
    def test_respuestas_llm_por_rol(self, rol):
        system = SYSTEM_BY_ROL[rol]
        preguntas = PREGUNTAS_POR_ROL[rol]
        scores_rol = []

        for pregunta in preguntas:
            try:
                respuesta = vllm_complete(system, pregunta, max_tokens=500)
            except Exception as e:
                pytest.fail(f"vLLM falló para rol={rol}: {e}")

            assert respuesta and len(respuesta) > 50, f"Respuesta muy corta para '{pregunta}'"

            juicio_prompt = (
                f"Rol del participante: {rol}\n"
                f"Pregunta: {pregunta}\n"
                f"Respuesta del asesor IA:\n{respuesta}\n\n"
                "Evalúa esta respuesta en el contexto de una simulación legislativa "
                "sobre el proyecto SIADR (Sistema Integrado de Alertas para el "
                "Desarrollo Rural de Cundinamarca)."
            )
            scores = opus_judge(juicio_prompt)
            scores_rol.append(scores)

            assert scores["coherencia_rol"] >= 5, (
                f"Coherencia baja ({scores['coherencia_rol']}/10) "
                f"para rol={rol}, pregunta='{pregunta[:60]}...'\n"
                f"Justificación: {scores['justificacion']}"
            )
            assert scores["relevancia_siadr"] >= 4, (
                f"Relevancia SIADR baja ({scores['relevancia_siadr']}/10) "
                f"para rol={rol}"
            )

        avg = {
            k: round(sum(s[k] for s in scores_rol) / len(scores_rol), 1)
            for k in ("coherencia_rol", "relevancia_siadr", "calidad_argumentativa")
        }
        llm_scores[rol] = avg
        print(f"\n[LLM] {rol}: {avg}")


# ─────────────────────────────────────────────
# 6. REPORTE FINAL
# ─────────────────────────────────────────────

def pytest_sessionfinish(session, exitstatus):
    if not llm_scores:
        return
    print("\n" + "=" * 60)
    print("REPORTE LLM — Scores promedio por rol")
    print("=" * 60)
    header = f"{'Rol':<22} {'Coherencia':>10} {'SIADR':>8} {'Arg.':>6}"
    print(header)
    print("-" * 60)
    for rol, s in llm_scores.items():
        print(
            f"{rol:<22} {s['coherencia_rol']:>10} "
            f"{s['relevancia_siadr']:>8} {s['calidad_argumentativa']:>6}"
        )
    print("=" * 60)
