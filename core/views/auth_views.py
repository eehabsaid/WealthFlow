# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

import json
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from core.models import (
    AppSettings,
    PagePermission,
    PAGE_PERMISSION_CHOICES,
    UserProfile,

)
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q

import datetime
from core.services.shared.auth_workflow_service import AuthWorkflowService

User = get_user_model()
from core.constants import (
    PAGE_PERMISSION_KEYS,
)

from django.db.models.signals import post_save
from django.dispatch import receiver

class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
        return JsonResponse({"error": "Admin access required"}, status=403)

def _build_user_dict(user):
    profile = AuthWorkflowService.get_profile(user)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "email_verified": profile.email_verified,
        "account_status": profile.account_status,
    }

def _get_user_allowed_pages(user):
    if user.is_staff or user.is_superuser:
        return PAGE_PERMISSION_KEYS
    return [perm.page for perm in user.page_permissions.all()]

def _request_lang(request):
    return (
        request.POST.get("lang", "").strip()
        or request.GET.get("lang", "").strip()
        or request.COOKIES.get("wf_lang", "").strip()
        or AppSettings.get("active_language", "en")
        or "en"
    )

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
                "user": _build_user_dict(user),
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
        return JsonResponse(
            {
                "user": _build_user_dict(request.user),
                "allowed_pages": _get_user_allowed_pages(request.user),
            }
        )

class UserListView(AdminRequiredMixin, View):
    def get(self, request):
        # support pagination and search: ?page=1&page_size=20&q=term
        q = request.GET.get("q", "").strip()
        page = int(request.GET.get("page", 1) or 1)
        page_size = int(request.GET.get("page_size", 20) or 20)

        qs = User.objects.order_by("username").all()
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q))

        paginator = Paginator(qs, page_size)
        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        users = [_build_user_dict(u) for u in page_obj.object_list]
        return JsonResponse(
            {
                "users": users,
                "page": page_obj.number,
                "page_size": page_size,
                "total": paginator.count,
                "num_pages": paginator.num_pages,
            }
        )

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
        email = data.get("email", "").strip()
        password = data.get("password", "")
        if not username or not email or not password:
            return JsonResponse(
                {"error": "username, email and password are required"}, status=400
            )
        if User.objects.filter(username=username).exists():
            return JsonResponse({"error": "Username is already taken"}, status=400)
        user = User.objects.create_user(
            username=username, email=email, password=password
        )
        user.is_active = data.get("is_active", True)
        user.is_staff = data.get("is_staff", False)
        user.is_superuser = data.get("is_superuser", False)
        user.save()
        if user.is_active:
            AuthWorkflowService.enable_user(user, actor=request.user)
        else:
            AuthWorkflowService.disable_user(user, actor=request.user)
        return JsonResponse({"user": _build_user_dict(user)}, status=201)

class UserDetailView(AdminRequiredMixin, View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        return JsonResponse({"user": _build_user_dict(user)})

    def put(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        original_is_active = user.is_active
        data = json.loads(
            request.body.decode("utf-8")
            if isinstance(request.body, bytes)
            else request.body
        )
        for field in ["email", "is_active", "is_staff", "is_superuser"]:
            if field in data:
                setattr(user, field, data[field])
        if data.get("password"):
            user.set_password(data["password"])
        user.save()
        if "is_active" in data and data["is_active"] != original_is_active:
            if data["is_active"]:
                AuthWorkflowService.enable_user(user, actor=request.user)
            else:
                AuthWorkflowService.disable_user(user, actor=request.user)
        return JsonResponse({"user": _build_user_dict(user)})

    def delete(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.delete()
        return JsonResponse({"deleted": pk})

class UserPermissionListView(AdminRequiredMixin, View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        permissions = user.page_permissions.all()
        return JsonResponse(
            {
                "permissions": [perm.to_dict() for perm in permissions],
                "available_pages": PAGE_PERMISSION_CHOICES,
            }
        )

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        data = json.loads(
            request.body.decode("utf-8")
            if isinstance(request.body, bytes)
            else request.body
        )
        page = data.get("page")
        if page not in PAGE_PERMISSION_KEYS:
            return JsonResponse({"error": "Invalid page permission"}, status=400)
        perm, created = PagePermission.objects.get_or_create(user=user, page=page)
        return JsonResponse(
            {"permission": perm.to_dict()}, status=201 if created else 200
        )

class UserBulkActionView(AdminRequiredMixin, View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        data = json.loads(
            request.body.decode("utf-8")
            if isinstance(request.body, bytes)
            else request.body
        )
        action = data.get("action")
        ids = data.get("ids") or []
        if not action or not isinstance(ids, list):
            return JsonResponse({"error": "action and ids required"}, status=400)

        users = User.objects.filter(id__in=ids)
        changed = 0
        if action == "delete":
            changed = users.count()
            users.delete()
        elif action == "activate":
            changed = users.count()
            for user in users:
                AuthWorkflowService.enable_user(user, actor=request.user)
        elif action == "deactivate":
            changed = users.count()
            for user in users:
                AuthWorkflowService.disable_user(user, actor=request.user)
        elif action == "set_staff":
            val = bool(data.get("value"))
            changed = users.update(is_staff=val)
        elif action == "set_superuser":
            val = bool(data.get("value"))
            changed = users.update(is_superuser=val)
        else:
            return JsonResponse({"error": "unknown action"}, status=400)

        return JsonResponse({"changed": changed})

class UserPermissionDetailView(AdminRequiredMixin, View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, pk):
        perm = get_object_or_404(PagePermission, pk=pk)
        perm.delete()
        return JsonResponse({"deleted": pk})

class PagePermissionChoicesView(AdminRequiredMixin, View):
    def get(self, request):
        return JsonResponse({"available_pages": PAGE_PERMISSION_CHOICES})

@login_required(login_url="/accounts/login/")
def user_management_page(request):
    # Only staff (admins) can access the management UI
    if not request.user.is_staff:
        return redirect("/")
    return render(request, "user_management.html")

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
            {"profile": profile.to_dict(), "user": _build_user_dict(request.user)}
        )

    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Not authenticated"}, status=401)
        profile, _ = UserProfile.objects.get_or_create(user=request.user)

        # Handle avatar upload — store as base64 in DB (no file system)
        if request.FILES.get("avatar"):
            import base64 as _b64

            f = request.FILES["avatar"]
            mime_type = f.content_type or "image/jpeg"
            raw_bytes = f.read()
            # Resize to max 256x256 to keep DB size reasonable
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
                pass  # If Pillow not available, store full image
            b64_str = _b64.b64encode(raw_bytes).decode("utf-8")
            profile.avatar_b64 = f"data:{mime_type};base64,{b64_str}"
            profile.save()
            return JsonResponse(
                {"avatar_url": profile.avatar_url(), "message": "Avatar updated"}
            )

        # Handle JSON profile update
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        if "full_name" in data:
            profile.full_name = data["full_name"].strip()
            # Also update Django User first/last name
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
            {"profile": profile.to_dict(), "user": _build_user_dict(request.user)}
        )

# ── Excel Export View ──────────────────────────────────────────────────────────

