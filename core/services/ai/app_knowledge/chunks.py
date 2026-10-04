"""Chunk store: built once per process, rebuilt when a source file changes (cheap mtime signature)."""

from __future__ import annotations

import os
import threading
from typing import Any

from django.conf import settings

from .chunk_sources import code_chunks, flow_chunks, page_chunks
from .data_flows import FILE_NAME

_LOCK = threading.Lock()
_STORE: dict[str, Any] = {"sig": None, "chunks": []}


def _signature() -> tuple:
    base = settings.BASE_DIR
    paths = [os.path.join(base, "ai_knowledge", FILE_NAME), os.path.join(base, "doc_engine", "content", "page_descriptions.json")]
    sig = [os.path.getmtime(p) if os.path.exists(p) else 0 for p in paths]
    return tuple(sig)  # code docstrings only change with a deploy/restart, which resets the process cache


def get_chunks(force: bool = False) -> list[dict[str, Any]]:
    sig = _signature()
    with _LOCK:
        if force or _STORE["sig"] != sig or not _STORE["chunks"]:
            _STORE["chunks"] = flow_chunks() + page_chunks() + code_chunks()
            _STORE["sig"] = sig
        return _STORE["chunks"]
