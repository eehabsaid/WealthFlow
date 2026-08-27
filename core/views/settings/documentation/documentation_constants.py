import os
import json
from django.conf import settings

BASE_DIR = settings.BASE_DIR
DOCS_DIR = os.path.join(BASE_DIR, "docs")
GENERATED_DIR = os.path.join(DOCS_DIR, "generated")
SCREENSHOTS_DIR = os.path.join(DOCS_DIR, "screenshots")
RUNTIME_DIR = os.path.join(GENERATED_DIR, "runtime")
HISTORY_FILE = os.path.join(GENERATED_DIR, "history.json")
STATUS_FILE = os.path.join(RUNTIME_DIR, "status.json")
CANCEL_FILE = os.path.join(RUNTIME_DIR, ".cancel_capture")


def read_json_file(filepath, default_value):
    if not os.path.exists(filepath):
        return default_value
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_value

def write_json_file(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
