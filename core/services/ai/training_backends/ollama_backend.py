"""
Ollama Training & Customization Backend Adapter.
"""

from __future__ import annotations

import json
import os
import subprocess
import logging
from typing import Any
from django.conf import settings
from core.services.ai.training_backends.base import BaseTrainingBackend

logger = logging.getLogger(__name__)

# Caps how many dataset examples get baked into the Modelfile as MESSAGE
# few-shot pairs. Ollama Modelfiles have no hard example-count limit, but an
# unbounded number of examples would produce a huge file and a slow/unwieldy
# `ollama create`, without meaningfully improving the model further — a
# representative sample is enough to steer style and domain answers.
MAX_TRAINING_EXAMPLES_FOR_MODELFILE = 30

# Caps how many characters of any single dataset field get embedded, so one
# unusually long instruction/answer can't blow up the Modelfile or break the
# triple-quoted MESSAGE block.
_MAX_FIELD_CHARS = 600


def _escape_modelfile_text(text: str) -> str:
    """Makes a string safe to embed inside a Modelfile triple-quoted
    MESSAGE block: escapes backslashes and double quotes, collapses
    newlines to spaces, and truncates to a sane length."""
    text = str(text or "").replace("\\", "\\\\").replace('"', '\\"')
    text = " ".join(text.split())
    if len(text) > _MAX_FIELD_CHARS:
        text = text[: _MAX_FIELD_CHARS - 1] + "…"
    return text


def _load_training_examples(dataset_path: str) -> list[dict[str, str]]:
    """Reads the SFT dataset JSONL file produced by AIDatasetEngine and
    returns up to MAX_TRAINING_EXAMPLES_FOR_MODELFILE valid (instruction,
    answer) pairs. Malformed lines and a missing/unreadable file are skipped
    rather than raised, since a dataset problem shouldn't block training —
    the Modelfile falls back to just the base model + system prompt."""
    examples: list[dict[str, str]] = []
    if not dataset_path or not os.path.isfile(dataset_path):
        return examples

    try:
        with open(dataset_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue

                instruction = str(row.get("instruction", "")).strip()
                context = str(row.get("context", "")).strip()
                answer = str(row.get("answer", "")).strip()
                if not instruction or not answer:
                    continue

                user_text = f"{instruction} {context}".strip() if context else instruction
                examples.append({"user": user_text, "assistant": answer})

                if len(examples) >= MAX_TRAINING_EXAMPLES_FOR_MODELFILE:
                    break
    except OSError as exc:
        logger.warning("Could not read training dataset at %s: %s", dataset_path, exc)
        return []

    return examples


class OllamaTrainingBackend(BaseTrainingBackend):
    @property
    def name(self) -> str:
        return "ollama"

    @property
    def is_available(self) -> bool:
        try:
            res = subprocess.run(["ollama", "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3)
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
        Builds a custom Ollama Modelfile incorporating system directives,
        real dataset examples as MESSAGE few-shot pairs, and creates a new
        local Ollama model version from it.
        """
        config = config or {}
        modelfile_dir = os.path.join(settings.BASE_DIR, "ai_knowledge", "modelfiles")
        os.makedirs(modelfile_dir, exist_ok=True)

        modelfile_path = os.path.join(modelfile_dir, f"Modelfile_{output_version_name}")

        examples = _load_training_examples(dataset_path)

        lines = [
            f"FROM {base_model_name}",
            'SYSTEM """You are the WealthFlow AI Assistant, trained on specialized WealthFlow domain knowledge and financial reasoning. Answer accurately and strictly format numbers."""',
            "PARAMETER temperature 0.2",
        ]
        for ex in examples:
            lines.append(f'MESSAGE user """{_escape_modelfile_text(ex["user"])}"""')
            lines.append(f'MESSAGE assistant """{_escape_modelfile_text(ex["assistant"])}"""')

        modelfile_content = "\n".join(lines) + "\n"

        with open(modelfile_path, "w", encoding="utf-8") as f:
            f.write(modelfile_content)

        if not self.is_available:
            return {
                "ok": False,
                "error": "Ollama CLI is not installed or accessible on system PATH.",
                "modelfile_path": modelfile_path,
                "training_examples_used": len(examples),
            }

        try:
            cmd = ["ollama", "create", output_version_name, "-f", modelfile_path]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
            if res.returncode == 0:
                return {
                    "ok": True,
                    "model_version_name": output_version_name,
                    "modelfile_path": modelfile_path,
                    "backend": self.name,
                    "training_examples_used": len(examples),
                }
            return {
                "ok": False,
                "error": f"Ollama create failed: {res.stderr}",
                "modelfile_path": modelfile_path,
                "training_examples_used": len(examples),
            }
        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
                "modelfile_path": modelfile_path,
                "training_examples_used": len(examples),
            }

