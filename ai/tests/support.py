"""Host-neutral test helpers: the same ai tests run in any Django project.

A host may provide ``AI_TEST_SUPPORT = "path.to.module"`` with optional ``make_sysadmin(user)`` and
``grant_ai_workspace_access(user)``. Without it, a sysadmin is a superuser and no plan gate exists.
"""
from django.conf import settings
from django.utils.module_loading import import_string


def _host(name):
    path = getattr(settings, "AI_TEST_SUPPORT", None)
    if not path:
        return None
    try:
        return import_string(f"{path}.{name}")
    except ImportError:
        return None


def make_sysadmin(user):
    """Make `user` pass the AI app's sysadmin check (default: superuser)."""
    hook = _host("make_sysadmin")
    if hook:
        return hook(user)
    user.is_superuser = True
    user.is_staff = True
    user.save()
    return user


def grant_ai_workspace_access(user):
    """Let `user` through the host's plan gate for the AI workspace (no-op without a gate)."""
    hook = _host("grant_ai_workspace_access")
    return hook(user) if hook else None
