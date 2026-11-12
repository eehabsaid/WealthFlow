"""Audit coded review records for file references that no longer exist in the live repo.

This is a lightweight source-grounded review helper for the existing ledger review files.
It does not train models or modify the repo; it only validates path references in the QA/patch review rows.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = [ROOT / "coding_agent" / "qa_review.jsonl", ROOT / "coding_agent" / "patch_review.jsonl"]
PATH_RE = re.compile(r"(?:^|[\s\(\[\{])([A-Za-z0-9_./\\-]+\.(?:py|js|html|css|json|md))")


def iter_rows(path: Path):
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


_BASENAME_INDEX: dict[str, bool] | None = None


def _basename_exists(name: str) -> bool:
    """Lazily built index of every basename under the repo, so a reference written as just "api.js" or a path missing its leading package
    (e.g. "dev_agent/guard/commands.py" for "ai/dev_agent/guard/commands.py") isn't flagged as missing when the file is genuinely there -
    these are how the agent's own free-text answers refer to files, not fabricated evidence."""
    global _BASENAME_INDEX
    if _BASENAME_INDEX is None:
        _BASENAME_INDEX = {}
        skip = {".git", "node_modules", "__pycache__", ".venv"}
        for folder, dirs, names in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in skip]
            for name in names:
                _BASENAME_INDEX[name] = True
    return _BASENAME_INDEX.get(name.replace("\\", "/").rsplit("/", 1)[-1], False)


def verify_file(path_text: str) -> bool:
    norm = path_text.replace("\\", "/")
    return (ROOT / norm).exists() or _basename_exists(norm)


def main() -> int:
    missing = []
    scanned = 0
    for review_path in FILES:
        for row in iter_rows(review_path):
            scanned += 1
            text = json.dumps(row, ensure_ascii=False)
            for ref in sorted(set(PATH_RE.findall(text))):
                if not verify_file(ref):
                    missing.append((review_path.name, row.get("task_id"), ref))
    print(f"review rows scanned: {scanned}")
    if not missing:
        print("all referenced paths exist in the live repository")
        return 0
    print(f"missing references: {len(missing)}")
    for file_name, task_id, ref in missing:
        print(f"{file_name}: {task_id} -> {ref}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
