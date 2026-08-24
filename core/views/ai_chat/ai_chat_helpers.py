import json
from django.http import JsonResponse
from core.models import AppSettings

# Maximum number of tool-call/response iterations per user message.
# Tunable: increase cautiously on GPU hardware, decrease if CPU latency is unacceptable.
MAX_TOOL_ITERATIONS = 8

# Total wall-clock budget (seconds) for the full investigation loop.
# Readable from AppSettings as "ai_total_loop_timeout"; defaults to 300s (5 minutes).
# This caps the worst-case (MAX_TOOL_ITERATIONS × per-call timeout) accumulation.
LOOP_TOTAL_TIMEOUT_SECONDS = 300

# Human-readable progress labels per registered tool, shown in the "thinking" bubble.
# {arg} is substituted from the tool's own call arguments when present.
TOOL_PROGRESS_LABELS = {
    "query_application_data": "Checking your data ({arg})",
    "read_application_codebase": "Reading codebase ({arg})",
    "read_live_app_structure": "Inspecting live app structure",
    "create_scenario": "Building scenario",
    "compare_scenarios": "Comparing scenarios",
    "summarize_report": "Summarizing report",
    "explain_chart": "Analyzing chart data",
    "suggest_optimizations": "Looking for optimizations",
    "suggest_app_feature": "Reviewing feature context",
}

# Which argument key to surface in {arg} for each tool, if any.
TOOL_PROGRESS_ARG_KEY = {
    "query_application_data": "search_query",
    "read_application_codebase": "search_term",
}


def _tool_progress_label(fn_name: str, fn_args: dict) -> str:
    """Builds a human-readable progress label for a tool call, e.g. 'Checking your data (companies)'."""
    template = TOOL_PROGRESS_LABELS.get(fn_name, fn_name.replace("_", " ").capitalize())
    arg_key = TOOL_PROGRESS_ARG_KEY.get(fn_name)
    if arg_key and "{arg}" in template:
        arg_val = str((fn_args or {}).get(arg_key, "")).strip()
        if arg_val:
            return template.format(arg=arg_val[:40])
        return template.split(" (")[0]
    return template

def _get_loop_timeout() -> int:
    """Read the total loop wall-clock budget from AppSettings with safe fallback."""
    try:
        return max(30, int(AppSettings.get("ai_total_loop_timeout", str(LOOP_TOTAL_TIMEOUT_SECONDS))))
    except (ValueError, TypeError):
        return LOOP_TOTAL_TIMEOUT_SECONDS

def _aiT_fallback_no_answer() -> str:
    """User-facing fallback text when the model returns no content and no tool
    call even after a retry nudge. Keeps the assistant message non-empty so the
    frontend always has something visible to render."""
    return (
        "I wasn't able to generate a response to that question. This can happen with "
        "smaller local models on complex requests — try rephrasing your question more "
        "specifically, or switch to a larger model in AI Advisor settings and try again."
    )

def _parse_tool_call(tc: dict) -> tuple[str, dict]:
    """Extract (fn_name, fn_args) from a raw tool_call dict. Returns ('', {}) on failure."""
    if not isinstance(tc, dict):
        return "", {}
    fn_info = tc.get("function", {}) if isinstance(tc.get("function"), dict) else {}
    fn_name = str(fn_info.get("name") or tc.get("name") or "").strip()
    fn_args = fn_info.get("arguments") or tc.get("arguments") or {}
    if isinstance(fn_args, str):
        try:
            fn_args = json.loads(fn_args)
        except Exception:
            fn_args = {}
    if not isinstance(fn_args, dict):
        fn_args = {}
    return fn_name, fn_args

def _fingerprint(fn_name: str, fn_args: dict) -> str:
    """Stable fingerprint of a (tool_name, arguments) pair for repeat-call detection."""
    return f"{fn_name}:{json.dumps(fn_args, sort_keys=True, default=str)}"

def _api_auth_required(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    return None
