"""
Ollama Training & Customization Backend Adapter.
"""

from __future__ import annotations

import os
import subprocess
import logging
from typing import Any
from django.conf import settings
from core.services.ai.training_backends.base import BaseTrainingBackend

logger = logging.getLogger(__name__)


class OllamaTrainingBackend(BaseTrainingBackend):
    @property
    def name(self) -> str:
        return "ollama"

    @property
    def is_available(self) -> bool:
        try:
            res = subprocess.run(["ollama", "--version"], capture_output=True, text=True, timeout=3)
            return res.returncode == 0
        except Exception:
            return False

    def train_model(
        self,
        dataset_path: str,
        base_model_name: str,
        output_version_name: str,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Builds a custom Ollama Modelfile incorporating system directives and creates new model version.
        """
        config = config or {}
        modelfile_dir = os.path.join(settings.BASE_DIR, ".brain", "modelfiles")
        os.makedirs(modelfile_dir, exist_ok=True)

        modelfile_path = os.path.join(modelfile_dir, f"Modelfile_{output_version_name}")

        modelfile_content = f"""FROM {base_model_name}
SYSTEM \"\"\"You are the WealthFlow AI Assistant, trained on specialized WealthFlow domain knowledge and financial reasoning. Answer accurately and strictly format numbers.\"\"\"
PARAMETER temperature 0.2
"""

        with open(modelfile_path, "w", encoding="utf-8") as f:
            f.write(modelfile_content)

        if not self.is_available:
            return {
                "ok": False,
                "error": "Ollama CLI is not installed or accessible on system PATH.",
                "modelfile_path": modelfile_path,
            }

        try:
            cmd = ["ollama", "create", output_version_name, "-f", modelfile_path]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode == 0:
                return {
                    "ok": True,
                    "model_version_name": output_version_name,
                    "modelfile_path": modelfile_path,
                    "backend": self.name,
                }
            return {
                "ok": False,
                "error": f"Ollama create failed: {res.stderr}",
                "modelfile_path": modelfile_path,
            }
        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
                "modelfile_path": modelfile_path,
            }
