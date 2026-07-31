"""
Authentication helper utilities.
"""

from core.models import AppSettings, AuthAuditLog
from core.constants import PAGE_PERMISSION_KEYS

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
        "email_verified": profile.email_verified,
        "account_status": profile.account_status,
    }

def get_user_allowed_pages(user):
    """Returns allowed page permission keys for the specified user."""
    if user.is_staff or user.is_superuser:
        return PAGE_PERMISSION_KEYS
    return [perm.page for perm in user.page_permissions.all()]

def request_lang(request):
    """Extracts active language from request POST/GET parameters, cookies, or AppSettings."""
    return (
        request.POST.get("lang", "").strip()
        or request.GET.get("lang", "").strip()
        or request.COOKIES.get("wf_lang", "").strip()
        or AppSettings.get("active_language", "en")
        or "en"
    )

def record_audit(user, event_type: str, actor=None, details: str = "") -> None:
    """Records an authentication audit log entry."""
    AuthAuditLog.objects.create(user=user, actor=actor, event_type=event_type, details=details)
