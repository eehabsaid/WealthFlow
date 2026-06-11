import json
from pathlib import Path
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import re


I18N_DIR = Path(settings.BASE_DIR) / "static" / "i18n"


def get_translations(request):
    translations = {}

    for file in I18N_DIR.glob("*.json"):
        lang_code = file.stem

        try:
            with open(file, "r", encoding="utf-8") as f:
                translations[lang_code] = json.load(f)
        except Exception:
            translations[lang_code] = {}

    return JsonResponse(translations)

def scan_translations(request):
    project_root = Path(settings.BASE_DIR)

    used_keys = set()

    patterns = [
        re.compile(r"\bt\(\s*['\"]([a-zA-Z0-9_\-]+)['\"]"),
        re.compile(r'data-i18n=["\']([a-zA-Z0-9_\-]+)["\']')
    ]

    scan_dirs = [
        project_root / "static" / "js",
        project_root / "templates"
    ]

    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue

        for file in scan_dir.rglob("*"):
            if file.suffix.lower() not in [".js", ".html"]:
                continue

            try:
                content = file.read_text(encoding="utf-8")
            except Exception:
                continue

            for pattern in patterns:
                matches = pattern.findall(content)
                used_keys.update(matches)
                used_keys = {
                    k for k in used_keys
                    if len(k) > 2
                    and k not in {"div", "tr", "td", "th", "span", "option"}
        }
    with open(I18N_DIR / "en.json", "r", encoding="utf-8") as f:
        en = json.load(f)

    with open(I18N_DIR / "ar.json", "r", encoding="utf-8") as f:
        ar = json.load(f)

    en_keys = {k for k in en.keys() if not k.startswith("__")}
    ar_keys = {k for k in ar.keys() if not k.startswith("__")}

    return JsonResponse({
        "found_keys": sorted(list(used_keys)),
        "missing_in_en": sorted(list(used_keys - en_keys)),
        "missing_in_ar": sorted(list(used_keys - ar_keys)),
        "unused_in_en": sorted(list(en_keys - used_keys)),
        "unused_in_ar": sorted(list(ar_keys - used_keys))
    })
@csrf_exempt
def save_translations(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    data = json.loads(request.body)

    for lang_code, content in data.items():
        with open(
            I18N_DIR / f"{lang_code}.json",
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                content,
                f,
                ensure_ascii=False,
                indent=2
            )

    return JsonResponse({"success": True})