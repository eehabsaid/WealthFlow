"""Repo index built from the source itself (AST for Python, a light scan for JS): files, classes, functions, models, imports, routes,
and who imports what. It stores file metadata so it can detect stale, renamed, modified and deleted files and refresh incrementally instead of
rebuilding on every request. Adapted from ai/services/coding/index.py, no Django."""

from __future__ import annotations

from .parsers import (  # noqa: F401
    CODE_EXT,
    MAX_BYTES,
    _JS_DEF,
    _JS_IMPORT,
    WORD,
    INDEX_VERSION,
    _sha256,
    _py,
    _js,
    _html,
    _words,
)
from .repo_index import (  # noqa: F401
    Index,
)

__all__ = ['CODE_EXT', 'MAX_BYTES', '_JS_DEF', '_JS_IMPORT', 'WORD', 'INDEX_VERSION', '_sha256', '_py', '_js', '_html', '_words', 'Index']
