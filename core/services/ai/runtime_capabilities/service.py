"""Orchestrates hardware detection + Ollama introspection + a live timing
benchmark into one recommendation report. Read-only: never persists anything
itself — the settings page applies a recommendation via the existing
AISettingsView save flow, same as any other manual setting change.
"""

from __future__ import annotations

from typing import Any

from core.services.ai.runtime_capabilities.hardware import detect_hardware
from core.services.ai.runtime_capabilities.ollama_introspection import (
    benchmark_generate,
    get_model_info,
    list_running_models,
)
from core.services.ai.runtime_capabilities.presets import recommend_config


def inspect_and_recommend(base_url: str, model: str, current: dict, timeout: int = 60) -> dict[str, Any]:
    """current: {ai_context_size, ai_max_tokens, ai_timeout, ai_keep_alive} —
    today's stored settings, used as the fallback whenever a real
    measurement isn't available. Never raises: every sub-call already
    degrades to None on failure."""
    hardware = detect_hardware()
    model_info = get_model_info(base_url, model, timeout=min(timeout, 15))
    running = list_running_models(base_url, timeout=min(timeout, 15))
    benchmark = benchmark_generate(base_url, model, timeout=timeout)

    result = recommend_config(current=current, model_info=model_info, hardware=hardware, benchmark=benchmark)

    return {
        "hardware": hardware,
        "model": model,
        "model_info": model_info,
        "running_models": running,
        "benchmark": benchmark,
        "recommended": result["recommended"],
        "notes": result["notes"],
    }
