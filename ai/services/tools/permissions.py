"""Read / Execute / Modify permission tiers for AI tool execution (backlog
item 7). Each tier includes every tool allowed by the tiers below it:
- read:    look at data, never changes anything (the vast majority of
           today's tools: query_application_data, read_live_app_structure,
           read_application_codebase, compare_scenarios, summarize_report,
           explain_chart, suggest_optimizations, suggest_app_feature)
- execute: runs a computation/action with no persisted side effect (no tool
           uses this tier yet — reserved for a future e.g. "run_what_if"
           that computes but doesn't save; exists so new tools have
           somewhere to declare themselves other than jumping straight to
           full write access)
- modify:  creates/updates/deletes the user's persisted data
           (create_scenario today)

Kept alongside, not replacing, the original ai_read_only boolean setting —
existing code/tests that read/write ai_read_only directly must keep working
unchanged. ai_permission_tier is the new, more expressive setting; when it
hasn't been explicitly set, it's derived from ai_read_only so upgraded
installs default to their previous behavior exactly (read_only=true -> tier
"read", read_only=false -> tier "modify" — the only two states that boolean
could ever represent, since "execute" didn't exist as a concept before).
"""

from __future__ import annotations

from core.models import AppSettings

TIER_READ = "read"
TIER_EXECUTE = "execute"
TIER_MODIFY = "modify"
TIER_ORDER = (TIER_READ, TIER_EXECUTE, TIER_MODIFY)
VALID_TIERS = frozenset(TIER_ORDER)


def normalize_tier(value: str | None) -> str:
    """Unknown/missing input -> the safest tier, "read"."""
    v = str(value or "").strip().lower()
    return v if v in VALID_TIERS else TIER_READ


def tier_index(tier: str) -> int:
    return TIER_ORDER.index(normalize_tier(tier))


def tool_allowed_at_tier(tool_tier: str, granted_tier: str) -> bool:
    """True if a tool declared at tool_tier may run under granted_tier."""
    return tier_index(tool_tier) <= tier_index(granted_tier)


def tool_tier(tool_def: dict) -> str:
    """A tool's own required tier. Prefers the explicit "tier" key; falls
    back to deriving one from the older is_read_only flag so a tool
    definition that hasn't been updated yet still gets a sane tier."""
    explicit = tool_def.get("tier")
    if explicit:
        return normalize_tier(explicit)
    return TIER_READ if tool_def.get("is_read_only", True) else TIER_MODIFY


def resolve_granted_tier(user=None) -> str:
    """The tier currently granted to the AI by settings. Reads
    ai_permission_tier if explicitly set; otherwise derives it from the
    legacy ai_read_only boolean (see module docstring)."""
    explicit = AppSettings.get("ai_permission_tier", "", user=user).strip().lower()
    if explicit in VALID_TIERS:
        return explicit
    read_only_str = AppSettings.get("ai_read_only", "true", user=user).strip().lower()
    read_only = read_only_str in ("true", "1", "yes")
    return TIER_READ if read_only else TIER_MODIFY


def resolve_tier_and_read_only_from_post(data: dict) -> tuple[str, bool, str | None]:
    """Given raw settings-POST data, returns (permission_tier, read_only, error).
    error is None on success. Used by ai_settings_save_helpers.py to keep the
    new tiered field and the legacy boolean consistent with each other (see
    module docstring)."""
    permission_tier_raw = data.get("ai_permission_tier")
    if permission_tier_raw is not None:
        tier = str(permission_tier_raw).strip().lower()
        if tier not in VALID_TIERS:
            return tier, True, f"Invalid ai_permission_tier '{tier}'. Must be one of {sorted(VALID_TIERS)}"
        return tier, tier == TIER_READ, None
    read_only = bool(data.get("ai_read_only", True))
    return (TIER_READ if read_only else TIER_MODIFY), read_only, None
