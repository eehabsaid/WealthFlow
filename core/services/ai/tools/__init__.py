"""
Umbrella re-export for the AI tool subsystem, so callers can do
`from core.services.ai.tools import X` without needing to know which
sibling file X lives in.

STRUCTURE / CONVENTION — read this before adding or splitting a file:
  - scenario.py           handlers: create/compare scenario, reports, optimizations
  - app_structure.py      live Django routes + Playwright DOM crawl
  - data_codebase.py      business-data query, feature suggestion, codebase inspection
  - defs_scenario.py      AI_TOOL_REGISTRY entries (scenario/report/optimization group)
  - defs_app.py           AI_TOOL_REGISTRY entries (app structure/codebase group)
  - defs.py               merges the two dicts into AI_TOOL_REGISTRY + get_registered_tool_schemas
  - validation_rules.py   per-tool parameter validation rules
  - execution.py          validate_and_execute_tool orchestrator
  - Whenever ANY file in this package grows past ~200 lines, split it
    further and update this __init__.py's imports/__all__ to match — this
    file is the single place external code depends on (`from
    core.services.ai.tools import ...`), so no other file needs to change
    when this package is reorganized internally.
  - This is the standard pattern for any future 200+ line split in this
    codebase: a package folder (tools/) with an __init__.py as the single
    re-export source, not a flat tools_*.py naming scheme. See
    core/views/settings/__init__.py for the sibling convention this
    mirrors.
"""

from __future__ import annotations

__all__ = [
    "AI_TOOL_REGISTRY",
    "get_registered_tool_schemas",
    "validate_and_execute_tool",
    "_get_live_django_routes",
    "_crawl_live_pages_with_playwright",
    "_handle_read_live_app_structure",
    "_handle_query_application_data",
    "_handle_suggest_app_feature",
    "_handle_read_application_codebase",
    "_handle_create_scenario",
    "_handle_compare_scenarios",
    "_handle_summarize_report",
    "_handle_explain_chart",
    "_handle_suggest_optimizations",
]

# Re-exported for backward-compatible public API.
from core.services.ai.tools.defs import (  # noqa: F401
    AI_TOOL_REGISTRY,
    get_registered_tool_schemas,
)
from core.services.ai.tools.execution import validate_and_execute_tool  # noqa: F401

# Re-exported: imported directly (or patched in tests) as
# core.services.ai.tools._crawl_live_pages_with_playwright /
# core.services.ai.tools.<handler_name> elsewhere in the codebase.
from core.services.ai.tools.app_structure import (  # noqa: F401
    _get_live_django_routes,
    _crawl_live_pages_with_playwright,
)
from core.services.ai.tools.data_codebase import (  # noqa: F401
    _handle_read_live_app_structure,
    _handle_query_application_data,
    _handle_suggest_app_feature,
    _handle_read_application_codebase,
)
from core.services.ai.tools.scenario import (  # noqa: F401
    _handle_create_scenario,
    _handle_compare_scenarios,
    _handle_summarize_report,
    _handle_explain_chart,
    _handle_suggest_optimizations,
)
