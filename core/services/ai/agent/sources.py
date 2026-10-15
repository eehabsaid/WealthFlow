"""Sources for an Agent answer, built ONLY from the tool calls that really ran (never from what the model says it used).

Returns the coarse keys the app already stores (investigation_code / _data / _docs) plus one entry per real read:
  agent:code:<path>:<start>-<end>   agent:data:<Model>   agent:figures:<capability>   agent:docs:<query>
  agent:app:<route or term>         agent:git:<path>
"""

from __future__ import annotations

from core.services.ai.investigation.defs import CODE_TOOLS

_MAX_REFS = 30


def _arg(args: dict, *names: str) -> str:
    for name in names:
        if args.get(name):
            return str(args[name])[:80]
    return ""


def _ref(tool: str, args: dict) -> str:
    if tool == "app_read_file":
        start = int(args.get("start_line") or 1)
        end = int(args.get("end_line") or start + 119)
        return f"agent:code:{_arg(args, 'path')}:{start}-{end}"
    if tool in ("app_grep", "app_find_files", "app_find_definition", "app_callers", "app_list_dir"):
        return f"agent:code:{tool.removeprefix('app_')}:{_arg(args, 'pattern', 'symbol', 'path') or '/'}"
    if tool == "app_git_history":
        return f"agent:git:{_arg(args, 'path')}"
    if tool in ("app_data_query", "app_data_models"):
        return f"agent:data:{_arg(args, 'model') or 'tables'}"
    if tool == "app_computed_figures":
        return f"agent:figures:{_arg(args, 'question')}"
    if tool == "app_knowledge_search":
        return f"agent:docs:{_arg(args, 'query')}"
    if tool in ("app_routes", "app_i18n_search", "app_trace_feature"):
        return f"agent:app:{_arg(args, 'query', 'term', 'feature')}"
    return f"agent:{tool}"


def build_sources(steps: list) -> list[str]:
    """`steps` = audit records of the executed tool calls (only successful ones count as a source)."""
    ok = [s for s in steps if s.get("status") == "success"]
    tools = {s.get("tool", "") for s in ok}
    keys = []
    if tools & (set(CODE_TOOLS) | {"app_callers", "app_git_history", "app_trace_feature"}):
        keys.append("investigation_code")
    if tools & {"app_data_models", "app_data_query", "app_computed_figures"}:
        keys.append("investigation_data")
    if tools & {"app_knowledge_search", "app_routes", "app_i18n_search"}:
        keys.append("investigation_docs")
    refs = []
    for step in ok:
        ref = _ref(step.get("tool", ""), step.get("arguments") or {})
        if ref not in refs:
            refs.append(ref)
    return (keys or ["investigation"]) + refs[:_MAX_REFS]
