"""coding_agent/config.json: protected files and the test area of each source folder. Editable text, no values in code."""

from __future__ import annotations

import fnmatch
import json

from ai.services.coding import AGENT_DIR

_DEFAULT = {"protected": [], "test_areas": {}, "max_file_lines": 200, "index_roots": None}   # None -> settings.AI_CODE_ROOTS


def load() -> dict:
    try:
        cfg = {**_DEFAULT, **json.loads((AGENT_DIR / "config.json").read_text(encoding="utf-8"))}
    except (OSError, ValueError):
        cfg = dict(_DEFAULT)
    if not cfg.get("index_roots"):
        from ai.conf import code_index_roots
        cfg["index_roots"] = code_index_roots()
    return cfg


def protected_reason(path: str) -> str:
    """Why `path` needs the owner's approval before any change, or '' when it is free to change."""
    norm = path.replace("\\", "/").lstrip("./")
    for rule in load()["protected"]:
        if fnmatch.fnmatch(norm, rule["pattern"]):
            return rule["reason"]
    return ""


def test_module(path: str) -> str:
    """The Django test package that covers `path` (longest matching folder prefix), or ''."""
    norm = path.replace("\\", "/")
    areas = load()["test_areas"]
    best = max((p for p in areas if norm.startswith(p)), key=len, default="")
    return areas.get(best, "")
