"""
AI Tool Registry — merges the split registry-definition dicts.

NOTE (200-line file convention): part of the ai/services/tools/
package. Definitions live in defs_scenario.py and defs_app.py; this module
merges them (plus the investigator tools from ai/services/investigation/) into the single public AI_TOOL_REGISTRY and exposes
get_registered_tool_schemas.
"""

from __future__ import annotations

from typing import Any

from ai.services.tools.defs_app import APP_TOOL_DEFS
from ai.services.exports.tool import NAME as FILE_TOOL_NAME, TOOL_DEF as FILE_TOOL_DEF
from ai.services.image_generation.tool import NAME as IMAGE_TOOL_NAME, TOOL_DEF as IMAGE_TOOL_DEF
from ai.services.investigation.defs import INVESTIGATION_TOOL_DEFS
from ai.services.memory.commands import MEMORY_TOOL_DEFS

AI_TOOL_REGISTRY: dict[str, dict[str, Any]] = {**APP_TOOL_DEFS, **INVESTIGATION_TOOL_DEFS, FILE_TOOL_NAME: FILE_TOOL_DEF, **MEMORY_TOOL_DEFS,
                                          IMAGE_TOOL_NAME: IMAGE_TOOL_DEF}


def get_registered_tool_schemas(domain: str | None = None) -> list[dict[str, Any]]:
    """Returns list of registered tool schemas in Ollama function-calling format, filtered by domain if specified."""
    schemas = []
    for tool_def in AI_TOOL_REGISTRY.values():
        if tool_def.get("offer_all_domains"):   # memory tools (read / save / forget): offered on every domain
            schemas.append(tool_def["schema"])
            continue
        if tool_def.get("offer_if"):   # generate_image: offered on every domain only while it is enabled and configured
            if tool_def["offer_if"]():
                schemas.append(tool_def["schema"])
            continue
        if tool_def.get("offer_always"):   # generate_file: offered on every domain while file generation is enabled
            from ai.services.exports.settings import exports_enabled

            if exports_enabled():
                schemas.append(tool_def["schema"])
            continue
        if domain and tool_def.get("domain") != domain:
            continue
        if tool_def.get("investigator_only") and domain != "app_investigation":
            continue  # investigator tools are offered by the investigator only (smaller default prompts)
        schemas.append(tool_def["schema"])
    return schemas
