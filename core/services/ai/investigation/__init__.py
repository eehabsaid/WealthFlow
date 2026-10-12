"""AI investigator: read-only tools (source code, owner-scoped business data, documentation) and the ReAct loop that
lets the local model explore the whole app on its own instead of answering "I don't have that tool/data".

  paths.py          safe repo access + secret redaction
  code_tools.py     list/find/grep/definition/read (sysadmin only)
  scope.py          which tables are queryable and how each is isolated by owner
  data_tools.py     app_data_models / app_data_query
  knowledge_tool.py app_knowledge_search
  defs.py           AI_TOOL_REGISTRY entries (merged in core/services/ai/tools/defs.py)
  refusal.py        detects "I can't / don't have access" answers (en/ar/fr/de)
  prompt.py         system prompt
  actions.py        tool-call extraction (native, text JSON)
  loop.py           the investigation loop
"""

from .defs import DOMAIN, INVESTIGATION_TOOL_DEFS, investigation_tool_schemas

__all__ = ["DOMAIN", "INVESTIGATION_TOOL_DEFS", "investigation_tool_schemas"]
