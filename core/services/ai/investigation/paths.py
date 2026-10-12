"""Safe, read-only access to the repository tree for the AI investigator (sysadmin only, see code_tools.py).

Every path is resolved inside BASE_DIR (symlinks and `..` cannot escape), secrets/databases/binaries/vendor bundles are
never listed, searched or read, and anything that looks like a credential is redacted from returned text.
"""

from __future__ import annotations

import fnmatch
import os
import re
import time
from pathlib import Path

from django.conf import settings

BASE = Path(settings.BASE_DIR).resolve()

BLOCKED_DIRS = frozenset({
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env", ".mypy_cache", ".pytest_cache", "htmlcov",
    "staticfiles", "media", "backups", "test_reports", "docs", "dist", "build", ".idea", ".vscode",
})
BLOCKED_FILES = (
    ".env", ".env.*", "*.sqlite3", "*.sqlite3.*", "*.sqlite", "*.db", "*.pem", "*.key", "*.p12", "*.pfx", "*.crt",
    "id_rsa*", "*.pyc", "*.pyo", "*.log", "*.bak*", "*.zip", "*.gz", "*.tar", "*.7z", "*.min.js", "*.min.css",
    "*.map", "credentials*", "secrets*", "*.pdf", "*.png", "*.jpg", "*.jpeg", "*.gif", "*.ico", "*.webp", "*.svg",
    "*.woff", "*.woff2", "*.ttf", "*.eot", "*.mp3", "*.mp4", "*.xlsx", "*.xls", "*.docx", "*.pptx", "*.lock",
)
MAX_FILE_BYTES = 400_000
_SECRET_ASSIGN = re.compile(
    r"""(?ix)(\b[\w.]*(?:secret|password|passwd|api[_-]?key|token|private[_-]?key|client[_-]?secret|hmac|salt)[\w.]*
    \s*[:=]\s*)(['"])(?!\s*\2)(?:(?!\2).)+\2""")
_LONG_TOKEN = re.compile(r"\b(?=[A-Za-z0-9+/_-]*\d)(?=[A-Za-z0-9+/_-]*[A-Za-z])[A-Za-z0-9+/_-]{40,}\b")
_CACHE: dict = {"at": None, "files": []}   # None = never built (a 0.0 stamp is wrong: monotonic() starts near 0 right after boot)
_CACHE_TTL_S = 60


class PathError(ValueError):
    """The requested path is outside the repo, blocked, or does not exist."""


def is_blocked_name(name: str) -> bool:
    low = name.lower()
    return any(fnmatch.fnmatch(low, pat) for pat in BLOCKED_FILES)


def rel(path: Path) -> str:
    return path.relative_to(BASE).as_posix() or "."


def resolve(rel_path: str = "") -> Path:
    """`rel_path` (repo-relative, '' = root) as an absolute Path, or PathError."""
    text = str(rel_path or "").strip().replace("\\", "/").lstrip("/")
    if text in ("", "."):
        return BASE
    parts = [p for p in text.split("/") if p not in ("", ".")]
    if ".." in parts:
        raise PathError("'..' is not allowed; paths are relative to the project root")
    target = (BASE / "/".join(parts)).resolve()
    if target != BASE and BASE not in target.parents:
        raise PathError("path is outside the project")
    check = target.relative_to(BASE).parts
    if any(p in BLOCKED_DIRS for p in check) or (check and is_blocked_name(check[-1]) and target.is_file()):
        raise PathError("that path is excluded (secrets, databases, binaries, vendor or generated files)")
    if not target.exists():
        raise PathError(f"'{text}' does not exist (use app_list_dir or app_find_files to discover paths)")
    return target


def iter_files(root: Path | None = None):
    """(relative posix path, size) of every readable text-candidate file under root; cached for a minute."""
    now = time.monotonic()
    if _CACHE["at"] is None or now - _CACHE["at"] > _CACHE_TTL_S:
        files = []
        for dirpath, dirnames, filenames in os.walk(BASE):
            dirnames[:] = sorted(d for d in dirnames if d not in BLOCKED_DIRS and not d.startswith("."))
            for fn in sorted(filenames):
                if is_blocked_name(fn):
                    continue
                full = Path(dirpath, fn)
                try:
                    size = full.stat().st_size
                except OSError:
                    continue
                if size <= MAX_FILE_BYTES:
                    files.append((full.relative_to(BASE).as_posix(), size))
        _CACHE.update(at=now, files=files)
    if root is None or root == BASE:
        return list(_CACHE["files"])
    prefix = rel(root) + "/"
    return [(p, s) for p, s in _CACHE["files"] if p.startswith(prefix) or p == rel(root)]


def read_text(path: Path) -> str | None:
    """File text (utf-8, undecodable bytes replaced) or None for binary files."""
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\0" in raw[:2048]:
        return None
    return raw.decode("utf-8", errors="replace")


def redact(text: str) -> str:
    """Mask credential-looking assignments and long random tokens before text reaches the model."""
    text = _SECRET_ASSIGN.sub(lambda m: f"{m.group(1)}{m.group(2)}***REDACTED***{m.group(2)}", text)
    return _LONG_TOKEN.sub("***REDACTED***", text)
