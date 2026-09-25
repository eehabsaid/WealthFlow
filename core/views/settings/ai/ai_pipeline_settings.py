"""AI chat pipeline settings (ai_validate_mode, ai_pipeline_debug): get / validate / persist.

Kept separate from ai_settings_get_helpers / ai_settings_save_helpers (200-line rule).
Stored app-wide like the other AI settings; read by chat_pipeline.validate / runner.
"""

from django.http import JsonResponse

from core.models import AppSettings

VALIDATE_MODES = ("off", "flag", "regenerate")
DEFAULT_VALIDATE_MODE = "flag"
_TRUE = ("true", "1", "yes")


def get_pipeline_settings(user=None) -> dict:
    mode = str(AppSettings.get("ai_validate_mode", DEFAULT_VALIDATE_MODE, user=user) or "").strip().lower()
    debug = str(AppSettings.get("ai_pipeline_debug", "false", user=user) or "").strip().lower()
    return {
        "ai_validate_mode": mode if mode in VALIDATE_MODES else DEFAULT_VALIDATE_MODE,
        "ai_pipeline_debug": debug in _TRUE,
    }


def validate_pipeline_settings(data):
    """Returns (validated, error_response). Missing keys fall back to current stored values."""
    current = get_pipeline_settings(user=None)
    mode = str(data.get("ai_validate_mode", current["ai_validate_mode"])).strip().lower()
    if mode not in VALIDATE_MODES:
        return None, JsonResponse(
            {"error": f"ai_validate_mode must be one of {list(VALIDATE_MODES)}"}, status=400
        )
    debug = data.get("ai_pipeline_debug", current["ai_pipeline_debug"])
    if isinstance(debug, str):
        debug = debug.strip().lower() in _TRUE
    return {"validate_mode": mode, "pipeline_debug": bool(debug)}, None


def persist_pipeline_settings(validated, user=None) -> None:
    AppSettings.set("ai_validate_mode", validated["validate_mode"], user=user)
    AppSettings.set("ai_pipeline_debug", "true" if validated["pipeline_debug"] else "false", user=user)
