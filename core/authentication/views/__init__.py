"""
core/authentication/views package.

Sibling modules:
- mixins.py       — AdminRequiredMixin
- helpers.py       — _render_auth, _render_auth_status
- page_views.py        — template-rendering auth views (login/signup/forgot/reset/verify)
- page_status_views.py — status-page views (pending/rejected/disabled/admin-approve/
                           admin-reject) and logout_view
- api_views.py     — JSON API views (LoginAPIView, SignupAPIView, LogoutAPIView,
                       CurrentUserView, UpdateProfileView)
- signals.py       — create_user_profile (post_save signal handler)

This file re-exports the public surface so external callers can keep importing
from core.authentication.views.
"""

from core.authentication.views.mixins import AdminRequiredMixin
from core.authentication.views.helpers import _render_auth, _render_auth_status
from core.authentication.views.page_views import (
    login_view,
    signup_view,
    forgot_password_view,
    reset_password_view,
    verify_email_view,
)
from core.authentication.views.page_status_views import (
    pending_approval_view,
    account_rejected_view,
    account_disabled_view,
    admin_approve_account_view,
    admin_reject_account_view,
    logout_view,
)
from core.authentication.views.api_views import (
    LoginAPIView,
    SignupAPIView,
    LogoutAPIView,
    CurrentUserView,
    UpdateProfileView,
)
from core.authentication.views.signals import create_user_profile
from core.authentication.utils import (
    build_user_dict as _build_user_dict,
    get_user_allowed_pages as _get_user_allowed_pages,
    request_lang as _request_lang,
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
