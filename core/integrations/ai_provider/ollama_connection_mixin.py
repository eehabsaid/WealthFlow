"""Connection checks and model-listing methods for OllamaProvider."""

from __future__ import annotations

import time
from typing import Any

from core.integrations.provider_utils import make_json_http_request
from core.services.ai.credential_encryption import redact_secrets


class OllamaConnectionMixin:
    """Connection reachability and model listing/availability checks for Ollama."""

    def check_connection(self) -> dict[str, Any]:
        start_time = time.perf_counter()
        version_url = f"{self.base_url}/api/version"

        data, status, err = make_json_http_request(url=version_url, method="GET", timeout=self.timeout)
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        if not err and isinstance(data, dict):
            return {
                "reachable": True,
                "version": data.get("version", "unknown"),
                "error": None,
                "response_time_ms": elapsed_ms,
            }

        # Fallback to /api/tags if /api/version returned 404 or failed
        return self._check_tags_connection(start_time)

    def _check_tags_connection(self, start_time: float) -> dict[str, Any]:
        tags_url = f"{self.base_url}/api/tags"
        data, status, err = make_json_http_request(url=tags_url, method="GET", timeout=self.timeout)
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        if not err and isinstance(data, dict):
            return {
                "reachable": True,
                "version": "unknown",
                "error": None,
                "response_time_ms": elapsed_ms,
            }

        safe_err = redact_secrets(err or "Connection failed")
        return {
            "reachable": False,
            "version": None,
            "error": safe_err,
            "response_time_ms": elapsed_ms,
        }

    def list_models(self, include_fine_tuned: bool = False) -> list[dict[str, Any]]:
        tags_url = f"{self.base_url}/api/tags"
        data, status, err = make_json_http_request(url=tags_url, method="GET", timeout=self.timeout)
        if not err and isinstance(data, dict):
            models = data.get("models", [])
            if not isinstance(models, list):
                return []
            if include_fine_tuned:
                return models
            return [
                m for m in models
                if not str(m.get("name", "")).strip().lower().startswith("wealthflow-v")
            ]
        return []

    def check_model_available(self, model: str) -> bool:
        target_model = (model or self.model or "").strip().lower()
        if not target_model:
            return False

        models = self.list_models()
        for m in models:
            name = str(m.get("name", "")).strip().lower()
            model_id = str(m.get("model", "")).strip().lower()
            if target_model in (name, model_id):
                return True
            if ":" not in target_model and (name.startswith(f"{target_model}:") or model_id.startswith(f"{target_model}:")):
                return True
        return False
