"""'Restore my account': cancel a scheduled deletion during the grace period (the account is disabled, so login is blocked)."""

from django.contrib.auth import get_user_model
from django.core.cache import cache

from core.authentication.services import AuthWorkflowService
from core.authentication.views.helpers import _render_auth, _render_auth_status
from core.services.account import restore_needs_admin, restore_user

User = get_user_model()

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 15 * 60


def _client_ip(request) -> str:
    return request.META.get("REMOTE_ADDR", "")


def _throttle_key(username: str, request) -> str:
    return f"restore-attempts:{username.lower()}:{_client_ip(request)}"


def restore_account_view(request):
    """GET: form. POST {username, password}: restore when the password is right and a deletion is pending."""
    if request.method != "POST":
        return _render_auth(request, "authentication/restore_account.html", {"prefill_username": request.GET.get("username", "").strip()})
    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "")
    ctx = {"prefill_username": username}
    key = _throttle_key(username, request)
    if cache.get(key, 0) >= MAX_ATTEMPTS:
        return _render_auth(request, "authentication/restore_account.html", {**ctx, "error_key": "auth_restore_too_many"})
    user = User.objects.filter(username=username).first()
    profile = AuthWorkflowService.get_profile(user) if user else None
    if not user or not profile.deletion_requested_at or not user.check_password(password):
        cache.set(key, cache.get(key, 0) + 1, WINDOW_SECONDS)
        return _render_auth(request, "authentication/restore_account.html", {**ctx, "error_key": "auth_restore_invalid"})
    cache.delete(key)
    if restore_needs_admin(user):
        return _render_auth(request, "authentication/restore_account.html", {**ctx, "error_key": "auth_restore_needs_admin"})
    restore_user(user, actor=user)
    return _render_auth_status(
        request, title_key="auth_restore_heading", message_key="auth_restore_done", tone="success", cta_href="/accounts/login/", cta_key="auth_login_button"
    )
