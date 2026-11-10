import os
import json
from django.conf import settings

from ai.doc_engine.config import CANCEL_FILE, DOCS_DIR, GENERATED_DIR, RUNTIME_DIR, SCREENSHOTS_DIR, STATUS_FILE   # one source of truth: the engine's folders

__all__ = ["BASE_DIR", "CANCEL_FILE", "DOCS_DIR", "GENERATED_DIR", "HISTORY_FILE", "RUNTIME_DIR", "SCREENSHOTS_DIR", "STATUS_FILE", "read_json_file", "write_json_file"]

BASE_DIR = settings.BASE_DIR
HISTORY_FILE = os.path.join(GENERATED_DIR, "history.json")


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
