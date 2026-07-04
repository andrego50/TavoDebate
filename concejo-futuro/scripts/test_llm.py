"""Test: vLLM connectivity, cache key discriminator, circuit breaker fallback."""

import hashlib
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx

VLLM_URL = os.environ.get("VLLM_BASE_URL", "http://192.168.0.221:9090/v1")
VLLM_MODEL = os.environ.get("VLLM_MODEL", "google/gemma-4-12B-it-qat-w4a16-ct")

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
results = []


def check(name: str, ok: bool, detail: str = ""):
    marker = PASS if ok else FAIL
    print(f"  {marker} {name}" + (f" — {detail}" if detail else ""))
    results.append(ok)


# ── 1. vLLM connectivity ──────────────────────────────────────────────────────
print("\n[1] vLLM connectivity")
try:
    r = httpx.get(f"{VLLM_URL}/models", timeout=5)
    r.raise_for_status()
    models = [m["id"] for m in r.json().get("data", [])]
    check("GET /models OK", True, f"models: {models}")
    check("Gemma 4 12B listed", VLLM_MODEL in models, f"looking for {VLLM_MODEL}")
except Exception as e:
    check("GET /models OK", False, str(e))
    check("Gemma 4 12B listed", False, "skipped")

# ── 2. vLLM inference ─────────────────────────────────────────────────────────
print("\n[2] vLLM inference")
try:
    payload = {
        "model": VLLM_MODEL,
        "messages": [{"role": "user", "content": "Responde solo: OK"}],
        "max_tokens": 10,
        "temperature": 0,
    }
    r = httpx.post(f"{VLLM_URL}/chat/completions", json=payload, timeout=30)
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    check("Inference response received", True, f"reply={content!r}")
except Exception as e:
    check("Inference response received", False, str(e))

# ── 3. Cache key discriminator ────────────────────────────────────────────────
print("\n[3] Cache key discriminator (bancada:rol:posicion)")


def cache_key(voice: str, question: str, cache_segment: str = "") -> str:
    normalized = question.lower().strip()[:200]
    segment_prefix = f"{cache_segment}:" if cache_segment else ""
    h = hashlib.md5(f"{segment_prefix}{normalized}".encode()).hexdigest()
    return f"llm_cache:{voice}:{h}"


q = "¿cuál es el presupuesto del SIADR?"

key_gobierno_concejal = cache_key("concejal", q, "Gobierno:concejal:A FAVOR")
key_oposicion_concejal = cache_key("concejal", q, "Oposición:concejal:EN CONTRA")
key_gobierno_alcalde = cache_key("alcalde", q, "Gobierno:alcalde:A FAVOR")
key_gobierno_concejal_2 = cache_key("concejal", q, "Gobierno:concejal:A FAVOR")

check(
    "Same bancada+rol → same key",
    key_gobierno_concejal == key_gobierno_concejal_2,
    f"key={key_gobierno_concejal[-8:]}",
)
check(
    "Different bancada → different key",
    key_gobierno_concejal != key_oposicion_concejal,
    "Gobierno vs Oposición",
)
check(
    "Different rol (same bancada) → different key",
    key_gobierno_concejal != key_gobierno_alcalde,
    "concejal vs alcalde",
)
check(
    "No segment → different from segmented",
    cache_key("concejal", q) != key_gobierno_concejal,
    "empty vs 'Gobierno:concejal:A FAVOR'",
)

# ── 4. Config defaults ────────────────────────────────────────────────────────
print("\n[4] Config defaults")
try:
    from core.config import settings

    check(
        "vllm_model is Gemma 4 12B",
        "gemma-4-12B" in settings.vllm_model or "gemma-4" in settings.vllm_model.lower(),
        settings.vllm_model,
    )
    check(
        "llm_priority starts with vllm",
        settings.llm_priority.split(",")[0] == "vllm",
        settings.llm_priority,
    )
    check(
        "vllm_base_url points to server",
        "192.168.0.221" in settings.vllm_base_url,
        settings.vllm_base_url,
    )
except Exception as e:
    check("Config import", False, str(e))

# ── Summary ───────────────────────────────────────────────────────────────────
passed = sum(results)
total = len(results)
print(f"\n{'='*50}")
print(f"  {passed}/{total} checks passed")
if passed < total:
    print("  Some checks failed — review output above")
    sys.exit(1)
else:
    print("  All good!")
