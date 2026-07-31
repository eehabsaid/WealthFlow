# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""
Backward compatibility shim for core.views.auth_views.
Re-exports all authentication views, mixins, and helpers from core.authentication.views.
"""

from core.authentication.views import (
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
]
