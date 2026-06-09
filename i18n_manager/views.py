import json
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


I18N_DIR = Path(settings.BASE_DIR) / "static" / "i18n"


def get_translations(request):
    with open(I18N_DIR / "en.json", "r", encoding="utf-8") as f:
        en = json.load(f)

    with open(I18N_DIR / "ar.json", "r", encoding="utf-8") as f:
        ar = json.load(f)

    return JsonResponse({
        "en": en,
        "ar": ar
    })


@csrf_exempt
def save_translations(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    data = json.loads(request.body)

    with open(I18N_DIR / "en.json", "w", encoding="utf-8") as f:
        json.dump(data["en"], f, ensure_ascii=False, indent=2)

    with open(I18N_DIR / "ar.json", "w", encoding="utf-8") as f:
        json.dump(data["ar"], f, ensure_ascii=False, indent=2)

    return JsonResponse({"success": True})