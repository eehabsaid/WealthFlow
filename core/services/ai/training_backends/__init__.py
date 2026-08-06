from typing import Any
from core.services.ai.training_backends.base import BaseTrainingBackend
from core.services.ai.training_backends.ollama_backend import OllamaTrainingBackend
from core.services.ai.training_backends.generic_backend import GenericTrainingBackend

_TRAINING_BACKENDS: dict[str, BaseTrainingBackend] = {
    "ollama": OllamaTrainingBackend(),
    "unsloth": GenericTrainingBackend("unsloth"),
    "axolotl": GenericTrainingBackend("axolotl"),
    "llamacpp": GenericTrainingBackend("llamacpp"),
}


def get_training_backend(name: str = "ollama") -> BaseTrainingBackend:
    clean_name = str(name or "ollama").strip().lower()
    return _TRAINING_BACKENDS.get(clean_name, _TRAINING_BACKENDS["ollama"])


def get_available_training_backends() -> list[dict[str, Any]]:
    return [
        {"name": b.name, "is_available": b.is_available}
        for b in _TRAINING_BACKENDS.values()
    ]
