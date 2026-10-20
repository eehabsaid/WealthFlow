"""Chat domains the sysadmin allows (Settings > AI Advisor > Chat domains).

Two domains exist: "business_data_analysis" (the user's own data) and "app_features_architecture" (how the app is built and
works). Both are on by default; at least one always stays on. With both on the workspace offers the choice; with one on the chat
has no choice and the server forces that domain whatever the browser sends."""

from __future__ import annotations

from core.models import AppSettings

BUSINESS = "business_data_analysis"
APP = "app_features_architecture"
KEYS = {BUSINESS: "ai_domain_business", APP: "ai_domain_app"}
DATA_TOOLS = ("app_data_models", "app_data_query", "app_computed_figures")   # the investigator's tools that read the user's data
_OFF = ("false", "0", "no", "off")


def is_on(domain: str) -> bool:
    return str(AppSettings.get(KEYS[domain], "true", user=None) or "true").strip().lower() not in _OFF


def enabled_domains() -> tuple[str, ...]:
    on = tuple(d for d in (BUSINESS, APP) if is_on(d))
    return on or (BUSINESS, APP)   # never none: a chat without a domain cannot answer


def app_enabled() -> bool:
    return APP in enabled_domains()


def resolve_domain(requested: str = "") -> str:
    """The domain a question runs in: the requested one when allowed, the only allowed one otherwise, \"\" (infer) when both are
    allowed and none was chosen."""
    allowed, wanted = enabled_domains(), str(requested or "").strip()
    if wanted in allowed:
        return wanted
    return allowed[0] if len(allowed) == 1 else ""
