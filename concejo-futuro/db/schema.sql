-- =============================================
-- TAVODEBATE — CONCEJO DEL FUTURO — Schema completo
-- =============================================

-- Usuarios (concejales registrados)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(100),
    nombre_completo VARCHAR(200) NOT NULL,
    municipio VARCHAR(100) NOT NULL,
    provincia VARCHAR(50) NOT NULL,
    bancada_id INT NOT NULL CHECK (bancada_id BETWEEN 1 AND 6),
    bancada_nombre VARCHAR(50) NOT NULL,
    temas_interes TEXT[] DEFAULT '{}',
    intereses_raw TEXT,
    intereses_keywords TEXT[] DEFAULT '{}',
    intereses_resumen VARCHAR(200),
    active_voice VARCHAR(20) DEFAULT 'ciudadano',
    first_seen TIMESTAMP DEFAULT NOW(),
    last_active TIMESTAMP DEFAULT NOW(),
    total_queries INT DEFAULT 0,
    audio_mode BOOLEAN DEFAULT FALSE,
    posicion_inicial VARCHAR(20),
    posicion_actual VARCHAR(20),
    posicion_cambios INT DEFAULT 0,
    propuestas_count INT DEFAULT 0,
    voto_proyecto VARCHAR(20),
    votos_enmiendas JSONB DEFAULT '{}',
    is_admin BOOLEAN DEFAULT FALSE,
    onboarding_complete BOOLEAN DEFAULT FALSE,
    onboarding_step INT DEFAULT 0
);

-- Interacciones concejal ↔ bot
CREATE TABLE interactions (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    user_id INT REFERENCES users(id),
    telegram_id BIGINT,
    nombre_concejal VARCHAR(200),
    municipio VARCHAR(100),
    provincia VARCHAR(50),
    bancada_id INT,
    bancada_nombre VARCHAR(50),
    voice_used VARCHAR(20) NOT NULL DEFAULT 'ciudadano',
    question TEXT NOT NULL,
    response TEXT NOT NULL,
    tokens_used INT DEFAULT 0,
    response_time_ms INT,
    alert_generated BOOLEAN DEFAULT FALSE,
    alert_data JSONB,
    sentiment VARCHAR(20),
    topics JSONB,
    position_strength INT DEFAULT 3,
    key_argument TEXT,
    classified_at TIMESTAMP
);

-- Propuestas de enmienda
CREATE TABLE proposals (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    user_id INT REFERENCES users(id),
    telegram_id BIGINT,
    nombre_concejal VARCHAR(200),
    municipio VARCHAR(100),
    provincia VARCHAR(50),
    bancada_id INT,
    bancada_nombre VARCHAR(50),
    articulo_afectado VARCHAR(20),
    tipo VARCHAR(20) DEFAULT 'enmienda',
    texto_propuesta TEXT NOT NULL,
    resumen VARCHAR(200),
    apoyos INT DEFAULT 1,
    apoyada_por BIGINT[] DEFAULT '{}',
    estado VARCHAR(20) DEFAULT 'propuesta',
    resultado_votacion JSONB
);

-- Acciones del facilitador
CREATE TABLE admin_actions (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    action_type VARCHAR(30) NOT NULL,
    parameters JSONB,
    executed_by VARCHAR(100),
    recipients_count INT DEFAULT 0
);

-- Broadcasts enviados
CREATE TABLE broadcasts (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    type VARCHAR(20) NOT NULL,
    subtype VARCHAR(30),
    content TEXT,
    media_file VARCHAR(200),
    reach INT DEFAULT 0,
    metadata JSONB
);

-- Reportes de inteligencia
CREATE TABLE intelligence_reports (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    report_type VARCHAR(30),
    bancada_id INT,
    summary TEXT NOT NULL,
    details JSONB,
    suggestions JSONB,
    read_by_admin BOOLEAN DEFAULT FALSE
);

-- Votaciones
CREATE TABLE votes (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    user_id INT REFERENCES users(id),
    telegram_id BIGINT,
    nombre_concejal VARCHAR(200),
    municipio VARCHAR(100),
    bancada_id INT,
    vote_type VARCHAR(20) NOT NULL,
    target_id INT,
    vote VARCHAR(20) NOT NULL,
    changed_from VARCHAR(20)
);

-- Sesiones de votación
CREATE TABLE voting_sessions (
    id SERIAL PRIMARY KEY,
    opened_at TIMESTAMP DEFAULT NOW(),
    closed_at TIMESTAMP,
    type VARCHAR(20) NOT NULL,
    target_id INT,
    description TEXT,
    is_open BOOLEAN DEFAULT TRUE,
    results JSONB
);

-- Tracking de impacto de fake news
CREATE TABLE fakenews_impact (
    id SERIAL PRIMARY KEY,
    fakenews_id INT NOT NULL,
    sent_at TIMESTAMP NOT NULL,
    interaction_id INT REFERENCES interactions(id),
    user_id BIGINT,
    bancada_id INT,
    minutes_after INT,
    matched_keywords TEXT[]
);

-- Estado comprimido por bancada
CREATE TABLE bancada_state (
    bancada_id INT PRIMARY KEY,
    summary TEXT NOT NULL DEFAULT 'Sin actividad aún.',
    updated_at TIMESTAMP DEFAULT NOW(),
    topics_ranking JSONB DEFAULT '{}',
    position_distribution JSONB DEFAULT '{}',
    active_count INT DEFAULT 0,
    key_players JSONB DEFAULT '[]',
    proposals JSONB DEFAULT '[]'
);

-- Estado global del debate (1 sola fila)
CREATE TABLE debate_state (
    id INT PRIMARY KEY DEFAULT 1,
    global_summary TEXT NOT NULL DEFAULT 'El debate aún no ha comenzado.',
    temperature VARCHAR(20) DEFAULT 'frio',
    approval_probability INT DEFAULT 50,
    hottest_topic VARCHAR(50) DEFAULT 'ninguno',
    alliances JSONB DEFAULT '{}',
    current_phase VARCHAR(50) DEFAULT 'registro',
    phase_started_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Propuestas proactivas del bot
CREATE TABLE proactive_proposals (
    id SERIAL PRIMARY KEY,
    cycle_number INT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    tipo VARCHAR(20) NOT NULL,
    destino VARCHAR(20) NOT NULL,
    canal VARCHAR(20) NOT NULL,
    contenido TEXT NOT NULL,
    razon TEXT,
    urgencia VARCHAR(10),
    status VARCHAR(20) DEFAULT 'pending',
    modified_content TEXT,
    executed_at TIMESTAMP
);

-- Items de dossier por bancada
CREATE TABLE dossier_items (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    bancada_id INT NOT NULL,
    tipo VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(50) DEFAULT 'system',
    used_count INT DEFAULT 0
);

-- Ponencias orales
CREATE TABLE ponencias (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    bancada_id INT NOT NULL,
    audio_path VARCHAR(200),
    transcript TEXT NOT NULL,
    analysis JSONB NOT NULL,
    resumen VARCHAR(500),
    posicion VARCHAR(20),
    argumentos TEXT[],
    frase_clave VARCHAR(300),
    uso_fake_news BOOLEAN DEFAULT FALSE,
    social_reactions_generated INT DEFAULT 0
);

-- Negociaciones entre bancadas
CREATE TABLE negotiations (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    bancada_a INT NOT NULL,
    bancada_b INT NOT NULL,
    iniciador_id BIGINT,
    receptor_id BIGINT,
    mensajes JSONB DEFAULT '[]',
    status VARCHAR(20) DEFAULT 'pendiente',
    resultado TEXT,
    closed_at TIMESTAMP
);

-- Eventos de presión
CREATE TABLE pressure_events (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    tipo VARCHAR(20) NOT NULL,
    tema VARCHAR(50) NOT NULL,
    actor VARCHAR(200) NOT NULL,
    mensaje TEXT NOT NULL,
    gravedad VARCHAR(20) NOT NULL,
    concejales_alcanzados INT DEFAULT 0,
    bancadas_alcanzadas INT[] DEFAULT '{}',
    efecto_posiciones JSONB
);

-- Gabinete del alcalde
CREATE TABLE gabinete (
    id VARCHAR(30) PRIMARY KEY,
    tipo VARCHAR(20) NOT NULL,
    nombre VARCHAR(200) NOT NULL,
    titular VARCHAR(200) NOT NULL,
    presupuesto_millones INT DEFAULT 0,
    competencias TEXT[] DEFAULT '{}',
    rol_siadr TEXT,
    aliado_bancada INT,
    aliado_tema VARCHAR(50),
    vulnerabilidad TEXT,
    estado VARCHAR(20) DEFAULT 'activo',
    removido_at TIMESTAMP,
    reemplazado_por VARCHAR(200),
    historial JSONB DEFAULT '[]'
);

-- Eventos del gabinete
CREATE TABLE gabinete_events (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    gabinete_id VARCHAR(30) REFERENCES gabinete(id),
    tipo_evento VARCHAR(30) NOT NULL,
    detalle TEXT NOT NULL,
    afecta_bancada INT,
    afecta_tema VARCHAR(50),
    concejales_notificados INT DEFAULT 0
);

-- =============================================
-- DATOS INICIALES
-- =============================================

-- Estado global inicial
INSERT INTO debate_state (id, global_summary) VALUES (1, 'El debate aún no ha comenzado.');

-- Estados de bancada iniciales
INSERT INTO bancada_state (bancada_id) VALUES (1), (2), (3), (4), (5), (6);

-- =============================================
-- ÍNDICES
-- =============================================
CREATE INDEX idx_interactions_ts ON interactions(created_at DESC);
CREATE INDEX idx_interactions_bancada ON interactions(bancada_id);
CREATE INDEX idx_interactions_voice ON interactions(voice_used);
CREATE INDEX idx_interactions_user ON interactions(user_id);
CREATE INDEX idx_users_bancada ON users(bancada_id);
CREATE INDEX idx_users_municipio ON users(municipio);
CREATE INDEX idx_users_provincia ON users(provincia);
CREATE INDEX idx_users_telegram ON users(telegram_id);
CREATE INDEX idx_users_temas ON users USING GIN(temas_interes);
CREATE INDEX idx_proposals_bancada ON proposals(bancada_id);
CREATE INDEX idx_proposals_estado ON proposals(estado);
CREATE INDEX idx_votes_type ON votes(vote_type);
CREATE INDEX idx_votes_user ON votes(user_id);
CREATE INDEX idx_broadcasts_ts ON broadcasts(created_at DESC);
CREATE INDEX idx_intel_ts ON intelligence_reports(created_at DESC);

-- =============================================
-- VISTAS ÚTILES
-- =============================================

-- Resumen por bancada
CREATE VIEW bancada_summary AS
SELECT
    u.bancada_id,
    u.bancada_nombre,
    COUNT(DISTINCT u.telegram_id) as concejales,
    COUNT(DISTINCT i.id) as total_consultas,
    MODE() WITHIN GROUP (ORDER BY i.voice_used) as voz_favorita,
    MODE() WITHIN GROUP (ORDER BY i.sentiment) as posicion_dominante
FROM users u
LEFT JOIN interactions i ON u.id = i.user_id
GROUP BY u.bancada_id, u.bancada_nombre;

-- Concejales activos (últimos 5 min)
CREATE VIEW active_users AS
SELECT * FROM users
WHERE last_active > NOW() - INTERVAL '5 minutes'
ORDER BY last_active DESC;

-- Resultados de votación del proyecto
CREATE VIEW vote_results AS
SELECT
    vote,
    COUNT(*) as count,
    ROUND(COUNT(*)::numeric / NULLIF(SUM(COUNT(*)) OVER(), 0) * 100, 1) as percentage
FROM votes
WHERE vote_type = 'proyecto'
GROUP BY vote;

-- Distribución de temas por bancada
CREATE VIEW tema_distribution AS
SELECT
    unnest(temas_interes) as tema,
    bancada_id,
    bancada_nombre,
    COUNT(*) as concejales,
    array_agg(nombre_completo) as nombres
FROM users
GROUP BY tema, bancada_id, bancada_nombre;
