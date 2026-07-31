# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
import datetime
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.shortcuts import render, redirect
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models import UserProfile
from core.authentication.services import AuthWorkflowService
from core.authentication.utils import (
    build_user_dict as _build_user_dict,
    get_user_allowed_pages as _get_user_allowed_pages,
    request_lang as _request_lang,
)

User = get_user_model()

class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
        return JsonResponse({"error": "Admin access required"}, status=403)

def _render_auth(request, template_name, extra_context=None):
    context = {"lang_code": _request_lang(request)}
    if extra_context:
        context.update(extra_context)
    response = render(request, template_name, context)
    response.set_cookie("wf_lang", context["lang_code"], max_age=31536000, samesite="Lax")
    return response

def _render_auth_status(request, *, title_key, message_key, tone="info", cta_href="", cta_key=""):
    return _render_auth(
        request,
        "auth_status.html",
        {
            "title_key": title_key,
            "message_key": message_key,
            "tone": tone,
            "cta_href": cta_href,
            "cta_key": cta_key,
        },
    )

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        lang = _request_lang(request)
        user_for_status = User.objects.filter(username=username).first()
        if user_for_status is not None:
            block_key = AuthWorkflowService.get_login_block(user_for_status)
            if block_key != "auth_error_invalid_login":
                return _render_auth(request, "login.html", {"error_key": block_key, "prefill_username": username})
        user = authenticate(request, username=username, password=password)
        if user is not None:
            profile = AuthWorkflowService.get_profile(user)
            profile.preferred_language = lang
            profile.save(update_fields=["preferred_language", "updated_at"])
            login(request, user)
            response = redirect("/")
            response.set_cookie("wf_lang", lang, max_age=31536000, samesite="Lax")
            return response
        return _render_auth(request, "login.html", {"error_key": "auth_error_invalid_login", "prefill_username": username})
    return _render_auth(request, "login.html")

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
            return _render_auth(request, "signup.html", context)

        context["error_key"] = result.error_key
        if result.extra:
            context.update(result.extra)
        return _render_auth(request, "signup.html", context)

    return _render_auth(request, "signup.html")

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
            "forgot_password.html",
            {
                "success_key": result.message_key if result.ok else "",
                "error_key": result.error_key if not result.ok else "",
                "prefill_email": identifier.strip(),
            },
        )
    return _render_auth(request, "forgot_password.html", {"prefill_email": request.GET.get("email", "").strip()})

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
        return _render_auth(request, "reset_password.html", {"reset_token": token})

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
        return _render_auth(request, "reset_password.html", {"error_key": result.error_key, "reset_token": token})
    return _render_auth(request, "reset_password.html", {"reset_token": token})

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

class LoginAPIView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        data = json.loads(
            request.body.decode("utf-8")
            if isinstance(request.body, bytes)
            else request.body
        )
        username = data.get("username", "").strip()
        password = data.get("password", "")
        user_for_status = User.objects.filter(username=username).first()
        if user_for_status is not None:
            block_key = AuthWorkflowService.get_login_block(user_for_status)
            if block_key != "auth_error_invalid_login":
                return JsonResponse({"error_key": block_key, "error": block_key}, status=400)
        user = authenticate(request, username=username, password=password)
        if user is None:
            return JsonResponse({"error_key": "auth_error_invalid_login", "error": "auth_error_invalid_login"}, status=400)
        profile = AuthWorkflowService.get_profile(user)
        profile.preferred_language = str(data.get("lang", "") or profile.preferred_language or "en")
        profile.save(update_fields=["preferred_language", "updated_at"])
        login(request, user)
        return JsonResponse(
            {
                "user": _build_user_dict(user, profile),
                "allowed_pages": _get_user_allowed_pages(user),
            }
        )

class SignupAPIView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        data = json.loads(
            request.body.decode("utf-8")
            if isinstance(request.body, bytes)
            else request.body
        )
        result = AuthWorkflowService.register_user(
            request,
            username=data.get("username", ""),
            email=data.get("email", ""),
            password=data.get("password", ""),
            confirm_password=data.get("confirm_password", ""),
            full_name=data.get("full_name", ""),
            lang=str(data.get("lang", "") or "en"),
        )
        if not result.ok:
            payload = {"error_key": result.error_key, "error": result.error_key}
            if result.extra:
                payload.update(result.extra)
            return JsonResponse(payload, status=400)
        return JsonResponse({"message_key": result.message_key}, status=201)

class LogoutAPIView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        logout(request)
        return JsonResponse({"success": True})

class CurrentUserView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"user": None, "allowed_pages": []})
        profile = AuthWorkflowService.get_profile(request.user)
        return JsonResponse(
            {
                "user": _build_user_dict(request.user, profile),
                "allowed_pages": _get_user_allowed_pages(request.user),
            }
        )

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Auto-create a UserProfile whenever a new User is created."""
    if created:
        UserProfile.objects.get_or_create(user=instance)

@method_decorator(csrf_exempt, name="dispatch")
class UpdateProfileView(View):
    """
    GET  /api/auth/profile/          — get current user profile
    POST /api/auth/profile/          — update full_name / bio / birthday
    POST /api/auth/profile/avatar/   — upload profile picture (multipart)
    """

    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Not authenticated"}, status=401)
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return JsonResponse(
            {"profile": profile.to_dict(), "user": _build_user_dict(request.user, profile)}
        )

    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Not authenticated"}, status=401)
        profile, _ = UserProfile.objects.get_or_create(user=request.user)

        if request.FILES.get("avatar"):
            import base64 as _b64

            f = request.FILES["avatar"]
            mime_type = f.content_type or "image/jpeg"
            raw_bytes = f.read()
            try:
                from PIL import Image
                import io as _io

                img = Image.open(_io.BytesIO(raw_bytes))
                img.thumbnail((256, 256), Image.LANCZOS)
                buf = _io.BytesIO()
                fmt = "JPEG" if "jpeg" in mime_type or "jpg" in mime_type else "PNG"
                img.save(buf, format=fmt, quality=85)
                raw_bytes = buf.getvalue()
                mime_type = "image/jpeg" if fmt == "JPEG" else "image/png"
            except Exception:
                pass
            b64_str = _b64.b64encode(raw_bytes).decode("utf-8")
            profile.avatar_b64 = f"data:{mime_type};base64,{b64_str}"
            profile.save()
            return JsonResponse(
                {"avatar_url": profile.avatar_url(), "message": "Avatar updated"}
            )

        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        if "full_name" in data:
            profile.full_name = data["full_name"].strip()
            parts = profile.full_name.split(" ", 1)
            request.user.first_name = parts[0]
            request.user.last_name = parts[1] if len(parts) > 1 else ""
            request.user.save(update_fields=["first_name", "last_name"])
        if "bio" in data:
            profile.bio = data["bio"]
        if "birthday" in data:
            raw_birthday = data.get("birthday")
            if raw_birthday in (None, ""):
                profile.birthday = None
            elif isinstance(raw_birthday, str):
                try:
                    parsed_birthday = datetime.date.fromisoformat(raw_birthday.strip())
                except ValueError:
                    return JsonResponse({"error": "Invalid birthday format. Use YYYY-MM-DD."}, status=400)
                if parsed_birthday > timezone.localdate():
                    return JsonResponse({"error": "Birthday cannot be in the future."}, status=400)
                profile.birthday = parsed_birthday
            else:
                return JsonResponse({"error": "Invalid birthday format. Use YYYY-MM-DD."}, status=400)

        profile.save()
        return JsonResponse(
            {"profile": profile.to_dict(), "user": _build_user_dict(request.user, profile)}
        )
