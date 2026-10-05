"""Sysadmin-only: default and per-user monthly AI token limits (/api/settings/ai/user-limits/).

Limits apply only to users on the general AI settings; the response also reports each user's mode and usage."""

import json

from django.contrib.auth import get_user_model
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views import View

from core.constants.ai_user_settings import DEFAULT_LIMIT_KEY, USER_LIMIT_KEY
from core.models import AppSettings
from core.services.ai.usage import effective_limit, used_tokens, uses_general_settings
from core.validators.json_body import parse_json_body
from core.views.auth_views import AdminRequiredMixin

User = get_user_model()


def _parse_limit(raw):
    """'' / None -> None (inherit); non-negative int -> int; anything else -> ValueError."""
    if raw is None or str(raw).strip() == "":
        return None
    value = int(str(raw).strip())
    if value < 0:
        raise ValueError("negative")
    return value


class AIUserLimitsView(AdminRequiredMixin, View):
    def get(self, request):
        q = request.GET.get("q", "").strip()
        page = int(request.GET.get("page", 1) or 1)
        qs = User.objects.order_by("username")
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q))
        paginator = Paginator(qs, 25)
        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        rows = []
        for u in page_obj.object_list:
            own = AppSettings.objects.filter(key=USER_LIMIT_KEY, owner=u).values_list("value", flat=True).first()
            general = uses_general_settings(u)
            rows.append({
                "id": u.id, "username": u.username, "use_general": general,
                "limit_override": own if own is not None else "",
                "effective_limit": effective_limit(u) if general else 0,
                "used": used_tokens(u),
            })
        return JsonResponse({
            "default_limit": AppSettings.get(DEFAULT_LIMIT_KEY, "0"),
            "users": rows, "page": page_obj.number, "num_pages": paginator.num_pages, "total": paginator.count,
        })

    def post(self, request):
        try:
            data = parse_json_body(request)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)
        try:
            if "default_limit" in data:
                AppSettings.set(DEFAULT_LIMIT_KEY, str(_parse_limit(data["default_limit"]) or 0))
            if "user_id" in data:
                target = User.objects.filter(pk=data["user_id"]).first()
                if target is None:
                    return JsonResponse({"error": "User not found"}, status=404)
                value = _parse_limit(data.get("limit"))
                if value is None:
                    AppSettings.objects.filter(key=USER_LIMIT_KEY, owner=target).delete()
                else:
                    AppSettings.set(USER_LIMIT_KEY, str(value), user=target)
        except (ValueError, TypeError):
            return JsonResponse({"error": "Limit must be a non-negative whole number of tokens", "error_key": "ai_limit_invalid"}, status=400)
        return JsonResponse({"ok": True})
