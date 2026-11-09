"""Ollama runtime introspection: /api/show (model capabilities) and /api/ps
(currently loaded models + VRAM actually in use right now). Additive/
best-effort only — every function returns None on any failure instead of
raising, exactly like OllamaConnectionMixin.check_connection().
"""

from __future__ import annotations

from typing import Any

from core.integrations.provider_utils import make_json_http_request


def get_model_info(base_url: str, model: str, timeout: int = 15) -> dict[str, Any] | None:
    """POST /api/show — returns the model's real context length, parameter
    size and quantization as Ollama itself reports them, instead of guessing
    from the model name string. Returns None if unreachable, the model isn't
    pulled, or the response is malformed."""
    if not model:
        return None
    url = f"{base_url.rstrip('/')}/api/show"
    data, status, err = make_json_http_request(
        url=url, method="POST", payload={"model": model}, timeout=timeout
    )
    if err or not isinstance(data, dict):
        return None

    details = data.get("details") or {}
    model_info = data.get("model_info") or {}

    # The context-length key is namespaced by architecture
    # (e.g. "llama.context_length", "qwen2.context_length") — Ollama doesn't
    # expose it under a fixed key, so find whichever *.context_length key
    # is actually present rather than hardcoding one architecture.
    context_length = None
    if isinstance(model_info, dict):
        for key, value in model_info.items():
            if key.endswith(".context_length") and isinstance(value, (int, float)):
                context_length = int(value)
                break

    return {
        "family": details.get("family") if isinstance(details, dict) else None,
        "parameter_size": details.get("parameter_size") if isinstance(details, dict) else None,
        "quantization_level": details.get("quantization_level") if isinstance(details, dict) else None,
        "max_context_length": context_length,
    }


def list_running_models(base_url: str, timeout: int = 15) -> list[dict[str, Any]] | None:
    """GET /api/ps — models currently loaded in Ollama right now, with the
    VRAM/RAM they're actually occupying. Returns None if unreachable/malformed,
    [] if reachable but nothing is currently loaded."""
    url = f"{base_url.rstrip('/')}/api/ps"
    data, status, err = make_json_http_request(url=url, method="GET", timeout=timeout)
    if err or not isinstance(data, dict):
        return None
    models = data.get("models")
    if not isinstance(models, list):
        return None
    return [
        {
            "name": m.get("name"),
            "size_bytes": m.get("size"),
            "size_vram_bytes": m.get("size_vram"),
            "expires_at": m.get("expires_at"),
        }
        for m in models
        if isinstance(m, dict)
    ]


_BENCHMARK_PROMPT = "Reply with only the single word: OK."
_BENCHMARK_NUM_PREDICT = 8


def benchmark_generate(base_url: str, model: str, timeout: int = 60) -> dict[str, Any] | None:
    """Runs one small real generation against the model to MEASURE actual
    prompt-eval and decode throughput on this hardware right now, instead of
    guessing from parameter count/quantization — matches the project's
    'measure or compute latency, never guess' rule for AI timing. A short,
    fixed low-token-count prompt keeps the cost of running this on-demand
    (settings-page action, not per chat turn) to a couple of seconds even on
    slow hardware. Returns None on any failure (caller falls back to leaving
    the current setting unchanged)."""
    if not model:
        return None
    url = f"{base_url.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "prompt": _BENCHMARK_PROMPT,
        "stream": False,
        "options": {"num_predict": _BENCHMARK_NUM_PREDICT},
    }
    data, status, err = make_json_http_request(url=url, method="POST", payload=payload, timeout=timeout)
    if err or not isinstance(data, dict):
        return None

    def ns_to_sec(key: str) -> float:
        v = data.get(key)
        return float(v) / 1e9 if isinstance(v, (int, float)) else 0.0

    prompt_tokens = data.get("prompt_eval_count")
    prompt_eval_s = ns_to_sec("prompt_eval_duration")
    gen_tokens = data.get("eval_count")
    gen_s = ns_to_sec("eval_duration")

    if not isinstance(prompt_tokens, (int, float)) or not isinstance(gen_tokens, (int, float)):
        return None

    prompt_tok_per_sec = (prompt_tokens / prompt_eval_s) if prompt_eval_s > 0 else None
    decode_tok_per_sec = (gen_tokens / gen_s) if gen_s > 0 else None

    return {
        "prompt_tokens": int(prompt_tokens),
        "prompt_eval_seconds": round(prompt_eval_s, 3),
        "prompt_tok_per_sec": round(prompt_tok_per_sec, 2) if prompt_tok_per_sec else None,
        "gen_tokens": int(gen_tokens),
        "gen_seconds": round(gen_s, 3),
        "decode_tok_per_sec": round(decode_tok_per_sec, 2) if decode_tok_per_sec else None,
    }
