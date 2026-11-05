"""Project: repo root, the coding_agent/ data folder, the rules from config.json, and safe path handling (Windows and POSIX)."""

from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path

DEFAULTS = {
    "max_file_lines": 200,
    "index_roots": ["."],
    "index_exclude": [],
    "protected": [],
    "forbidden": [],
    "secret_files": [".env", "*.env", "*.pem", "*id_rsa*", "*.pfx"],
    "test_areas": {},
    "test_command": ["python", "manage.py", "test", "{modules}"],
    "commands": {"allow": [], "ask": [], "deny": [], "ask_args": []},
    "verify_steps": [],
    "e2e": {"paths": [], "command": ""},
}
ALWAYS_EXCLUDE = {".git", "node_modules", "venv", ".venv", "__pycache__", ".mypy_cache", ".pytest_cache", "dist", "build"}
RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}


class PathError(ValueError):
    pass


def norm(raw) -> str:
    """Repo-relative posix path, or PathError. Rejects absolute, drive, UNC, '..', alternate data streams, reserved Windows names."""
    text = str(raw or "").strip().replace("\\", "/")
    if not text or "\0" in text:
        raise PathError("empty path")
    if text.startswith(("/", "~")) or re.match(r"^[A-Za-z]:", text):
        raise PathError(f"path must be relative to the project: {text}")
    parts = []
    for part in text.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise PathError(f"'..' is not allowed: {text}")
        if ":" in part or part.endswith((".", " ")) or part.split(".")[0].lower() in RESERVED:
            raise PathError(f"invalid path component '{part}' (unsafe on Windows)")
        parts.append(part)
    if not parts:
        raise PathError("empty path")
    return "/".join(parts)


def matches(path: str, rules) -> str | None:
    """The reason (or pattern) of the first rule matching `path`, case-insensitively; None when nothing matches."""
    low = path.lower()
    base = low.rsplit("/", 1)[-1]
    for rule in rules:
        pattern = (rule["pattern"] if isinstance(rule, dict) else str(rule)).lower()
        if fnmatch.fnmatchcase(low, pattern) or ("/" not in pattern and fnmatch.fnmatchcase(base, pattern)):
            return rule.get("reason", pattern) if isinstance(rule, dict) else pattern
    return None


class Project:
    def __init__(self, root, agent_dir: str = "coding_agent"):
        self.root = Path(root).resolve()
        self.agent_dir = self.root / agent_dir
        self.lock_dir = self.agent_dir / ".locks"
        self.config = self._load()

    def _load(self) -> dict:
        try:
            data = json.loads((self.agent_dir / "config.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        merged = {**DEFAULTS, **data}
        merged["commands"] = {**DEFAULTS["commands"], **(data.get("commands") or {})}
        merged["e2e"] = {**DEFAULTS["e2e"], **(data.get("e2e") or {})}
        return merged

    def resolve(self, raw) -> tuple[str, Path]:
        """(repo-relative posix path, absolute Path) of something inside the project, or PathError (also for symlink escapes)."""
        rel = norm(raw)
        target = (self.root / rel).resolve()
        if not target.is_relative_to(self.root):
            raise PathError(f"resolves outside the project: {rel}")
        return rel, target

    def forbidden_reason(self, rel: str) -> str:
        if rel == ".git" or rel.startswith(".git/"):
            return "git internals are never edited"
        return matches(rel, self.config["forbidden"]) or ""

    def secret_reason(self, rel: str) -> str:
        hit = matches(rel, self.config["secret_files"])
        return f"matches secret-file pattern {hit}" if hit else ""

    def protected_reason(self, rel: str) -> str:
        return matches(rel, self.config["protected"]) or ""

    def test_module(self, rel: str) -> str:
        areas = self.config["test_areas"]
        best = max((p for p in areas if rel.startswith(p)), key=len, default="")
        return areas.get(best, "")
