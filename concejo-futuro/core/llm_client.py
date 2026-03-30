"""TavoDebate - Cliente LLM multi-proveedor con circuit breaker."""

import hashlib
import json
import logging
import time
from enum import Enum

import httpx
import redis.asyncio as aioredis

from core.config import settings

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    DEEPSEEK = "deepseek"
    KIMI = "kimi"


PROVIDER_CONFIG = {
    LLMProvider.DEEPSEEK: {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "api_key_attr": "deepseek_api_key",
    },
    LLMProvider.KIMI: {
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
        "api_key_attr": "kimi_api_key",
    },
}

RESPUESTAS_EMERGENCIA = {
    "default": (
        "El sistema de IA está temporalmente saturado. Mientras tanto, "
        "revisa tu dossier de bancada (/estado) y prepara tus argumentos."
    ),
    "costos": (
        "El proyecto SIADR tiene un presupuesto de $2.400M COP para 30 "
        "municipios piloto. Consulta tu dossier para más detalles."
    ),
    "corrupcion": (
        "Recuerda los precedentes: Centros Poblados ($70.000M), "
        "Agro Ingreso Seguro. Pregunta al contralor (/contralor)."
    ),
    "privacidad": (
        "El proyecto contempla anonimización de datos y auditoría ciudadana. "
        "Revisa el artículo 12 del proyecto de acuerdo."
    ),
    "empleo": (
        "El SIADR no reemplaza empleos existentes. Automatiza la priorización "
        "que hoy se hace manualmente o no se hace."
    ),
}


class CircuitBreaker:
    def __init__(self, max_failures: int = 3, reset_timeout: int = 60):
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.is_open = False

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.max_failures:
            self.is_open = True
            logger.warning("Circuit breaker OPEN")

    def record_success(self):
        self.failures = 0
        self.is_open = False

    def can_execute(self) -> bool:
        if not self.is_open:
            return True
        if time.time() - self.last_failure_time > self.reset_timeout:
            self.is_open = False
            self.failures = 0
            logger.info("Circuit breaker RESET")
            return True
        return False


class LLMClient:
    def __init__(self, redis_client: aioredis.Redis | None = None):
        self.primary = LLMProvider(settings.llm_primary)
        self.fallback = (
            LLMProvider.KIMI
            if self.primary == LLMProvider.DEEPSEEK
            else LLMProvider.DEEPSEEK
        )
        self.breakers = {
            LLMProvider.DEEPSEEK: CircuitBreaker(),
            LLMProvider.KIMI: CircuitBreaker(),
        }
        self.redis = redis_client
        self.http = httpx.AsyncClient(timeout=30.0)

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        use_cache: bool = True,
        cache_voice: str = "default",
    ) -> str:
        # Check cache
        if use_cache and self.redis:
            cached = await self._get_cache(cache_voice, user_message)
            if cached:
                return cached

        # Try primary, then fallback
        for provider in [self.primary, self.fallback]:
            if not self.breakers[provider].can_execute():
                continue
            try:
                response = await self._call_provider(
                    provider, system_prompt, user_message, temperature, max_tokens
                )
                self.breakers[provider].record_success()
                if use_cache and self.redis:
                    await self._set_cache(cache_voice, user_message, response)
                return response
            except Exception as e:
                logger.error(f"LLM error ({provider.value}): {e}")
                self.breakers[provider].record_failure()

        # Degraded mode
        logger.warning("All LLM providers failed, using emergency response")
        return self._get_emergency_response(user_message)

    async def _call_provider(
        self,
        provider: LLMProvider,
        system_prompt: str,
        user_message: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        config = PROVIDER_CONFIG[provider]
        api_key = getattr(settings, config["api_key_attr"])

        response = await self.http.post(
            f"{config['base_url']}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": config["model"],
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def _get_cache(self, voice: str, question: str) -> str | None:
        key = self._cache_key(voice, question)
        cached = await self.redis.get(key)
        if cached:
            logger.debug(f"Cache hit: {key}")
            return cached.decode()
        return None

    async def _set_cache(self, voice: str, question: str, response: str):
        key = self._cache_key(voice, question)
        await self.redis.setex(key, 300, response)

    @staticmethod
    def _cache_key(voice: str, question: str) -> str:
        normalized = question.lower().strip()[:200]
        h = hashlib.md5(normalized.encode()).hexdigest()
        return f"llm_cache:{voice}:{h}"

    @staticmethod
    def _get_emergency_response(user_message: str) -> str:
        msg_lower = user_message.lower()
        for keyword, response in RESPUESTAS_EMERGENCIA.items():
            if keyword != "default" and keyword in msg_lower:
                return response
        return RESPUESTAS_EMERGENCIA["default"]

    async def switch_primary(self, provider: str):
        self.primary = LLMProvider(provider)
        self.fallback = (
            LLMProvider.KIMI
            if self.primary == LLMProvider.DEEPSEEK
            else LLMProvider.DEEPSEEK
        )
        logger.info(f"LLM primary switched to {provider}")

    async def close(self):
        await self.http.aclose()
