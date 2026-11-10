"""Access mixins for AI views; the rules come from the host via ai.host."""
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import JsonResponse

from ai.host import user_has_permission, user_is_sysadmin


class _JsonDenied(UserPassesTestMixin):
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
        return JsonResponse({"error": "Admin access required"}, status=403)


class SysadminRequiredMixin(_JsonDenied):
    def test_func(self):
        return self.request.user.is_authenticated and user_is_sysadmin(self.request.user)


class AdminRequiredMixin(SysadminRequiredMixin):
    """Alias kept for the existing views."""


class PermissionRequiredMixin(_JsonDenied):
    required_key = None

    def test_func(self):
        return user_has_permission(self.request.user, self.required_key)
