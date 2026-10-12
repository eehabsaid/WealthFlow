"""Loads knowledge chunks from the three real sources. A chunk is a small dict:
{id, source, title, text, location}. Nothing here is hand-written knowledge."""

from __future__ import annotations

import ast
import json
import os
import re
from pathlib import Path
from typing import Any

from django.conf import settings

from .data_flows import FILE_NAME

MAX_CHUNK_CHARS = 700
# the assistant's own plumbing is noise for "how do I use the app" questions
_SKIP_DIRS = ("/migrations/", "/tests/", "/management/", "/services/ai/", "/views/ai_chat/")


def _clip(text: str, limit: int = MAX_CHUNK_CHARS) -> str:
    text = re.sub(r"[ \t]+", " ", (text or "").strip())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "..."


# Auto-generated stub text that says nothing about the page; it only competes with real answers in retrieval
# (the model once answered "where do I change my default currency?" with this stub).
_PLACEHOLDER_PURPOSE = "Configure the administrative settings and preferences for "


def _page_text_parts(page: dict[str, Any]) -> list[str]:
    """One documented page as 1..n texts of at most MAX_CHUNK_CHARS: long pages are SPLIT by step, never cut
    (a page whose last step was clipped made that step unanswerable, e.g. the account-deletion step)."""
    purpose = str(page["purpose"]).strip()
    steps = [f"{i}. {s}" for i, s in enumerate(page.get("steps") or [], 1)]
    whole = f"{purpose} Steps: {' '.join(steps)}"
    if len(whole) <= MAX_CHUNK_CHARS:
        return [whole]
    head = _clip(purpose, 300)
    context = _clip(purpose, 120)
    parts, buf, lead = [], [], f"{head} Steps:"
    for step in steps:
        step = _clip(step, MAX_CHUNK_CHARS - len(lead) - 1)
        if buf and len(lead) + 1 + len(" ".join(buf)) + 1 + len(step) > MAX_CHUNK_CHARS:
            parts.append(f"{lead} {' '.join(buf)}")
            buf, lead = [], f"{context} (continued) Steps:"
        buf.append(step)
    if buf or not parts:
        parts.append(f"{lead} {' '.join(buf)}".strip())
    return parts


def page_chunks() -> list[dict[str, Any]]:
    """doc_engine/content/page_descriptions.json: one chunk per documented page / tab / modal (long ones split)."""
    path = Path(settings.BASE_DIR) / "doc_engine" / "content" / "page_descriptions.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    chunks = []
    for key, page in data.items():
        if not isinstance(page, dict) or not page.get("purpose") or str(page["purpose"]).startswith(_PLACEHOLDER_PURPOSE):
            continue
        title = key.replace("::", " > ").replace("_", " ").replace("-", " ")
        for n, text in enumerate(_page_text_parts(page)):
            chunks.append({"id": f"page:{key}" if n == 0 else f"page:{key}:{n}", "source": "page", "title": title,
                           "location": f"page {key}", "text": text})
    return chunks


def flow_chunks() -> list[dict[str, Any]]:
    """ai_knowledge/10_data_flows.md split by '## ' section, then by bullet groups that fit a chunk."""
    path = Path(settings.BASE_DIR) / "ai_knowledge" / FILE_NAME
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    chunks = []
    for block in re.split(r"\n(?=## )", text):
        lines = [ln for ln in block.strip().splitlines() if ln.strip()]
        if not lines or not lines[0].startswith("## "):
            continue
        title, body = lines[0][3:].strip(), lines[1:]
        buf: list[str] = []
        for ln in body + [None]:
            if ln is None or sum(len(b) for b in buf) + len(ln or "") > MAX_CHUNK_CHARS:
                if buf:
                    chunks.append({"id": f"flow:{title}:{len(chunks)}", "source": "flow", "title": title,
                                   "location": f"ai_knowledge/{FILE_NAME}", "text": "\n".join(buf)})
                buf = []
            if ln:
                buf.append(ln)
    return chunks


def code_chunks() -> list[dict[str, Any]]:
    """Module and class docstrings of core/services and core/views (the 'why' written next to the code)."""
    base = Path(settings.BASE_DIR)
    chunks = []
    for root, _, files in os.walk(base / "core"):
        rel_root = os.path.relpath(root, base).replace("\\", "/") + "/"
        if ("/services/" not in "/" + rel_root and "/views/" not in "/" + rel_root) or any(s in "/" + rel_root for s in _SKIP_DIRS):
            continue
        for name in files:
            if not name.endswith(".py") or name.startswith("test"):
                continue
            rel = os.path.join(rel_root, name).replace("\\", "/")
            try:
                tree = ast.parse((Path(root) / name).read_text(encoding="utf-8", errors="ignore"))
            except (SyntaxError, OSError):
                continue
            doc = (ast.get_docstring(tree) or "").strip()
            if len(doc) >= 80 and not name.startswith("__"):
                chunks.append({"id": f"code:{rel}", "source": "code", "title": name[:-3].replace("_", " "),
                               "location": rel, "text": _clip(doc)})
            for node in tree.body:
                cdoc = (ast.get_docstring(node) or "").strip() if isinstance(node, ast.ClassDef) else ""
                if len(cdoc) >= 80:
                    chunks.append({"id": f"code:{rel}:{node.name}", "source": "code", "title": node.name,
                                   "location": rel, "text": _clip(cdoc)})
    return chunks
