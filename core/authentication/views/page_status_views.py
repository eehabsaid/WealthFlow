from django.contrib.auth import logout
from django.shortcuts import redirect

from core.authentication.views.helpers import _render_auth_status


def check_email_view(request):
    return _render_auth_status(
        request,
        title_key="auth_check_email_title",
        message_key="auth_signup_success_verify_email",
        tone="info",
        cta_href="/accounts/login/",
        cta_key="auth_login_button",
    )


def account_disabled_view(request):
    return _render_auth_status(
        request,
        title_key="auth_account_disabled_title",
        message_key="auth_status_disabled",
        tone="danger",
        cta_href="/accounts/login/",
        cta_key="auth_login_button",
    )


def logout_view(request):
    logout(request)
    return redirect("/accounts/login/")
