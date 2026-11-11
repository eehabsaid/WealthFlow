"""Audit coded review records for file references that no longer exist in the live repo.

This is a lightweight source-grounded review helper for the existing ledger review files.
It does not train models or modify the repo; it only validates path references in the QA/patch review rows.
"""

from __future__ import annotations

import json
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


def verify_file(path_text: str) -> bool:
    norm = path_text.replace("\\", "/")
    candidate = ROOT / norm
    return candidate.exists()


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
