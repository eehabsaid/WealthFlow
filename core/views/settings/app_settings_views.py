# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""NOTE: single-resource file. If it grows past ~200 lines, split it and
move the resulting files into a settings/<domain>/ subfolder (see
settings/ai/ or settings/gold/ for the pattern: an empty __init__.py plus
one file per concern), then update core/views/settings/__init__.py."""


import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction

from core.models import AppSettings


@method_decorator(csrf_exempt, name="dispatch")
class SettingsView(View):
    def get(self, request):
        settings = AppSettings.objects.all()
        return JsonResponse({"settings": {s.key: s.value for s in settings}})

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
                obj = AppSettings.set(key, val_str)
                saved[obj.key] = obj.value

        if isinstance(data, dict) and "key" in data and "value" in data and len(items) == 1 and "settings" not in data:
            return JsonResponse({"key": items[0][0], "value": saved.get(items[0][0], "")})

        return JsonResponse({"status": "ok", "settings": saved})
