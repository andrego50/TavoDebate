"""TavoDebate - Dashboard Streamlit (5 pestañas para el facilitador)."""

import json
import os
import time
from datetime import datetime

import httpx
import streamlit as st

st.set_page_config(
    page_title="TavoDebate — Concejo del Futuro",
    layout="wide",
    page_icon="🏛️",
)

# --- Config ---
ORCHESTRATOR_URL = "http://orchestrator:8000"
DB_URL = "postgresql://concejo:concejo2026@postgres:5432/concejo_futuro"

# --- DB Connection ---
import psycopg2

@st.cache_resource
def get_db():
    return psycopg2.connect(DB_URL)


def query_db(sql, params=None):
    conn = get_db()
    # Reconectar si la conexión cacheada murió (ej. reinicio de Postgres)
    if conn.closed:
        st.cache_resource.clear()
        conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [desc[0] for desc in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    except Exception as e:
        conn.rollback()
        st.error(f"DB Error: {e}")
        return []


def execute_db(sql, params=None):
    conn = get_db()
    if conn.closed:
        st.cache_resource.clear()
        conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"DB Error: {e}")


def send_command(command: str, args: dict = None) -> bool:
    token = os.environ.get("ADMIN_API_TOKEN", "")
    if not token:
        st.error("ADMIN_API_TOKEN no configurado en el entorno del dashboard.")
        return False
    try:
        resp = httpx.post(
            f"{ORCHESTRATOR_URL}/admin/command",
            json={"command": command, "args": args or {}},
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        data = resp.json()
        if not data.get("ok"):
            st.error(f"El orquestador rechazó el comando: {data}")
            return False
        return True
    except Exception as e:
        st.error(f"API Error: {e}")
        return False


# --- Tabs ---
tab_monitor, tab_control, tab_medios, tab_concejales = st.tabs([
    "📊 Monitor", "🎮 Control", "📸 Medios", "👥 Concejales"
])

# ===== TAB 1: MONITOR =====
with tab_monitor:
    st.title("📊 Monitor en Vivo — TavoDebate")

    @st.fragment(run_every=5)
    def monitor_live():
        import pandas as pd

        # KPIs — 4 columnas en una sola fila
        col1, col2, col3, col4 = st.columns(4)

        users_row = query_db("SELECT COUNT(*) as n FROM users WHERE onboarding_complete = true")
        interactions_row = query_db("SELECT COUNT(*) as n FROM interactions")
        recent_row = query_db(
            "SELECT COUNT(*) as n FROM interactions "
            "WHERE created_at > NOW() - INTERVAL '1 minute'"
        )
        phase_row = query_db(
            "SELECT current_phase FROM debate_state WHERE id = 1"
        )

        col1.metric("Concejales", users_row[0]["n"] if users_row else 0)
        col2.metric("Total consultas", interactions_row[0]["n"] if interactions_row else 0)
        col3.metric("Consultas/min", recent_row[0]["n"] if recent_row else 0)
        col4.metric("Fase", (phase_row[0]["current_phase"] if phase_row else "—") or "—")

        st.divider()

        # Charts
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Consultas por bancada")
            bancada_data = query_db(
                "SELECT bancada_nombre, COUNT(*) as n FROM interactions "
                "WHERE bancada_id IS NOT NULL GROUP BY bancada_nombre ORDER BY n DESC"
            )
            if bancada_data:
                df = pd.DataFrame(bancada_data)
                st.bar_chart(df.set_index("bancada_nombre"), use_container_width=True)

        with c2:
            st.subheader("Consultas por voz")
            voice_data = query_db(
                "SELECT voice_used, COUNT(*) as n FROM interactions "
                "GROUP BY voice_used ORDER BY n DESC"
            )
            if voice_data:
                df = pd.DataFrame(voice_data)
                st.bar_chart(df.set_index("voice_used"), use_container_width=True)

        st.divider()

        # Recent interactions
        st.subheader("Últimas consultas")
        recents = query_db(
            "SELECT bancada_nombre, municipio, voice_used, "
            "LEFT(question, 100) as pregunta, created_at "
            "FROM interactions ORDER BY created_at DESC LIMIT 10"
        )
        for r in recents:
            st.text(
                f"[{r['bancada_nombre']}] {r['municipio']} "
                f"({r['voice_used']}): {r['pregunta']}"
            )

        # Proposals
        st.subheader("Top propuestas")
        proposals = query_db(
            "SELECT id, bancada_nombre, resumen, apoyos "
            "FROM proposals ORDER BY apoyos DESC LIMIT 5"
        )
        for p in proposals:
            st.text(
                f"#{p['id']} [{p['bancada_nombre']}] "
                f"{p['resumen']} — {p['apoyos']} apoyos"
            )

    monitor_live()


# ===== TAB 2: CONTROL =====
with tab_control:
    st.title("🎮 Control del Facilitador")

    # Broadcast
    st.subheader("📢 Broadcasts")
    broadcast_msg = st.text_area("Mensaje para todos", key="broadcast_msg")
    broadcast_audio = st.checkbox("Con audio TTS")
    if st.button("📢 Enviar a todos"):
        send_command("broadcast", {"message": broadcast_msg, "with_audio": broadcast_audio})
        st.success("Broadcast enviado")

    st.divider()

    # Phase control
    st.subheader("🕐 Control de fases")
    phases = [
        "registro", "ponencia_alcalde", "preguntas_alcalde",
        "investigacion", "debate", "enmiendas", "votacion", "debriefing",
    ]
    phase = st.selectbox("Fase", phases)
    if st.button("Cambiar fase"):
        send_command("fase", {"phase": phase})
        st.success(f"Fase: {phase}")

    # Timer
    timer_min = st.number_input("Minutos para timer", value=5, min_value=1, max_value=60)
    if st.button("Iniciar timer"):
        send_command("ronda", {"minutes": timer_min})
        st.success(f"Timer de {timer_min} min")

    st.divider()

    # Voting
    st.subheader("🗳️ Votación del Proyecto")

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("🗳️ Abrir votación", use_container_width=True):
            # Cerrar sesiones previas abiertas
            execute_db(
                "UPDATE voting_sessions SET is_open = false, closed_at = NOW() "
                "WHERE is_open = true"
            )
            # Abrir nueva sesión
            execute_db(
                "INSERT INTO voting_sessions (type, description, is_open) "
                "VALUES ('proyecto', 'Votación del Proyecto de Acuerdo SIADR', true)"
            )
            # Iniciar timer de 5 min en el simulation agent
            send_command("ronda", {"minutes": 5, "name": "Votación proyecto"})
            st.success("Votación abierta — timer de 5 min iniciado")
            st.info(
                "Para enviar la papeleta a cada concejal, "
                "usa /fase votacion desde el bot de Telegram."
            )

    with btn_col2:
        if st.button("⏹️ Cerrar votación", use_container_width=True):
            execute_db(
                "UPDATE voting_sessions SET is_open = false, closed_at = NOW() "
                "WHERE is_open = true"
            )
            st.success("Votación cerrada")

    # Resultados — siempre 3 columnas, filtrados por sesión activa
    @st.fragment(run_every=3)
    def voting_results():
        active = query_db(
            "SELECT id, opened_at FROM voting_sessions "
            "WHERE is_open = true AND type = 'proyecto' LIMIT 1"
        )
        if not active:
            st.info("No hay votación activa en este momento.")
            return

        sid = active[0]["id"]
        opened_at = active[0]["opened_at"]

        votes = query_db(
            "SELECT vote, COUNT(*) as n FROM votes "
            "WHERE vote_type = 'proyecto' AND created_at >= %s "
            "GROUP BY vote",
            (opened_at,),
        )
        total_row = query_db(
            "SELECT COUNT(*) as n FROM users "
            "WHERE onboarding_complete = true AND bancada_nombre != 'Dinamizador'"
        )
        total = total_row[0]["n"] if total_row else 0
        vote_map = {v["vote"]: v["n"] for v in votes} if votes else {}
        voted = sum(vote_map.values())

        st.caption(
            f"Sesión abierta a las {opened_at.strftime('%H:%M')} — "
            f"{voted} de {total} han votado"
        )

        # Una sola fila, 3 columnas siempre
        vc1, vc2, vc3 = st.columns(3)
        vc1.metric("✅ A favor", vote_map.get("si", 0))
        vc2.metric("❌ En contra", vote_map.get("no", 0))
        vc3.metric("⚪ Abstención", vote_map.get("abstencion", 0))

    voting_results()

    st.divider()

    # Admin log
    st.subheader("📋 Log de acciones")
    actions = query_db(
        "SELECT created_at, action_type, parameters FROM admin_actions "
        "ORDER BY created_at DESC LIMIT 20"
    )
    for a in actions:
        st.text(f"{a['created_at']} | {a['action_type']} | {a['parameters']}")


# ===== TAB 3: MEDIOS =====
with tab_medios:
    st.title("📸 Medios")
    st.info("Upload y envío de medios (fotos, videos, docs)")

    uploaded = st.file_uploader("Subir archivo", type=["jpg", "png", "mp4", "pdf", "docx"])
    if uploaded:
        save_path = f"/app/media/{uploaded.name}"
        with open(save_path, "wb") as f:
            f.write(uploaded.getbuffer())
        st.success(f"Archivo guardado: {save_path}")


# ===== TAB 4: CONCEJALES =====
with tab_concejales:
    st.title("👥 Concejales")

    # Filters
    filter_col1, filter_col2 = st.columns(2)
    bancada_filter = filter_col1.selectbox(
        "Filtrar por bancada", ["Todas", "1", "2", "3", "4", "5", "6"]
    )
    provincia_filter = filter_col2.text_input("Filtrar por provincia", "")

    query = "SELECT * FROM users WHERE onboarding_complete = true"
    params = []
    if bancada_filter != "Todas":
        query += f" AND bancada_id = {int(bancada_filter)}"
    if provincia_filter:
        query += " AND provincia ILIKE %s"
        params.append(f"%{provincia_filter}%")
    query += " ORDER BY last_active DESC"

    users_data = query_db(query, params if params else None)
    if users_data:
        import pandas as pd
        df = pd.DataFrame(users_data)
        display_cols = [
            "nombre_completo", "municipio", "provincia", "bancada_nombre",
            "total_queries", "active_voice", "last_active",
        ]
        available_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available_cols], use_container_width=True)

    # Inactive users
    st.subheader("Concejales inactivos (>15 min)")
    inactive = query_db(
        "SELECT nombre_completo, municipio, bancada_nombre, last_active "
        "FROM users WHERE onboarding_complete = true "
        "AND last_active < NOW() - INTERVAL '15 minutes' "
        "ORDER BY last_active ASC LIMIT 20"
    )
    for u in inactive:
        st.text(f"{u['nombre_completo']} ({u['municipio']}) — {u['bancada_nombre']} — {u['last_active']}")


# Auto-refresh eliminado: los fragmentos del monitor y votación
# se actualizan solos (run_every=5s / 3s) sin recargar toda la app.
# Esto evita que el rerun global borre el texto del facilitador.
