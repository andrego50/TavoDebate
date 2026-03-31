"""TavoDebate - Configuración central del sistema."""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str = ""
    admin_user_ids: str = ""
    admin_chat_id: str = ""

    # LLM Providers
    deepseek_api_key: str = ""
    kimi_api_key: str = ""
    openai_api_key: str = ""
    llm_primary: str = "deepseek"

    # Database
    database_url: str = "postgresql+asyncpg://concejo:concejo2026@postgres:5432/concejo_futuro"
    postgres_password: str = "concejo2026"

    # Redis
    redis_url: str = "redis://redis:6379"

    # Config
    briefing_interval_seconds: int = 120
    environment: str = "dev"
    vps_domain: str = "localhost"
    telegram_webhook_url: str = ""

    # Agent
    agent_type: str = "orchestrator"
    instance_id: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def admin_ids(self) -> list[int]:
        return [int(x.strip()) for x in self.admin_user_ids.split(",") if x.strip()]

    @property
    def admin_chat_id_int(self) -> int:
        return int(self.admin_chat_id) if self.admin_chat_id else 0

    @property
    def is_dev(self) -> bool:
        return self.environment == "dev"

    @property
    def webhook_url(self) -> str:
        return f"https://{self.vps_domain}:8000/webhook"


def get_settings() -> Settings:
    return Settings()


settings = Settings()

# --- Constantes del taller ---

BANCADAS = {
    1: {"nombre": "🏛️ Gobierno", "posicion": "A FAVOR"},
    2: {"nombre": "⚖️ Oposición", "posicion": "EN CONTRA"},
    3: {"nombre": "🌾 Rural", "posicion": "CONDICIONAL"},
    4: {"nombre": "🏙️ Urbana", "posicion": "PRAGMÁTICOS"},
    5: {"nombre": "💰 Presupuesto", "posicion": "FISCALIZACIÓN"},
    6: {"nombre": "👁️ Veeduría", "posicion": "CONTROL SOCIAL"},
}

# Roles del ejercicio — algunos votan, otros participan sin voto
ROLES = {
    # === CONCEJALES (votan) ===
    "concejal": {
        "nombre": "🏛️ Concejal",
        "grupo": "concejo",
        "descripcion": "Representante del Concejo — vota el proyecto",
        "puede_votar": True,
    },
    # === GOBIERNO (defienden el proyecto, no votan) ===
    "alcalde": {
        "nombre": "👔 Alcalde Proponente",
        "grupo": "gobierno",
        "descripcion": "Defiende el proyecto SIADR ante el Concejo",
        "puede_votar": False,
    },
    "sec_planeacion": {
        "nombre": "📐 Secretario de Planeación",
        "grupo": "gobierno",
        "descripcion": "Datos técnicos, viabilidad y metodología del SIADR",
        "puede_votar": False,
    },
    "sec_hacienda": {
        "nombre": "💰 Secretario de Hacienda",
        "grupo": "gobierno",
        "descripcion": "Presupuesto, regalías y sostenibilidad financiera",
        "puede_votar": False,
    },
    "sec_agricultura": {
        "nombre": "🌾 Secretario de Agricultura",
        "grupo": "gobierno",
        "descripcion": "Componente agro, UMATA y familias campesinas",
        "puede_votar": False,
    },
    "dir_tic": {
        "nombre": "📡 Director de TIC",
        "grupo": "gobierno",
        "descripcion": "Conectividad, infraestructura tecnológica e IoT",
        "puede_votar": False,
    },
    "dir_umata": {
        "nombre": "🧑‍🌾 Director UMATA",
        "grupo": "gobierno",
        "descripcion": "Puente entre tecnología y comunidades campesinas",
        "puede_votar": False,
    },
    # === SOCIEDAD CIVIL (opinan, presionan, no votan) ===
    "lider_campesino": {
        "nombre": "🧑‍🌾 Líder Campesino",
        "grupo": "sociedad_civil",
        "descripcion": "Representa a comunidades rurales y veredas",
        "puede_votar": False,
    },
    "lider_indigena": {
        "nombre": "🪶 Líder Indígena",
        "grupo": "sociedad_civil",
        "descripcion": "Derechos étnicos y consulta previa",
        "puede_votar": False,
    },
    "lider_jac": {
        "nombre": "🏘️ Líder JAC",
        "grupo": "sociedad_civil",
        "descripcion": "Junta de Acción Comunal — necesidades locales",
        "puede_votar": False,
    },
    "ambientalista": {
        "nombre": "🌿 Ambientalista",
        "grupo": "sociedad_civil",
        "descripcion": "Impacto ambiental, agua y ecosistemas",
        "puede_votar": False,
    },
    "periodista": {
        "nombre": "📰 Periodista",
        "grupo": "sociedad_civil",
        "descripcion": "Investiga y publica sobre el debate",
        "puede_votar": False,
    },
    # === SECTOR PRIVADO / EMPRESA ===
    "empresa_tech": {
        "nombre": "🏢 Empresa TechCundi",
        "grupo": "empresa",
        "descripcion": "Consorcio que ejecutaría el SIADR",
        "puede_votar": False,
    },
    "gremio_agro": {
        "nombre": "🌽 Gremio Agrícola",
        "grupo": "empresa",
        "descripcion": "Representa agricultores y productores",
        "puede_votar": False,
    },
    # === CONTROL / INSTITUCIONAL ===
    "contralor": {
        "nombre": "📋 Contralor Departamental",
        "grupo": "control",
        "descripcion": "Vigila el uso de recursos públicos",
        "puede_votar": False,
    },
    "personero": {
        "nombre": "⚖️ Personero Municipal",
        "grupo": "control",
        "descripcion": "Derechos ciudadanos y legalidad del proceso",
        "puede_votar": False,
    },
    "veedor": {
        "nombre": "👁️ Veedor Ciudadano",
        "grupo": "control",
        "descripcion": "Control social y transparencia",
        "puede_votar": False,
    },
}

PROVINCIAS_MUNICIPIOS = {
    "Almeidas": ["Chocontá", "Machetá", "Manta", "Sesquilé", "Suesca", "Tibirita", "Villapinzón"],
    "Alto Magdalena": ["Agua de Dios", "Girardot", "Guataquí", "Jerusalén", "Nariño", "Nilo", "Ricaurte", "Tocaima"],
    "Bajo Magdalena": ["Caparrapí", "Guaduas", "Puerto Salgar"],
    "Gualivá": ["Albán", "La Peña", "La Vega", "Nimaima", "Nocaima", "Quebradanegra", "San Francisco", "Sasaima", "Supatá", "Útica", "Vergara", "Villeta"],
    "Guavio": ["Gachalá", "Gachetá", "Gama", "Guasca", "Guatavita", "Junín", "Ubalá"],
    "Magdalena Centro": ["Bituima", "Chaguaní", "Guayabal de Síquima", "Pulí", "San Juan de Rioseco", "Vianí"],
    "Medina": ["Medina", "Paratebueno"],
    "Oriente": ["Cáqueza", "Chipaque", "Choachí", "Fómeque", "Fosca", "Guayabetal", "Gutiérrez", "Quetame", "Ubaque", "Une"],
    "Rionegro": ["El Peñón", "La Palma", "Pacho", "Paime", "San Cayetano", "Topaipí", "Villagómez", "Yacopí"],
    "Sabana Centro": ["Cajicá", "Chía", "Cogua", "Cota", "Gachancipá", "Nemocón", "Sopó", "Tabio", "Tenjo", "Tocancipá", "Zipaquirá"],
    "Sabana Occidente": ["Bojacá", "El Rosal", "Facatativá", "Funza", "Madrid", "Mosquera", "Subachoque", "Zipacón"],
    "Soacha": ["Sibaté", "Soacha"],
    "Sumapaz": ["Arbeláez", "Cabrera", "Fusagasugá", "Granada", "Pandi", "Pasca", "San Bernardo", "Silvania", "Tibacuy", "Venecia"],
    "Tequendama": ["Anapoima", "Anolaima", "Apulo", "Cachipay", "El Colegio", "La Mesa", "Quipile", "San Antonio del Tequendama", "Tena", "Viotá"],
    "Ubaté": ["Carmen de Carupa", "Cucunubá", "Fúquene", "Guachetá", "Lenguazaque", "Simijaca", "Susa", "Sutatausa", "Tausa", "Ubaté"],
}

MUNICIPIOS_COORDS = {
    "Chocontá": (5.146, -73.684), "Villapinzón": (5.215, -73.597),
    "Girardot": (4.302, -74.802), "Agua de Dios": (4.378, -74.667),
    "Guaduas": (5.067, -74.598), "Caparrapí": (5.349, -74.496),
    "Villeta": (5.014, -74.472), "La Vega": (4.998, -74.341),
    "Gachetá": (4.818, -73.637), "Guasca": (4.866, -73.877),
    "San Juan de Rioseco": (4.847, -74.627), "Vianí": (4.874, -74.558),
    "Medina": (4.509, -73.349), "Paratebueno": (4.375, -73.213),
    "Cáqueza": (4.408, -73.948), "Fómeque": (4.487, -73.895),
    "Pacho": (5.131, -74.159), "Yacopí": (5.459, -74.339),
    "Zipaquirá": (5.022, -74.005), "Cajicá": (4.919, -74.028),
    "Facatativá": (4.815, -74.355), "Madrid": (4.734, -74.264),
    "Soacha": (4.579, -74.217), "Sibaté": (4.49, -74.26),
    "Fusagasugá": (4.337, -74.364), "Cabrera": (3.979, -74.486),
    "La Mesa": (4.633, -74.462), "Viotá": (4.438, -74.523),
    "Ubaté": (5.308, -73.816), "Simijaca": (5.505, -73.852),
    "Chía": (4.862, -74.059), "Cogua": (5.063, -73.978),
    "Cota": (4.813, -74.102), "Gachancipá": (4.993, -73.874),
    "Nemocón": (5.066, -73.879), "Sopó": (4.907, -73.942),
    "Tabio": (4.914, -74.098), "Tenjo": (4.870, -74.144),
    "Tocancipá": (4.964, -73.912),
}


def get_provincia_for_municipio(municipio: str) -> str:
    """Retorna la provincia dado un municipio."""
    for provincia, municipios in PROVINCIAS_MUNICIPIOS.items():
        if municipio in municipios:
            return provincia
    return "Desconocida"


def get_coords_for_municipio(municipio: str) -> tuple[float, float] | None:
    """Retorna (lat, lng) para un municipio, o None si no se conoce."""
    return MUNICIPIOS_COORDS.get(municipio)
