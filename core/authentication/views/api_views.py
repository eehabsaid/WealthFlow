import datetime
import json

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from core.models import UserProfile
from core.authentication.services import AuthWorkflowService
from core.authentication.utils import (
    build_user_dict as _build_user_dict,
    get_user_allowed_pages as _get_user_allowed_pages,
)

User = get_user_model()


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
