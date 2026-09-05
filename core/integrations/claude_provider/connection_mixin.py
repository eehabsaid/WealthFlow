"""
Connectivity check and model listing for ClaudeProvider.
"""

from __future__ import annotations

import time
from typing import Any

from core.integrations.claude_provider.constants import CLAUDE_DEFAULT_MODELS
from core.services.ai.credential_encryption import redact_secrets


class ClaudeConnectionMixin:
    def check_connection(self) -> dict[str, Any]:
        from core.integrations import claude_provider as _claude_provider_pkg

        start = time.perf_counter()
        if not self.api_key:
            return {"reachable": False, "version": None, "error": "Claude API key is missing.", "response_time_ms": 0}

        secrets = [self.api_key]
        # Minimal messages ping request to test key validity
        url = f"{self.base_url}/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        payload = {
            "model": self.model or "claude-3-5-haiku-20241022",
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
        }

        data, status, err = _claude_provider_pkg.make_json_http_request(url=url, method="POST", headers=headers, payload=payload, timeout=self.timeout, secrets=secrets)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        if err:
            safe_err = redact_secrets(err, secrets)
            return {"reachable": False, "version": None, "error": safe_err, "response_time_ms": elapsed_ms}

        return {"reachable": True, "version": "2023-06-01", "error": None, "response_time_ms": elapsed_ms}

    def list_models(self) -> list[dict[str, Any]]:
        # Anthropic does not have a public list models REST endpoint; return curated list
        return list(CLAUDE_DEFAULT_MODELS)

    def check_model_available(self, model: str) -> bool:
        target = (model or self.model or "").strip().lower()
        if not target:
            return False
        # If API key is present, accept valid model string format
        return bool(self.api_key)
