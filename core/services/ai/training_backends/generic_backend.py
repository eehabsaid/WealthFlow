"""
Generic / External Training Backend Adapter (Unsloth, Axolotl, LlamaCpp).
"""

from __future__ import annotations

import logging
from typing import Any
from core.services.ai.training_backends.base import BaseTrainingBackend

logger = logging.getLogger(__name__)


class GenericTrainingBackend(BaseTrainingBackend):
    def __init__(self, backend_name: str = "unsloth"):
        self._name = backend_name

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_available(self) -> bool:
        return True

    def train_model(
        self,
        dataset_path: str,
        base_model_name: str,
        output_version_name: str,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "status": "Prepared dataset for external trainer",
            "backend": self.name,
            "dataset_path": dataset_path,
            "output_version_name": output_version_name,
        }
