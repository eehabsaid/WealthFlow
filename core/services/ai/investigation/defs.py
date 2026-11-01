"""AI_TOOL_REGISTRY entries for the investigator (all read tier). Merged in core/services/ai/tools/defs.py.

`investigator_only` keeps them out of the default chat path's tool list (smaller prompts there); the investigator asks
for them with domain="app_investigation" via investigation_tool_schemas(user), which hides the code tools from
everyone except the sysadmin.
"""

from __future__ import annotations

from typing import Any

from . import code_tools as ct
from . import data_tools as dt
from .defs_agent import AGENT_TOOL_DEFS
from .defs_helpers import A as _A, B as _B, DOMAIN, I as _I, O as _O, S as _S, p as _p, tool as _tool
from .knowledge_tool import knowledge_search
from core.services.ai.coding import tools as coding

__all__ = ["CODE_TOOLS", "DOMAIN", "INVESTIGATION_TOOL_DEFS", "investigation_tool_schemas"]
CODE_TOOLS = ("app_list_dir", "app_find_files", "app_grep", "app_find_definition", "app_read_file",
              "app_callers", "app_git_history", "app_trace_feature",
              "app_coding_context", "app_plan_files", "app_repo_index")   # sysadmin only (see code_tools.code_access_allowed)


INVESTIGATION_TOOL_DEFS: dict[str, dict[str, Any]] = {t["name"]: t for t in (
    _tool("app_list_dir", "List a folder of the WealthFlow source tree (path relative to the project root, '' = root).",
          ct.list_dir, {"path": _p(_S, "e.g. 'core/services/billing'")}),
    _tool("app_find_files", "Find source files by name: wildcard ('*balance*.py') or plain substring ('expense_service').",
          ct.find_files, {"pattern": _p(_S, "file name pattern"), "path": _p(_S, "optional folder to limit the search")},
          ["pattern"]),
    _tool("app_grep", "Search the source code for text or a regex; returns file, line and the matching line.",
          ct.grep, {"pattern": _p(_S, "regex or plain text"), "path": _p(_S, "optional folder"),
                    "file_glob": _p(_S, "comma list, default *.py,*.js,*.html,*.css,*.json,*.md"),
                    "ignore_case": _p(_B, "default true"), "max_results": _p(_I, "default 40, max 100"),
                    "context": _p(_I, "lines of context around each match, 0-3")}, ["pattern"]),
    _tool("app_find_definition", "Find where a function, class or JS global is defined (file and line).",
          ct.find_definition, {"symbol": _p(_S, "e.g. ExpenseService or initCollapsibleTables")}, ["symbol"]),
    _tool("app_read_file", "Read a source file with line numbers (max ~220 lines per call; call again for the next lines).",
          ct.read_file, {"path": _p(_S, "file path from app_find_files / app_grep"), "start_line": _p(_I, "default 1"),
                         "end_line": _p(_I, "default start+119")}, ["path"]),
    _tool("app_knowledge_search", "Search the app's documentation: what each page does, how data flows, where things are recorded.",
          knowledge_search, {"query": _p(_S, "natural-language question or keywords")}, ["query"]),
    _tool("app_data_models", "List the user's data tables with complete field names and row counts, or describe one table's field types and "
          "foreign-key target fields (model=Name). Use the canonical model names returned here.",
          dt.models, {"model": _p(_S, "optional table name, e.g. Expense, FixedAsset, SalaryEntry")}),
    _tool("app_data_query",
          "Read the CURRENT USER's own data. Use exact model and field names from app_data_models. Foreign-key fields take IDs; "
          "filter/group by related labels or codes with paths such as currency__code__iexact='EGP' or bank__name__icontains='QNB'. "
          "For Expense, amount_base is the base-currency value and amount is the transaction-currency value. "
          "BankCertificate.interest_value is distinct from posted BankCertificateInterestHistory.interest_amount. "
          "Aggregate keys are only count, sum, avg, min, max; use sum for totals instead of adding rows. "
          "For duplicate checks, group by all identity fields and "
          "filter groups with having such as {\"count__gt\":1}.",
          dt.query, {"model": _p(_S, "table name from app_data_models"), "filters": _p(_O, "{field__lookup: value}; lookups: "
                     "exact iexact contains icontains startswith gt gte lt lte in isnull range year month day; use relation__field for FK text"),
                     "fields": _p(_A, "columns to return (default: first 14)"), "order_by": _p(_A, "e.g. ['-date']"),
                     "limit": _p(_I, "rows, default 25, max 100"),
                     "aggregate": _p(_O, "only count, sum, avg, min, max; e.g. {\"sum\":\"amount_base\",\"count\":\"*\"}"),
                     "group_by": _p(_S, "one field or comma-separated fields, e.g. category__name or date,amount_base,category"),
                     "having": _p(_O, "optional aggregate filter after grouping, e.g. {\"count__gt\":1}")}, ["model"]),
)}

INVESTIGATION_TOOL_DEFS.update(AGENT_TOOL_DEFS)
INVESTIGATION_TOOL_DEFS.update({t["name"]: t for t in (
    _tool("app_coding_context", "For a coding task: the project skills, past decisions and files that matter, cut to a size. Call it first.",
          coding.coding_context, {"task": _p(_S, "the task in a sentence"), "max_chars": _p(_I, "size limit, default 6000")}, ["task"]),
    _tool("app_plan_files", "Before proposing a change: for the files you would change, which are protected (need the owner's approval), who calls them, "
          "which tests cover them and their line counts.", coding.plan_files, {"files": _p(_A, "repo-relative paths")}, ["files"]),
    _tool("app_repo_index", "Search the auto-built repo index by file, class, function, model or route name; callers=true lists who imports it.",
          coding.repo_index, {"query": _p(_S, "name part"), "callers": _p(_B, "also list files that import it")}, ["query"]),
)})


def investigation_tool_schemas(user, domain: str = "") -> list[dict[str, Any]]:
    """Tool schemas offered to the investigator for `user` (code tools only when code access is allowed). In the Business domain
    only the tools that read the user's own data; in the App domain everything except them (see core/services/ai/domains.py)."""
    from core.services.ai.domains import APP, BUSINESS, DATA_TOOLS

    from core.services.ai.exports.settings import exports_enabled
    from core.services.ai.exports.tool import TOOL_DEF as file_tool

    code_ok = ct.code_access_allowed(user)
    def allowed(name: str) -> bool:
        if domain == BUSINESS:
            return name in DATA_TOOLS
        return (code_ok or name not in CODE_TOOLS) and not (domain == APP and name in DATA_TOOLS)

    schemas = [d["schema"] for n, d in INVESTIGATION_TOOL_DEFS.items() if allowed(n)]
    from core.services.ai.memory.commands import MEMORY_TOOL_DEFS

    return schemas + ([file_tool["schema"]] if exports_enabled() else []) + [d["schema"] for d in MEMORY_TOOL_DEFS.values()]
