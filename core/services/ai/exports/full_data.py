"""The COMPLETE data behind an answer, rebuilt when the file is downloaded (nothing is stored).

The chat shows at most 300 rows and a model's reply is whatever it wrote, but a file must hold everything. Two replays,
both owner-scoped to the conversation's user and capped by the `ai_file_max_rows` setting:

  1. the `generate_file` tool calls saved on the answer: each `dataset` spec is run against the database again;
  2. the question the answer replied to, routed again by the instant-answer router and executed in export mode
     (no 300-row cap, no cell truncation): the exact table, even when a model wrote the visible text.

Anything else (advice, prose, analytics) falls back to the saved answer text."""

from __future__ import annotations

import logging
import re
from typing import Any

from ..query_engine.executors.common import export_mode
from .dataset import DatasetError, cell_text, dataset_markdown
from .settings import get_settings

logger = logging.getLogger(__name__)
TOOL_NAME = "generate_file"
_FENCE = re.compile(r"```([\w+-]*)\n(.*?)```", re.S)


def tool_calls_for_files(message: Any) -> list[dict]:
    return [c for c in (message.tool_calls or []) if isinstance(c, dict) and c.get("tool") == TOOL_NAME and c.get("status") == "success"]


def _table_markdown(raw: dict, title: str) -> str:
    columns = [cell_text(c) for c in raw.get("columns", [])][:60]
    lines = [f"## {title}" if title else "", "", "| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    lines += ["| " + " | ".join(cell_text(v) for v in (r if isinstance(r, (list, tuple)) else [r])[:len(columns)]) + " |" for r in raw.get("rows", [])]
    if isinstance(raw.get("totals"), list):
        lines.append("| " + " | ".join(f"**{cell_text(v)}**" if v != "" else "" for v in raw["totals"][:len(columns)]) + " |")
    return "\n".join(lines)


_PAREN = re.compile(r"\([^)]*\)")


def _norm_heading(line: str) -> str:
    """A heading without its numbering ("4.1.", "٥.١"), its "(English)" gloss and punctuation, so two drafts of one guide agree."""
    return "".join(ch for ch in _PAREN.sub("", line.lstrip("#")).lower() if ch.isalpha())


def _heading_set(text: str) -> set[str]:
    return {_norm_heading(line) for line in text.splitlines() if line.lstrip().startswith("#")} - {""}


def _title(text: str) -> str:
    return next((_norm_heading(line) for line in text.splitlines() if line.startswith("# ")), "")


def superseded_drafts(calls: list[dict]) -> set[int]:
    """Indices of generate_file calls whose text is an earlier, shorter draft of the SAME document written again later.

    A model that is not sure its file was saved writes the whole guide again (nine times in one real run), and joining every
    call put nine copies in the file. Two texts are drafts of one document when they carry the same "# title", or when at
    least a third of the smaller one's headings (and at least three) also head the other; the longest draft is kept. Texts
    about different things are parts of one document: all kept."""
    kept: list[tuple[int, set[str], int, str]] = []     # (call index, headings, length, title) of the draft kept per document
    skip: set[int] = set()
    for i, call in enumerate(calls):
        text = str((call.get("arguments") or {}).get("content") or "")
        heads, title = _heading_set(text), _title(text)
        if not text.strip() or len(heads) < 3:
            continue
        for n, (j, other, size, other_title) in enumerate(kept):
            if (title and title == other_title) or len(heads & other) >= max(3, min(len(heads), len(other)) // 3):
                if len(text) > size:
                    skip.add(j)
                    kept[n] = (i, heads, len(text), title)
                else:
                    skip.add(i)
                break
        else:
            kept.append((i, heads, len(text), title))
    return skip


def from_tool_calls(message: Any, user: Any) -> tuple[str, str | None] | None:
    """(markdown, raw text for code formats) built from the saved generate_file arguments."""
    calls = tool_calls_for_files(message)
    if not calls:
        return None
    cfg, parts, source = get_settings(), [], None
    old_drafts = superseded_drafts(calls)
    for index, call in enumerate(calls):
        args = call.get("arguments") or {}
        title = str(args.get("title") or "")
        specs = args.get("datasets") if isinstance(args.get("datasets"), list) else ([args["dataset"]] if args.get("dataset") else [])
        for spec in specs:
            try:
                parts.append(dataset_markdown(user, spec, cfg.max_rows, title if len(specs) == 1 else ""))
            except DatasetError as exc:
                logger.warning("export dataset replay failed: %s", exc)
        if isinstance(args.get("table"), dict):
            parts.append(_table_markdown(args["table"], title if not specs else ""))
        if args.get("content") and index not in old_drafts:
            source = str(args["content"])
            parts.append(source if args.get("format") not in ("py", "js", "html", "css", "json", "sql", "txt", "md") else f"```\n{source}\n```")
    return ("\n\n".join(p if isinstance(p, str) else p[0] for p in parts), source) if parts else None


def from_question(message: Any, user: Any, question: str, previous: str) -> str | None:
    """Exact, uncapped markdown for a question the instant-answer router can compute; None otherwise."""
    from ..query_engine.engine import _category_lookup
    from ..query_engine.registry import get_capability
    from ..query_engine.render import render
    from ..query_engine.slots import route
    from .intent import strip_export_terms

    try:
        routing = route(strip_export_terms(question), category_lookup=_category_lookup(user), previous=previous)
        cap = get_capability(routing.request.capability) if routing.status == "ready" and routing.request else None
        if cap is None:
            return None
        with export_mode(get_settings().max_rows):
            return render(cap.executor(user, routing.request)) or None
    except Exception as exc:   # best effort: the saved answer text is still a correct file
        logger.warning("export replay failed: %s", exc)
        return None


def code_from_markdown(content: str, extension: str) -> str:
    """Raw text for a code/text file: the fenced block of that language, else all fenced blocks, else the whole answer."""
    blocks = _FENCE.findall(content or "")
    if not blocks:
        return str(content or "").strip() + "\n"
    same = [body for lang, body in blocks if lang.lower() in (extension, {"py": "python", "js": "javascript", "md": "markdown"}.get(extension, extension))]
    return "\n".join(same or [body for _, body in blocks]).rstrip() + "\n"


def formats_from_tool_calls(calls: Any) -> list:
    """Download formats the model chose with generate_file when the user's own words named none."""
    from .intent import exports_enabled_formats

    return exports_enabled_formats([c.get("arguments", {}).get("format") for c in (calls or [])
                                    if isinstance(c, dict) and c.get("tool") == TOOL_NAME and c.get("status") == "success"])
