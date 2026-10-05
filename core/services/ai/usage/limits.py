"""Monthly AI token usage and the sysadmin-set limit.

Unit: tokens (prompt + completion) per calendar month, summed from the assistant AIMessage rows the chat
view stamps with the request's token totals. The limit applies ONLY to users on the general AI settings;
users on their own settings are never limited.
"""

from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from core.constants.ai_user_settings import DEFAULT_LIMIT_KEY, USE_GENERAL_KEY, USER_LIMIT_KEY
from core.models import AIMessage, AppSettings


def uses_general_settings(user) -> bool:
    flag = AppSettings.objects.filter(key=USE_GENERAL_KEY, owner=user).values_list("value", flat=True).first()
    return str(flag if flag is not None else "true").strip().lower() not in ("false", "0", "no")


def _as_int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def effective_limit(user) -> int:
    """0 = unlimited. Per-user row wins (blank/absent = inherit the default, "0" = unlimited for this user)."""
    own = AppSettings.objects.filter(key=USER_LIMIT_KEY, owner=user).values_list("value", flat=True).first()
    own_val = _as_int(own) if own is not None else None
    if own_val is not None:
        return max(own_val, 0)
    default = _as_int(AppSettings.get(DEFAULT_LIMIT_KEY, "0"))
    return max(default or 0, 0)


def month_start():
    now = timezone.localtime()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def used_tokens(user) -> int:
    agg = AIMessage.objects.filter(
        conversation__user=user, role="assistant", created_at__gte=month_start()
    ).aggregate(p=Coalesce(Sum("prompt_tokens"), 0), c=Coalesce(Sum("completion_tokens"), 0))
    return int(agg["p"] or 0) + int(agg["c"] or 0)


def limit_status(user) -> dict:
    general = uses_general_settings(user)
    limit = effective_limit(user) if general else 0
    used = used_tokens(user)
    return {
        "use_general": general,
        "limit": limit,
        "used": used,
        "limited": bool(general and limit > 0),
        "exceeded": bool(general and limit > 0 and used >= limit),
    }
