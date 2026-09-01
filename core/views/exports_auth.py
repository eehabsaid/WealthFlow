"""Umbrella re-export for the Auth & User Identity domain, so
core/views/__init__.py can pull all of it via one import block instead
of ~30 separate lines. Covers login/signup/session views (auth_views.py)
plus the User & Permission management API (settings/user/), since both
back the same "who can access the app" concern.

Whenever auth_views.py or settings/user/ grows and adds/removes a
public name, update the imports/__all__ below to match — this file is
what core/views/__init__.py depends on, so no other file needs to
change when auth_views.py or settings/user/ is reorganized internally.
"""

from .auth_views import (
    AdminRequiredMixin,
    LoginAPIView,
    SignupAPIView,
    LogoutAPIView,
    CurrentUserView,
    UpdateProfileView,
    login_view,
    signup_view,
    forgot_password_view,
    reset_password_view,
    verify_email_view,
    pending_approval_view,
    account_rejected_view,
    account_disabled_view,
    admin_approve_account_view,
    admin_reject_account_view,
    logout_view,
    create_user_profile,
    _build_user_dict,
    _get_user_allowed_pages,
    _request_lang,
    _render_auth,
    _render_auth_status,
)
from .settings import (
    UserListView,
    UserDetailView,
    UserPermissionListView,
    UserBulkActionView,
    UserPermissionDetailView,
    PagePermissionChoicesView,
    user_management_page,
)

__all__ = [
    "AdminRequiredMixin",
    "LoginAPIView",
    "SignupAPIView",
    "LogoutAPIView",
    "CurrentUserView",
    "UpdateProfileView",
    "login_view",
    "signup_view",
    "forgot_password_view",
    "reset_password_view",
    "verify_email_view",
    "pending_approval_view",
    "account_rejected_view",
    "account_disabled_view",
    "admin_approve_account_view",
    "admin_reject_account_view",
    "logout_view",
    "create_user_profile",
    "_build_user_dict",
    "_get_user_allowed_pages",
    "_request_lang",
    "_render_auth",
    "_render_auth_status",
    "UserListView",
    "UserDetailView",
    "UserPermissionListView",
    "UserBulkActionView",
    "UserPermissionDetailView",
    "PagePermissionChoicesView",
    "user_management_page",
]
