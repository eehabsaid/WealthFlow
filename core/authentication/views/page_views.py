import json

from django.contrib.auth import authenticate, get_user_model, login
from django.http import JsonResponse
from django.shortcuts import redirect

from core.authentication.services import AuthWorkflowService
from core.authentication.utils import request_lang as _request_lang
from core.authentication.views.helpers import _render_auth, _render_auth_status

User = get_user_model()


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        lang = _request_lang(request)
        user_for_status = User.objects.filter(username=username).first()
        if user_for_status is not None:
            block_key = AuthWorkflowService.get_login_block(user_for_status)
            if block_key != "auth_error_invalid_login":
                return _render_auth(request, "authentication/login.html", {"error_key": block_key, "prefill_username": username})
        user = authenticate(request, username=username, password=password)
        if user is not None:
            profile = AuthWorkflowService.get_profile(user)
            profile.preferred_language = lang
            profile.save(update_fields=["preferred_language", "updated_at"])
            login(request, user)
            response = redirect("/")
            response.set_cookie("wf_lang", lang, max_age=31536000, samesite="Lax")
            return response
        return _render_auth(request, "authentication/login.html", {"error_key": "auth_error_invalid_login", "prefill_username": username})
    return _render_auth(request, "authentication/login.html")


def signup_view(request):
    if request.method == "POST":
        result = AuthWorkflowService.register_user(
            request,
            username=request.POST.get("username", ""),
            email=request.POST.get("email", ""),
            password=request.POST.get("password", ""),
            confirm_password=request.POST.get("confirm_password", ""),
            full_name=request.POST.get("full_name", ""),
            lang=_request_lang(request),
        )
        context = {
            "prefill_username": request.POST.get("username", "").strip(),
            "prefill_email": request.POST.get("email", "").strip(),
            "prefill_full_name": request.POST.get("full_name", "").strip(),
        }
        if result.ok:
            context["success_key"] = result.message_key
            return _render_auth(request, "authentication/signup.html", context)

        context["error_key"] = result.error_key
        if result.extra:
            context.update(result.extra)
        return _render_auth(request, "authentication/signup.html", context)

    return _render_auth(request, "authentication/signup.html")


def forgot_password_view(request):
    if request.method == "POST":
        if request.content_type == "application/json":
            data = json.loads(request.body.decode("utf-8") if isinstance(request.body, bytes) else request.body)
            identifier = data.get("email", "") or data.get("identifier", "")
        else:
            identifier = request.POST.get("email", "") or request.POST.get("identifier", "")
        result = AuthWorkflowService.request_password_reset(request, identifier=identifier, lang=_request_lang(request))
        if request.path.startswith("/api/"):
            status_code = 200 if result.ok else 400
            payload = {"message_key": result.message_key} if result.ok else {"error_key": result.error_key, "error": result.error_key}
            return JsonResponse(payload, status=status_code)
        return _render_auth(
            request,
            "authentication/forgot_password.html",
            {
                "success_key": result.message_key if result.ok else "",
                "error_key": result.error_key if not result.ok else "",
                "prefill_email": identifier.strip(),
            },
        )
    return _render_auth(request, "authentication/forgot_password.html", {"prefill_email": request.GET.get("email", "").strip()})


def reset_password_view(request, token):
    if request.method == "GET":
        resolved_token, error_key = AuthWorkflowService.resolve_token(token, "password_reset")
        if resolved_token is None:
            return _render_auth_status(
                request,
                title_key="auth_reset_password_heading",
                message_key=error_key,
                tone="danger",
                cta_href="/accounts/forgot-password/",
                cta_key="auth_forgot_password_button",
            )
        return _render_auth(request, "authentication/reset_password.html", {"reset_token": token})

    if request.method == "POST":
        result = AuthWorkflowService.reset_password(
            token,
            password=request.POST.get("password", ""),
            confirm_password=request.POST.get("confirm_password", ""),
        )
        if result.ok:
            return _render_auth_status(
                request,
                title_key="auth_reset_password_heading",
                message_key=result.message_key,
                tone="success",
                cta_href="/accounts/login/",
                cta_key="auth_login_button",
            )
        return _render_auth(request, "authentication/reset_password.html", {"error_key": result.error_key, "reset_token": token})
    return _render_auth(request, "authentication/reset_password.html", {"reset_token": token})


def verify_email_view(request, token):
    result = AuthWorkflowService.verify_email(request, token)
    if result.ok:
        return _render_auth_status(
            request,
            title_key="auth_verify_email_title",
            message_key=result.message_key,
            tone="success",
            cta_href="/accounts/pending-approval/",
            cta_key="auth_pending_approval_cta",
        )
    return _render_auth_status(
        request,
        title_key="auth_verify_email_title",
        message_key=result.error_key,
        tone="danger",
        cta_href="/accounts/login/",
        cta_key="auth_login_button",
    )
