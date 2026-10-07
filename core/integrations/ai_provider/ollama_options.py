"""Generation-option building for OllamaProvider.generate()."""

from __future__ import annotations

from typing import Any


def build_options(kwargs: dict[str, Any], user_options: dict[str, Any]) -> dict[str, Any]:
    """Merge call kwargs > per-user options > AppSettings into Ollama's options dict."""
    from core.models import AppSettings

    options: dict[str, Any] = {}
    try:
        options["num_predict"] = int(kwargs.get("max_tokens") or user_options.get("max_tokens") or AppSettings.get("ai_max_tokens", "2048"))
    except (ValueError, TypeError):
        pass
    try:
        options["temperature"] = float(kwargs.get("temperature") or user_options.get("temperature") or AppSettings.get("ai_temperature", "0.7"))
    except (ValueError, TypeError):
        pass
    try:
        options["num_ctx"] = int(kwargs.get("context_size") or user_options.get("context_size") or AppSettings.get("ai_context_size", "4096"))
    except (ValueError, TypeError):
        pass
    try:
        top_k_val = kwargs.get("top_k") or AppSettings.get("ai_top_k", None)
        if top_k_val not in (None, ""):
            options["top_k"] = int(top_k_val)
    except (ValueError, TypeError):
        pass
    try:
        top_p_val = kwargs.get("top_p") or AppSettings.get("ai_top_p", None)
        if top_p_val not in (None, ""):
            options["top_p"] = float(top_p_val)
    except (ValueError, TypeError):
        pass
    try:
        repeat_penalty_val = kwargs.get("repeat_penalty") or AppSettings.get("ai_repeat_penalty", None)
        if repeat_penalty_val not in (None, ""):
            options["repeat_penalty"] = float(repeat_penalty_val)
    except (ValueError, TypeError):
        pass
    try:
        # ai_seed: blank means "no fixed seed" (non-deterministic) — the
        # normal case. Only set options["seed"] when a real value is
        # configured; an empty string must never reach int().
        seed_val = kwargs.get("seed") or AppSettings.get("ai_seed", None)
        if seed_val not in (None, ""):
            options["seed"] = int(seed_val)
    except (ValueError, TypeError):
        pass
    return options
