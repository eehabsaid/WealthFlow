from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import JsonResponse

from core.authentication.utils.auth_utils import user_is_sysadmin, effective_permission_keys


class SysadminRequiredMixin(UserPassesTestMixin):
    """Hard-locked: only is_sysadmin passes, regardless of any role or
    override. Used for Roles management, User Management, and Billing
    Plans/Payment Gateway — see core/constants/roles.py."""

    def test_func(self):
        return self.request.user.is_authenticated and user_is_sysadmin(self.request.user)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
        return JsonResponse({"error": "Admin access required"}, status=403)


class AdminRequiredMixin(SysadminRequiredMixin):
    """Deprecated alias, kept so unmigrated views default to the strictest
    option (sysadmin-only) rather than silently losing their gate. New code
    should use SysadminRequiredMixin or PermissionRequiredMixin directly."""

    pass


class PermissionRequiredMixin(UserPassesTestMixin):
    """Delegable: passes for is_sysadmin, or any user whose role(s)/overrides
    grant `required_key` — see core.authentication.utils.auth_utils
    .effective_permission_keys(). Subclasses set `required_key`."""

    required_key = None

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user_is_sysadmin(user):
            return True
        return self.required_key in effective_permission_keys(user)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
        return JsonResponse({"error": "Admin access required"}, status=403)
