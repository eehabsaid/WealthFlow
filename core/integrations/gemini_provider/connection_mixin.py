"""
Connectivity check and model listing for GeminiProvider.
"""

from __future__ import annotations

import time
import urllib.parse
from typing import Any

from core.integrations.gemini_provider.constants import GEMINI_DEFAULT_MODELS
from core.services.ai.credential_encryption import redact_secrets


class GeminiConnectionMixin:
    def check_connection(self) -> dict[str, Any]:
        from core.integrations import gemini_provider as _gemini_provider_pkg

        start = time.perf_counter()
        if not self.api_key:
            return {"reachable": False, "version": None, "error": "Gemini API key is missing.", "response_time_ms": 0}

        secrets = [self.api_key]
        encoded_key = urllib.parse.quote(self.api_key)
        url = f"{self.base_url}/models?key={encoded_key}"

        data, status, err = _gemini_provider_pkg.make_json_http_request(url=url, method="GET", timeout=self.timeout, secrets=secrets)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        if err:
            safe_err = redact_secrets(err, secrets)
            return {"reachable": False, "version": None, "error": safe_err, "response_time_ms": elapsed_ms}

        return {"reachable": True, "version": "v1beta", "error": None, "response_time_ms": elapsed_ms}

    def list_models(self) -> list[dict[str, Any]]:
        from core.integrations import gemini_provider as _gemini_provider_pkg

        if not self.api_key:
            return list(GEMINI_DEFAULT_MODELS)

        secrets = [self.api_key]
        encoded_key = urllib.parse.quote(self.api_key)
        url = f"{self.base_url}/models?key={encoded_key}"

        data, status, err = _gemini_provider_pkg.make_json_http_request(url=url, method="GET", timeout=self.timeout, secrets=secrets)
        if err or not isinstance(data, dict):
            return list(GEMINI_DEFAULT_MODELS)

        models = data.get("models", [])
        if isinstance(models, list) and models:
            res = []
            for m in models:
                if isinstance(m, dict):
                    name_raw = str(m.get("name", "")).strip()
                    clean_name = name_raw.replace("models/", "") if name_raw.startswith("models/") else name_raw
                    if clean_name and "generateContent" in m.get("supportedGenerationMethods", []):
                        res.append({"name": clean_name, "model": clean_name})
            return res or list(GEMINI_DEFAULT_MODELS)
        return list(GEMINI_DEFAULT_MODELS)

    def check_model_available(self, model: str) -> bool:
        target = (model or self.model or "").strip().lower()
        if not target:
            return False
        return bool(self.api_key)
