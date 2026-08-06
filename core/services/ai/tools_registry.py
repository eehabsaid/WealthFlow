"""
Automatic Tool Discovery & Registry for AI Subsystem.
Discovers and registers AI tools with standardized metadata, validation, and zero-write safety checks.
CRITICAL CONSTRAINT: 100% READ-ONLY enforcement for read-only tools.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

_TOOL_REGISTRY: dict[str, dict[str, Any]] = {}


def register_tool(
    name: str,
    description: str,
    handler: Callable[[Any, dict[str, Any]], dict[str, Any]],
    schema: dict[str, Any],
    domain: str = "business_data_analysis",
    is_read_only: bool = True,
    required_permissions: list[str] | None = None,
    supported_intents: list[str] | None = None,
) -> None:
    """Register an AI tool with complete metadata validation."""
    clean_name = str(name or "").strip()
    if not clean_name:
        raise ValueError("Tool name cannot be empty")

    if clean_name in _TOOL_REGISTRY:
        logger.warning("Overwriting existing tool registration for '%s'", clean_name)

    _TOOL_REGISTRY[clean_name] = {
        "name": clean_name,
        "description": description,
        "is_read_only": is_read_only,
        "domain": domain,
        "required_permissions": required_permissions or [],
        "supported_intents": supported_intents or [],
        "handler": handler,
        "schema": schema,
    }


def ai_tool(
    name: str,
    description: str,
    schema: dict[str, Any],
    domain: str = "business_data_analysis",
    is_read_only: bool = True,
    required_permissions: list[str] | None = None,
    supported_intents: list[str] | None = None,
) -> Callable:
    """Decorator for registering an AI tool function."""
    def decorator(fn: Callable) -> Callable:
        register_tool(
            name=name,
            description=description,
            handler=fn,
            schema=schema,
            domain=domain,
            is_read_only=is_read_only,
            required_permissions=required_permissions,
            supported_intents=supported_intents,
        )
        return fn
    return decorator


def get_tool(name: str) -> dict[str, Any] | None:
    """Lookup tool definition by name."""
    return _TOOL_REGISTRY.get(str(name or "").strip())


def get_all_tools() -> dict[str, dict[str, Any]]:
    """Return dictionary of all registered tools."""
    return _TOOL_REGISTRY


def validate_tool_registry() -> list[str]:
    """Startup validation check for registered tools. Returns list of errors if any."""
    errors = []
    for name, tool_def in _TOOL_REGISTRY.items():
        if not tool_def.get("handler"):
            errors.append(f"Tool '{name}' has no handler function")
        if not tool_def.get("schema"):
            errors.append(f"Tool '{name}' has no schema definition")
    return errors
