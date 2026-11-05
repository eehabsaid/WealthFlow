"""Minimal JSON-over-HTTP POST (stdlib only) with retry on transient errors and credential redaction in every error message."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from .base import ProviderError, redact

TRANSIENT = (408, 429, 500, 502, 503, 504)


def post_json(url: str, headers: dict, body: dict, timeout: int, secrets=(), retries: int = 2, backoff: float = 1.0) -> dict:
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **headers}, method="POST")
    last = "unknown error"
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last = f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:500]}"
            if exc.code not in TRANSIENT:
                break
        except ValueError:
            last = "provider returned invalid JSON"
            break
        except OSError as exc:   # URLError, timeouts, connection resets
            last = f"cannot reach the provider: {exc}"
        if attempt < retries:
            time.sleep(backoff * (attempt + 1))
    raise ProviderError(redact(last, secrets))
