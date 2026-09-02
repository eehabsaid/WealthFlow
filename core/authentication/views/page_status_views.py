from django.contrib.auth import logout
from django.shortcuts import redirect

from core.authentication.services import AuthWorkflowService
from core.authentication.views.helpers import _render_auth_status


def pending_approval_view(request):
    return _render_auth_status(
        request,
        title_key="auth_pending_approval_title",
        message_key="auth_status_pending_admin_approval",
        tone="info",
        cta_href="/accounts/login/",
        cta_key="auth_login_button",
    )


def account_rejected_view(request):
    return _render_auth_status(
        request,
        title_key="auth_account_rejected_title",
        message_key="auth_status_rejected",
        tone="danger",
        cta_href="/accounts/forgot-password/",
        cta_key="auth_forgot_password_button",
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


def admin_approve_account_view(request, token):
    result = AuthWorkflowService.approve_user(token, actor=request.user if request.user.is_authenticated else None)
    return _render_auth_status(
        request,
        title_key="auth_admin_approval_title",
        message_key=result.message_key if result.ok else result.error_key,
        tone="success" if result.ok else "danger",
        cta_href="/accounts/login/",
        cta_key="auth_login_button",
    )


def admin_reject_account_view(request, token):
    result = AuthWorkflowService.reject_user(token, actor=request.user if request.user.is_authenticated else None)
    return _render_auth_status(
        request,
        title_key="auth_admin_rejection_title",
        message_key=result.message_key if result.ok else result.error_key,
        tone="danger" if result.ok else "danger",
        cta_href="/accounts/login/",
        cta_key="auth_login_button",
    )


def logout_view(request):
    logout(request)
    return redirect("/accounts/login/")
