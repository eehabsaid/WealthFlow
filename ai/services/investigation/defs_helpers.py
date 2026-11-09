"""Shared builders for the investigator tool definitions (split out so defs.py and defs_agent.py stay under 200 lines)."""

from __future__ import annotations

from typing import Any

DOMAIN = "app_investigation"


def tool(name: str, description: str, handler, properties: dict, required: list | None = None) -> dict[str, Any]:
    return {
        "name": name, "description": description, "is_read_only": True, "tier": "read", "domain": DOMAIN,
        "investigator_only": True, "handler": lambda user, params: handler(user, params),
        "schema": {"type": "function", "function": {
            "name": name, "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required or []}}},
    }


S, I, B, O, A = ({"type": t} for t in ("string", "integer", "boolean", "object", "array"))


def p(spec: dict, description: str) -> dict:
    return {**spec, "description": description}
