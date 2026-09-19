"""
Authentication helper utilities.
"""

from core.models import AppSettings, AuthAuditLog
from core.constants.roles import grantable_permission_keys


def user_is_sysadmin(user):
    """The one unconditional, no-opt-in-needed access tier. Independent of
    Django's own is_staff/is_superuser — see core/constants/roles.py.

    Always fetches the profile fresh via AuthWorkflowService.get_profile()
    rather than `user.profile` — Django's reverse-cache for a OneToOne can
    hold a stale instance from an earlier get_or_create() on this same
    user object, which would silently mask a just-granted sysadmin flag."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    from core.authentication.services import AuthWorkflowService

    profile = AuthWorkflowService.get_profile(user)
    return bool(profile.is_sysadmin)


def effective_permission_keys(user):
    """Union of the user's role grants, with per-user overrides (PagePermission
    rows) applied on top — an override always wins, in either direction.
    Sysadmins get every grantable key without needing role/override rows."""
    if user is None or not getattr(user, "is_authenticated", False):
        return set()
    if user_is_sysadmin(user):
        return set(grantable_permission_keys())

    from core.models import RolePermission

    keys = set(
        RolePermission.objects.filter(role__user_roles__user=user).values_list(
            "key", flat=True
        )
    )
    for override in user.page_permissions.all():
        if override.granted:
            keys.add(override.page)
        else:
            keys.discard(override.page)
    return keys


def build_user_dict(user, profile=None):
    """Formats User and UserProfile into a standardized dictionary."""
    if profile is None:
        from core.authentication.services import AuthWorkflowService
        profile = AuthWorkflowService.get_profile(user)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "is_sysadmin": bool(profile.is_sysadmin),
        "email_verified": profile.email_verified,
        "account_status": profile.account_status,
        "roles": [ur.role.name for ur in user.roles.select_related("role").all()],
    }

def get_user_allowed_pages(user):
    """Returns the user's effective permission keys (main-app pages AND
    settings tabs, unified) as a list."""
    return list(effective_permission_keys(user))

def request_lang(request):
    """Extracts active language. Priority: explicit POST/GET param (a
    genuine one-off request override) > the authenticated user's own
    preferred_language > the wf_lang cookie (browser-scoped, so only
    trustworthy pre-auth) > the platform default > "en".

    The cookie is deliberately ranked below the authenticated profile:
    it's set on the anonymous login page and is per-browser, not
    per-account, so on a shared browser it must never outrank a known
    user's own stored preference — that ordering previously caused a
    flash of the wrong language on the very pages meant to reflect the
    account you just logged into."""
    explicit = request.POST.get("lang", "").strip() or request.GET.get("lang", "").strip()
    if explicit:
        return explicit

    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        from core.authentication.services import AuthWorkflowService

        profile = AuthWorkflowService.get_profile(user)
        if profile.preferred_language:
            return profile.preferred_language

    cookie_lang = request.COOKIES.get("wf_lang", "").strip()
    if cookie_lang:
        return cookie_lang

    return AppSettings.get("active_language", "en") or "en"

def record_audit(user, event_type: str, actor=None, details: str = "") -> None:
    """Records an authentication audit log entry."""
    AuthAuditLog.objects.create(user=user, actor=actor, event_type=event_type, details=details)
