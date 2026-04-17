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
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"DB Error: {e}")


def send_command(command: str, args: dict = None):
    token = os.environ.get("ADMIN_API_TOKEN", "")
    if not token:
        st.error("ADMIN_API_TOKEN no configurado en el entorno del dashboard.")
        return
    try:
        httpx.post(
            f"{ORCHESTRATOR_URL}/admin/command",
            json={"command": command, "args": args or {}},
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
    except Exception as e:
        st.error(f"API Error: {e}")


# --- Tabs ---
tab_monitor, tab_control, tab_medios, tab_concejales, tab_crisis = st.tabs([
    "📊 Monitor", "🎮 Control", "📸 Medios", "👥 Concejales", "📰 Sala de Crisis"
])

# ===== TAB 1: MONITOR =====
with tab_monitor:
    st.title("📊 Monitor en Vivo — TavoDebate")

    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    users = query_db("SELECT COUNT(*) as n FROM users WHERE onboarding_complete = true")
    interactions = query_db("SELECT COUNT(*) as n FROM interactions")
    recent = query_db(
        "SELECT COUNT(*) as n FROM interactions WHERE created_at > NOW() - INTERVAL '1 minute'"
    )

    col1.metric("Concejales", users[0]["n"] if users else 0)
    col2.metric("Total consultas", interactions[0]["n"] if interactions else 0)
    col3.metric("Consultas/min", recent[0]["n"] if recent else 0)
    col4.metric("Fase", "En curso")

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
            import pandas as pd
            df = pd.DataFrame(bancada_data)
            st.bar_chart(df.set_index("bancada_nombre"))

    with c2:
        st.subheader("Consultas por voz")
        voice_data = query_db(
            "SELECT voice_used, COUNT(*) as n FROM interactions "
            "GROUP BY voice_used ORDER BY n DESC"
        )
        if voice_data:
            import pandas as pd
            df = pd.DataFrame(voice_data)
            st.bar_chart(df.set_index("voice_used"))

    st.divider()

    # Recent interactions (anonymized)
    st.subheader("Últimas consultas")
    recents = query_db(
        "SELECT bancada_nombre, municipio, voice_used, "
        "LEFT(question, 100) as pregunta, created_at "
        "FROM interactions ORDER BY created_at DESC LIMIT 10"
    )
    for r in recents:
        st.text(f"[{r['bancada_nombre']}] {r['municipio']} ({r['voice_used']}): {r['pregunta']}")

    # Proposals
    st.subheader("Top propuestas")
    proposals = query_db(
        "SELECT id, bancada_nombre, resumen, apoyos "
        "FROM proposals ORDER BY apoyos DESC LIMIT 5"
    )
    for p in proposals:
        st.text(f"#{p['id']} [{p['bancada_nombre']}] {p['resumen']} — {p['apoyos']} apoyos")


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

    # Bombs
    st.subheader("💥 Datos Bomba")
    bomb_cols = st.columns(4)
    for i in range(1, 9):
        col = bomb_cols[(i - 1) % 4]
        if col.button(f"Bomba #{i}", key=f"bomb_{i}"):
            send_command("bomba", {"bomb_id": i})
            st.success(f"Bomba #{i} enviada")

    st.divider()

    # Fake News
    st.subheader("📰 Fake News")
    fn_cols = st.columns(3)
    for i in range(1, 7):
        col = fn_cols[(i - 1) % 3]
        if col.button(f"FakeNews #{i}", key=f"fn_{i}"):
            send_command("fakenews", {"news_id": i})
            st.success(f"Fake news #{i} enviada")

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
    st.subheader("🗳️ Votación")
    if st.button("Abrir votación de proyecto"):
        execute_db(
            "INSERT INTO voting_sessions (type, description) "
            "VALUES ('proyecto', 'Votación del Proyecto SIADR')"
        )
        st.success("Sesión de votación abierta")

    if st.button("Cerrar votación activa"):
        execute_db("UPDATE voting_sessions SET is_open = false, closed_at = NOW() WHERE is_open = true")
        st.success("Votación cerrada")

    # Vote results
    votes = query_db(
        "SELECT vote, COUNT(*) as n FROM votes "
        "WHERE vote_type = 'proyecto' GROUP BY vote"
    )
    if votes:
        st.write("Resultados actuales:")
        for v in votes:
            st.metric(v["vote"], v["n"])

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
        query += f" AND provincia ILIKE '%{provincia_filter}%'"
    query += " ORDER BY last_active DESC"

    users_data = query_db(query)
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


# ===== TAB 5: SALA DE CRISIS =====
with tab_crisis:
    st.title("📰 Sala de Crisis — Fake News")

    # Timeline of broadcasts
    st.subheader("Timeline de noticias")
    broadcasts = query_db(
        "SELECT created_at, type, subtype, content, reach "
        "FROM broadcasts ORDER BY created_at DESC LIMIT 30"
    )
    for b in broadcasts:
        icon = "📰" if b["type"] == "fakenews" else "📢"
        st.text(f"{icon} [{b['created_at']}] {b['type']}: {b['content'][:100]}")

    st.divider()

    # Fake news impact
    st.subheader("Impacto de fake news")
    impact = query_db(
        "SELECT fakenews_id, COUNT(*) as menciones, "
        "COUNT(DISTINCT user_id) as concejales "
        "FROM fakenews_impact GROUP BY fakenews_id ORDER BY menciones DESC"
    )
    if impact:
        for i in impact:
            st.metric(f"Fake News #{i['fakenews_id']}", f"{i['menciones']} menciones, {i['concejales']} concejales")

    # Reveal button
    st.divider()
    if st.button("🎭 REVELAR TODAS LAS FAKE NEWS", type="primary"):
        from core.fakenews import FAKE_NEWS
        for news_id, news in FAKE_NEWS.items():
            send_command("broadcast", {"message": news["reveal_text"]})
        st.success("Todas las fake news reveladas")


# Auto-refresh
time.sleep(5)
st.rerun()
