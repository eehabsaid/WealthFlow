"""
AI Tool Registry — merges the split registry-definition dicts.

NOTE (200-line file convention): part of the core/services/ai/tools/
package. Definitions live in defs_scenario.py and defs_app.py; this module
merges them into the single public AI_TOOL_REGISTRY and exposes
get_registered_tool_schemas.
"""

from __future__ import annotations

from typing import Any

from core.services.ai.tools.defs_scenario import SCENARIO_TOOL_DEFS
from core.services.ai.tools.defs_app import APP_TOOL_DEFS

AI_TOOL_REGISTRY: dict[str, dict[str, Any]] = {**SCENARIO_TOOL_DEFS, **APP_TOOL_DEFS}


def get_registered_tool_schemas(domain: str | None = None) -> list[dict[str, Any]]:
    """Returns list of registered tool schemas in Ollama function-calling format, filtered by domain if specified."""
    schemas = []
    for tool_def in AI_TOOL_REGISTRY.values():
        if domain and tool_def.get("domain") != domain:
            continue
        schemas.append(tool_def["schema"])
    return schemas
