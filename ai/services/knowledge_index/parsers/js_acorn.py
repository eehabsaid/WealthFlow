"""Acorn-based JavaScript indexing through a one-shot Node process per batch (no server, no network).

Available only when `node` is on PATH and the repo's node_modules contains `acorn` (it ships with eslint/prettier).
Anything that fails here (no Node, parse error in one file) falls back to the pure-Python scanner for just that file.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from ai.services.knowledge_index import config
from ai.services.knowledge_index.parsers import make_symbol

BRIDGE = Path(__file__).with_name("acorn_bridge.js")
_TIMEOUT_S = 120


def acorn_path() -> str | None:
    """Acorn from the project's node_modules (a transitive dependency of eslint/prettier), or from the indexed root."""
    from django.conf import settings

    for base in (Path(settings.BASE_DIR), config.base_dir()):
        found = base / "node_modules" / "acorn"
        if (found / "package.json").is_file():
            return str(found)
    return None


def available() -> bool:
    return bool(shutil.which("node") and acorn_path())


def _convert(raw: dict, text: str) -> tuple[list[dict], list[dict]]:
    lines = text.splitlines()
    symbols = []
    for s in raw["symbols"]:
        first = lines[s["line"] - 1].strip() if 0 < s["line"] <= len(lines) else ""
        sym = make_symbol(s["name"], s["kind"], s["line"], s["end"], parent=s["parent"], sig=first,
                          body="\n".join(lines[s["line"] - 1: min(s["end"], s["line"] + 30)]))
        sym["scope"] = s["scope"]
        symbols.append(sym)
    seen, refs = set(), []
    for r in raw["refs"]:
        key = (r["line"], r["name"], r["kind"])
        if key not in seen:
            seen.add(key)
            refs.append(r)
    return symbols, refs


def parse_many(files: list[tuple[str, Path]]) -> dict[str, tuple[list[dict], list[dict]]]:
    """{rel path: (symbols, refs)} for the files Acorn could parse; missing keys = use the fallback scanner."""
    if not files or not available():
        return {}
    payload = json.dumps({"acorn": acorn_path(), "files": [{"path": rel, "abs": str(p)} for rel, p in files]})
    try:
        done = subprocess.run(["node", str(BRIDGE)], input=payload, capture_output=True, text=True, timeout=_TIMEOUT_S,
                              cwd=config.base_dir(), check=False)
        data = json.loads(done.stdout) if done.returncode == 0 and done.stdout else {}
    except (OSError, subprocess.SubprocessError, ValueError):
        return {}
    out = {}
    for rel, path in files:
        raw = data.get(rel)
        if raw and "error" not in raw:
            out[rel] = _convert(raw, path.read_text(encoding="utf-8", errors="replace"))
    return out
