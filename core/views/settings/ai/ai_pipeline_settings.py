"""AI chat pipeline settings (ai_validate_mode, ai_pipeline_debug, ai_direct_answers, ai_investigator_mode, ai_code_access, ai_file_generation + max size / max rows, Agent mode ai_agent_*): get / validate / persist.

Kept separate from ai_settings_get_helpers / ai_settings_save_helpers (200-line rule).
Stored app-wide like the other AI settings; read by chat_pipeline.validate / runner.
"""

from django.http import JsonResponse

from core.models import AppSettings
from core.services.ai.agent.settings import get_agent_settings, persist_agent_settings, validate_agent_settings
from core.services.ai.domains import KEYS as DOMAIN_KEYS, is_on as domain_is_on

VALIDATE_MODES = ("off", "flag", "regenerate")
DEFAULT_VALIDATE_MODE = "flag"
INVESTIGATOR_MODES = ("auto", "always", "off")   # chat_pipeline/investigate.py: auto = takes over when a normal answer gives up
FILE_LIMITS = {"ai_file_max_mb": (1, 50, 10), "ai_file_max_rows": (100, 200000, 50000)}   # min, max, default
_TRUE = ("true", "1", "yes")
_FALSE = ("false", "0", "no", "off")


def _clamped(raw, key) -> int:
    low, high, default = FILE_LIMITS[key]
    try:
        return max(low, min(high, int(float(str(raw)))))
    except ValueError:
        return default


def get_pipeline_settings(user=None) -> dict:
    mode = str(AppSettings.get("ai_validate_mode", DEFAULT_VALIDATE_MODE, user=user) or "").strip().lower()
    debug = str(AppSettings.get("ai_pipeline_debug", "false", user=user) or "").strip().lower()
    direct = str(AppSettings.get("ai_direct_answers", "true", user=user) or "true").strip().lower()
    inv = str(AppSettings.get("ai_investigator_mode", "auto", user=user) or "auto").strip().lower()
    code = str(AppSettings.get("ai_code_access", "true", user=None) or "true").strip().lower()   # global: a sysadmin security switch
    files = str(AppSettings.get("ai_file_generation", "true", user=None) or "true").strip().lower()   # global: sysadmin switch
    return {
        "ai_file_generation": files not in _FALSE,   # default ON: the AI can build Excel / Word / PDF / CSV / code files for the user
        **{key: _clamped(AppSettings.get(key, str(default), user=None), key) for key, (_, _, default) in FILE_LIMITS.items()},
        "ai_investigator_mode": inv if inv in INVESTIGATOR_MODES else "auto",
        "ai_code_access": code not in _FALSE,   # default ON; source-code tools are sysadmin-only either way
        "ai_validate_mode": mode if mode in VALIDATE_MODES else DEFAULT_VALIDATE_MODE,
        "ai_pipeline_debug": debug in _TRUE,
        **get_agent_settings(),   # Agent mode: switch, editable instructions (+ default text), step / time / read limits
        "ai_direct_answers": direct not in _FALSE,  # default ON; read by query_engine.is_enabled
        **{key: domain_is_on(domain) for domain, key in DOMAIN_KEYS.items()},   # Chat domains: business / data and app features / code
    }


def validate_pipeline_settings(data):
    """Returns (validated, error_response). Missing keys fall back to current stored values."""
    current = get_pipeline_settings(user=None)
    mode = str(data.get("ai_validate_mode", current["ai_validate_mode"])).strip().lower()
    if mode not in VALIDATE_MODES:
        return None, JsonResponse(
            {"error": f"ai_validate_mode must be one of {list(VALIDATE_MODES)}"}, status=400
        )
    inv = str(data.get("ai_investigator_mode", current["ai_investigator_mode"])).strip().lower()
    if inv not in INVESTIGATOR_MODES:
        return None, JsonResponse({"error": f"ai_investigator_mode must be one of {list(INVESTIGATOR_MODES)}"}, status=400)
    code = data.get("ai_code_access", current["ai_code_access"])
    if isinstance(code, str):
        code = code.strip().lower() not in _FALSE
    debug = data.get("ai_pipeline_debug", current["ai_pipeline_debug"])
    if isinstance(debug, str):
        debug = debug.strip().lower() in _TRUE
    direct = data.get("ai_direct_answers", current["ai_direct_answers"])
    if isinstance(direct, str):
        direct = direct.strip().lower() not in _FALSE
    files = data.get("ai_file_generation", current["ai_file_generation"])
    if isinstance(files, str):
        files = files.strip().lower() not in _FALSE
    limits = {}
    for key in FILE_LIMITS:
        raw = data.get(key, current[key])
        try:
            float(str(raw))
        except ValueError:
            return None, JsonResponse({"error": f"{key} must be a number"}, status=400)
        limits[key] = _clamped(raw, key)
    domains = {}
    for domain, key in DOMAIN_KEYS.items():
        value = data.get(key, current[key])
        domains[domain] = value.strip().lower() not in _FALSE if isinstance(value, str) else bool(value)
    if not any(domains.values()):
        return None, JsonResponse({"error": "At least one chat domain must stay enabled"}, status=400)
    agent, agent_error = validate_agent_settings(data, current)
    if agent_error:
        return None, JsonResponse({"error": agent_error}, status=400)
    return {"agent": agent, "file_generation": bool(files), "file_limits": limits, "validate_mode": mode, "pipeline_debug": bool(debug), "direct_answers": bool(direct),
            "investigator_mode": inv, "code_access": bool(code), "domains": domains}, None


def persist_pipeline_settings(validated, user=None) -> None:
    persist_agent_settings(validated["agent"])   # always global (sysadmin)
    AppSettings.set("ai_validate_mode", validated["validate_mode"], user=user)
    AppSettings.set("ai_pipeline_debug", "true" if validated["pipeline_debug"] else "false", user=user)
    AppSettings.set("ai_direct_answers", "true" if validated["direct_answers"] else "false", user=user)
    AppSettings.set("ai_investigator_mode", validated["investigator_mode"], user=user)
    AppSettings.set("ai_code_access", "true" if validated["code_access"] else "false", user=None)   # always global
    AppSettings.set("ai_file_generation", "true" if validated["file_generation"] else "false", user=None)   # always global
    for domain, key in DOMAIN_KEYS.items():
        AppSettings.set(key, "true" if validated["domains"][domain] else "false", user=None)   # always global (sysadmin)
    for key, value in validated["file_limits"].items():
        AppSettings.set(key, str(value), user=None)
