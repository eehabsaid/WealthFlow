"""Runtime capability inspection: hardware detection, Ollama /api/show +
/api/ps introspection, a live timing benchmark, and the resulting
per-model/per-hardware config recommendation (ai_context_size, ai_max_tokens,
ai_timeout, ai_keep_alive). Read-only — applying a recommendation goes
through the existing AISettingsView save flow.
"""

from core.services.ai.runtime_capabilities.hardware import detect_hardware
from core.services.ai.runtime_capabilities.ollama_introspection import (
    benchmark_generate,
    get_model_info,
    list_running_models,
)
from core.services.ai.runtime_capabilities.presets import recommend_config
from core.services.ai.runtime_capabilities.service import inspect_and_recommend

__all__ = [
    "detect_hardware",
    "benchmark_generate",
    "get_model_info",
    "list_running_models",
    "recommend_config",
    "inspect_and_recommend",
]
