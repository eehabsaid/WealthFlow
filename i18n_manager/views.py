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
    prefixes = set()

    # Fully dynamic regex patterns to extract translations out of frontend assets
    patterns = [
        # 1. Matches JavaScript invocation blocks: _t('key') or t("key")
        re.compile(r"\b_?t\(\s*['\"]([a-zA-Z0-9_\-]+)['\"]"),
        
        # 2. Matches ANY attribute starting with data-i18n (e.g., data-i18n, data-i18n-title, data-i18n-postfix)
        re.compile(r'data-i18n(?:-[a-zA-Z0-9_\-]+)?=["\']([a-zA-Z0-9_\-]+)["\']'),
    ]
    
    # Extract dynamic translation prefixes (Framework #3: e.g., data-i18n-prefix="type_")
    prefix_pattern = re.compile(r'data-i18n-prefix=["\']([a-zA-Z0-9_\-]+)["\']')

    scan_dirs = [project_root / "static" / "js", project_root / "templates"]

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

            # Accumulate explicit language keys
            for pattern in patterns:
                used_keys.update(pattern.findall(content))
            
            # Accumulate formatting string prefixes
            prefixes.update(prefix_pattern.findall(content))

    # Strip native HTML elements captured accidentally due to template edge strings
    ignored_elements = {"div", "tr", "td", "th", "span", "option", "label", "input", "select"}
    used_keys = {k for k in used_keys if len(k) > 2 and k not in ignored_elements}

    # Dynamic translation dictionary auditing across ALL JSON translation profiles
    report = {}
    for file in I18N_DIR.glob("*.json"):
        lang_code = file.stem
        try:
            with open(file, "r", encoding="utf-8") as f:
                lang_dict = json.load(f)
        except Exception:
            continue
            
        lang_keys = {k for k in lang_dict.keys() if not k.startswith("__")}
        
        # Detect missing dictionary entries
        missing = sorted(list(used_keys - lang_keys))
        
        # Detect unused dictionary entries, excluding any managed via dynamic code prefixes
        unused = sorted([
            k for k in (lang_keys - used_keys) 
            if not any(k.startswith(p) for p in prefixes)
        ])
        
        report[lang_code] = {
            "missing": missing,
            "unused": unused
        }

    return JsonResponse({
        "found_static_keys": sorted(list(used_keys)),
        "active_prefixes_detected": sorted(list(prefixes)),
        "languages_telemetry": report
    })


@csrf_exempt
def save_translations(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    data = json.loads(request.body)
    for lang_code, content in data.items():
        with open(I18N_DIR / f"{lang_code}.json", "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)

    return JsonResponse({"success": True})