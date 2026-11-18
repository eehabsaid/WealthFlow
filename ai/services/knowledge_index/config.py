"""Knowledge-index settings: where the index lives, what is indexed, which parser version is current.

The index is a separate, gitignored SQLite file (default runtime/knowledge_index.sqlite3, override with
settings.AI_KNOWLEDGE_INDEX_PATH) so the tracked db.sqlite3 never grows. It holds SOURCE only, never user data.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings

INDEX_VERSION = 5          # bump when the schema or a parser changes: the next refresh rebuilds everything
INDEXED_SUFFIXES = (".py", ".js", ".html", ".css", ".md")
DATA_FILES = ("page_descriptions.json", "inventory.json")      # the only .json files indexed, besides locale files
LOCALE_DIRS = ("static/i18n",)
LANGS = ("en", "ar", "fr", "de")
MAX_BODY_CHARS = 1200      # source text per symbol used for keyword tokens and embeddings
FRESH_CHECK_SECONDS = 5    # a query re-checks file stamps at most this often


def base_dir() -> Path:
    return Path(getattr(settings, "AI_KNOWLEDGE_ROOT", None) or settings.BASE_DIR).resolve()


def index_path() -> Path:
    custom = getattr(settings, "AI_KNOWLEDGE_INDEX_PATH", None)
    return Path(custom) if custom else base_dir() / "runtime" / "knowledge_index.sqlite3"


def js_engine() -> str:
    """auto (Acorn when node + acorn are installed, else the pure-Python scanner) | acorn | python."""
    value = str(getattr(settings, "AI_KNOWLEDGE_JS_ENGINE", "auto")).lower()
    return value if value in ("auto", "acorn", "python") else "auto"


def is_indexable(rel: str) -> bool:
    """Suffix rule on top of ai.services.investigation.paths (which already refuses secrets, databases, binaries, vendor)."""
    name = rel.rsplit("/", 1)[-1]
    if rel.endswith(".py") or rel.endswith(INDEXED_SUFFIXES[1:]):
        return not name.endswith(".min.js")
    if rel.endswith(".json"):
        return name in DATA_FILES or any(rel.startswith(d + "/") and name[:-5] in LANGS for d in LOCALE_DIRS)
    return False
