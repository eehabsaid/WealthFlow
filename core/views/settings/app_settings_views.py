# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""NOTE: single-resource file. If it grows past ~200 lines, split it and
move the resulting files into a settings/<domain>/ subfolder (see
settings/ai/ or settings/gold/ for the pattern: an empty __init__.py plus
one file per concern), then update core/views/settings/__init__.py.

Some keys here are per-user (see USER_SCOPED_SETTING_KEYS), some are
platform-global (everything else — SMTP, available_languages, etc.).
active_language is a further special case, backed by
UserProfile.preferred_language rather than a per-user AppSettings row."""


import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction

from core.models import AppSettings
from core.constants.user_scoped_settings import USER_SCOPED_SETTING_KEYS, ACTIVE_LANGUAGE_KEY


def _resolve_for_user(request):
    """Global rows, overlaid with the current user's own rows for
    user-scoped keys, overlaid with their preferred_language for the
    active_language special case."""
    user = request.user if request.user.is_authenticated else None
    qs = AppSettings.objects.filter(owner=None)
    resolved = {s.key: s.value for s in qs}
    if user is not None:
        own = AppSettings.objects.filter(owner=user, key__in=USER_SCOPED_SETTING_KEYS)
        resolved.update({s.key: s.value for s in own})
        from core.authentication.services import AuthWorkflowService

        profile = AuthWorkflowService.get_profile(user)
        if profile.preferred_language:
            resolved[ACTIVE_LANGUAGE_KEY] = profile.preferred_language
    return resolved


@method_decorator(csrf_exempt, name="dispatch")
class SettingsView(View):
    def get(self, request):
        return JsonResponse({"settings": _resolve_for_user(request)})

    def post(self, request):
        data = json.loads(request.body or "{}")
        items = []

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "key" in item and "value" in item:
                    items.append((str(item["key"]), item["value"]))
        elif isinstance(data, dict):
            if "settings" in data:
                raw_settings = data["settings"]
                if isinstance(raw_settings, dict):
                    for k, v in raw_settings.items():
                        items.append((str(k), v))
                elif isinstance(raw_settings, list):
                    for item in raw_settings:
                        if isinstance(item, dict) and "key" in item and "value" in item:
                            items.append((str(item["key"]), item["value"]))
            elif "key" in data and "value" in data:
                items.append((str(data["key"]), data["value"]))
            else:
                for k, v in data.items():
                    items.append((str(k), v))

        if not items:
            return JsonResponse({"error": "No settings provided"}, status=400)

        user = request.user if request.user.is_authenticated else None
        saved = {}
        with transaction.atomic():
            for key, val in items:
                val_str = (
                    val
                    if isinstance(val, str)
                    else json.dumps(val)
                    if isinstance(val, (dict, list))
                    else str(val)
                    if val is not None
                    else ""
                )
                if key == ACTIVE_LANGUAGE_KEY and user is not None:
                    from core.authentication.services import AuthWorkflowService

                    profile = AuthWorkflowService.get_profile(user)
                    profile.preferred_language = val_str
                    profile.save(update_fields=["preferred_language"])
                    saved[key] = val_str
                    continue
                scoped_user = user if (user is not None and key in USER_SCOPED_SETTING_KEYS) else None
                obj = AppSettings.set(key, val_str, user=scoped_user)
                saved[obj.key] = obj.value

        if isinstance(data, dict) and "key" in data and "value" in data and len(items) == 1 and "settings" not in data:
            return JsonResponse({"key": items[0][0], "value": saved.get(items[0][0], "")})

        return JsonResponse({"status": "ok", "settings": saved})
