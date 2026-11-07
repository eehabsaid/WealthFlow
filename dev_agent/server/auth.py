"""Who may talk to the local server. Bearer token (constant-time compare), exact Host and Origin checks (stops DNS rebinding and cross-site pages)."""

from __future__ import annotations

import hmac
import secrets

LOCAL_NAMES = ("127.0.0.1", "localhost")


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_ok(expected: str, header: str | None) -> bool:
    if not expected or not header or not header.startswith("Bearer "):
        return False
    return hmac.compare_digest(header[7:].strip().encode("utf-8"), expected.encode("utf-8"))


def host_ok(host: str | None, port: int) -> bool:
    return bool(host) and host.lower() in {f"{name}:{port}" for name in LOCAL_NAMES}


def origin_ok(origin: str | None, fetch_site: str | None, port: int) -> bool:
    """No Origin (the extension, curl, the CLI) is fine; a browser must come from this very server."""
    if fetch_site and fetch_site.lower() not in ("same-origin", "none"):
        return False
    return origin is None or origin.lower() in {f"http://{name}:{port}" for name in LOCAL_NAMES}
