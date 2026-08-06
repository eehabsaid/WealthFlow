"""
Base Training Backend Interface.

Defines pluggable training backend protocol for model fine-tuning adapters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTrainingBackend(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of training backend adapter."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if underlying training framework CLI or API is accessible."""
        pass

    @abstractmethod
    def train_model(
        self,
        dataset_path: str,
        base_model_name: str,
        output_version_name: str,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Executes model training/fine-tuning pipeline."""
        pass
