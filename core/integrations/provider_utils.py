"""
Shared Provider HTTP Utilities.

Provides centralized JSON HTTP request/response handling using stdlib urllib.request.
Automatically redacts API keys and sensitive credentials from exception messages and logs.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Sequence

from core.services.ai.credential_encryption import redact_secrets

logger = logging.getLogger(__name__)


def make_json_http_request(
    url: str,
    method: str = "POST",
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = 15,
    secrets: Sequence[str | None] | None = None,
) -> tuple[dict[str, Any] | list[Any] | None, int, str | None]:
    """
    Execute standard JSON HTTP request via urllib.request.

    Returns tuple: (parsed_json_data, status_code, error_message)
    Error messages and logged warnings are strictly sanitized with redact_secrets().
    """
    req_headers = {
        "User-Agent": "WealthFlow/1.0",
        "Accept": "application/json",
    }
    if headers:
        req_headers.update(headers)

    req_data = None
    if payload is not None and method.upper() in ("POST", "PUT", "PATCH"):
        req_headers["Content-Type"] = "application/json"
        req_data = json.dumps(payload).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=req_data, headers=req_headers, method=method.upper())
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw_body = resp.read().decode("utf-8")
            status_code = resp.status
            parsed_data = json.loads(raw_body) if raw_body else {}
            return parsed_data, status_code, None
    except urllib.error.HTTPError as exc:
        raw_err = f"HTTP {exc.code}: {exc.reason}"
        try:
            body_err = exc.read().decode("utf-8")
            if body_err:
                raw_err = f"{raw_err} - {body_err[:300]}"
        except Exception:
            pass
        safe_err = redact_secrets(raw_err, secrets)
        logger.warning("AI Provider HTTPError for %s: %s", redact_secrets(url, secrets), safe_err)
        return None, exc.code, safe_err
    except urllib.error.URLError as exc:
        raw_err = f"URL Error: {exc.reason}"
        safe_err = redact_secrets(raw_err, secrets)
        logger.warning("AI Provider URLError for %s: %s", redact_secrets(url, secrets), safe_err)
        return None, 0, safe_err
    except Exception as exc:
        raw_err = str(exc)
        safe_err = redact_secrets(raw_err, secrets)
        logger.warning("AI Provider request failed for %s: %s", redact_secrets(url, secrets), safe_err)
        return None, 0, safe_err
