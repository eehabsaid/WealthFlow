"""Does the chosen model accept images? Decided per provider; an unknown answer is "no", so the UIs disable the image option instead of guessing.
Ollama is asked (POST /api/show lists "vision" among a model's capabilities); the cloud providers are decided by model name."""

from __future__ import annotations

import json
import re
import threading
import time
import urllib.request

OPENAI = re.compile(r"^(gpt-4o|gpt-4\.1|gpt-4\.5|gpt-5|gpt-4-turbo|gpt-4-vision|chatgpt-4o|o1(?!-mini|-preview)|o3|o4)")
GEMINI = re.compile(r"^gemini-(1\.5|2|3)")
TTL = 60.0
_cache: dict = {}
_lock = threading.Lock()


def _ollama(base_url: str, model: str, timeout: float) -> tuple[bool, str]:
    request = urllib.request.Request(f"{base_url.rstrip('/')}/api/show", data=json.dumps({"model": model}).encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            caps = json.loads(response.read().decode("utf-8")).get("capabilities") or []
    except (OSError, ValueError, AttributeError):
        return False, "could not ask Ollama whether this model accepts images"
    return ("vision" in caps), ("" if "vision" in caps else "this Ollama model does not report vision support")


def check(provider: str, model: str, base_url: str = "", timeout: float = 3.0) -> tuple[bool, str]:
    """(accepts images, why not)."""
    name = (model or "").strip().lower()
    if not name:
        return False, "no model chosen"
    if provider == "anthropic":
        ok = name.startswith("claude") and not name.startswith(("claude-2", "claude-instant"))
    elif provider == "openai":
        ok = bool(OPENAI.match(name))
    elif provider == "gemini":
        ok = bool(GEMINI.match(name))
    elif provider == "ollama":
        key = (base_url, name)
        with _lock:
            hit = _cache.get(key)
        if hit and time.monotonic() - hit[0] < TTL:
            return hit[1]
        result = _ollama(base_url, model, timeout)
        with _lock:
            _cache[key] = (time.monotonic(), result)
        return result
    else:
        return False, "unknown provider"
    return ok, "" if ok else f"{model} is not known to accept images"


def supports_images(provider: str, model: str, base_url: str = "") -> bool:
    return check(provider, model, base_url)[0]
