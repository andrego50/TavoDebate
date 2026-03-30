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

def get_provincia_for_municipio(municipio: str) -> str:
    """Retorna la provincia dado un municipio."""
    for provincia, municipios in PROVINCIAS_MUNICIPIOS.items():
        if municipio in municipios:
            return provincia
    return "Desconocida"
