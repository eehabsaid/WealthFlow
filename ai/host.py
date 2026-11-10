"""Host adapter: everything ai/ needs from the project it is installed in.

Each hook is a dotted path in Django settings; unset hooks fall back to a safe
default that needs nothing from the host. See ai/INSTALL.md.

  AI_SYSADMIN_CHECK   callable(user) -> bool        default: user.is_superuser
  AI_PERMISSION_CHECK callable(user, key) -> bool   default: any authenticated user
  AI_AUDIT_HOOK       callable(user, event, actor=None, details="")  default: log line
  AI_FEATURE_GATE     callable(flag) -> view decorator               default: no gate
  AI_BASE_CURRENCY    callable(user) -> str         default: "USD"
  AI_DEFAULT_CURRENCY callable() -> str             default: "USD"
  AI_EXCHANGE_RATE    callable(from_code, to_code) -> float|None   default: no conversion
"""
import logging
from functools import wraps

from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger("ai.host")


def _hook(name):
    path = getattr(settings, name, None)
    return import_string(path) if path else None


def user_is_sysadmin(user) -> bool:
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    hook = _hook("AI_SYSADMIN_CHECK")
    return bool(hook(user)) if hook else bool(getattr(user, "is_superuser", False))


def user_has_permission(user, key) -> bool:
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if user_is_sysadmin(user):
        return True
    hook = _hook("AI_PERMISSION_CHECK")
    return bool(hook(user, key)) if hook else True


def record_audit(user, event_type, actor=None, details="") -> None:
    hook = _hook("AI_AUDIT_HOOK")
    if hook:
        hook(user, event_type, actor=actor, details=details)
    else:
        logger.info("audit %s user=%s actor=%s %s", event_type, getattr(user, "pk", None),
                    getattr(actor, "pk", None), details)


def feature_required(flag):
    """View decorator; the host may gate AI features per plan, default is open."""
    gate = _hook("AI_FEATURE_GATE")
    if gate:
        return gate(flag)

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def base_currency(user) -> str:
    hook = _hook("AI_BASE_CURRENCY")
    return str(hook(user)) if hook else "USD"


def default_currency() -> str:
    hook = _hook("AI_DEFAULT_CURRENCY")
    return str(hook()) if hook else "USD"


def exchange_rate(from_code, to_code):
    """Rate to multiply an amount in from_code by to get to_code, or None when unknown."""
    hook = _hook("AI_EXCHANGE_RATE")
    return hook(from_code, to_code) if hook else None
