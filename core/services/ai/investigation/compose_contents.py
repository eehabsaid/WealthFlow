"""A contents / index list the model wrote inside the guide is removed (the app builds no table of contents of its own here).

Only the SHAPE is judged, in every language: a list whose items mirror the document's own headings, or whose items end in page
numbers behind a dot leader / ellipsis. A chapter that held nothing but such a list disappears with it."""

from __future__ import annotations

import re

ITEM = re.compile(r"^\s*(?:[-*+•]|\d+[.)])\s+(\S.*?)\s*$")
LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
NUMBERING = re.compile(r"^\d+(?:\.\d+)*[.)]?\s+")
LEADER_PAGE = re.compile(r"\s*(?:\.{2,}|…+|·{2,}|\t)\s*\d{1,4}\s*$")
ANY_PAGE = re.compile(r"(?:\s*(?:\.{2,}|…+|·{2,}|\t)\s*|\s+)\d{1,4}\s*$")
SHARE, MIN_PAGED, MIN_MIRRORED = 0.75, 3, 4


def _norm(text: str) -> str:
    return "".join(ch for ch in str(text).lower().replace("&", "and") if ch.isalnum())


def _title(item: str) -> str:
    return ANY_PAGE.sub("", NUMBERING.sub("", LINK.sub(r"\1", item).strip())).strip(" *_`")


def is_contents(items: list[str], known: frozenset) -> bool:
    n = len(items)
    paged = sum(1 for i in items if LEADER_PAGE.search(LINK.sub(r"\1", i))) / n if n else 0
    mirrored = sum(1 for i in items if _norm(_title(i)) in known) / n if n else 0
    return (n >= MIN_PAGED and paged >= SHARE) or (n >= MIN_MIRRORED and mirrored >= SHARE)


def _blocks(lines: list[str]) -> list[tuple[int, int]]:
    """[(first, last)] line index ranges of lists (items may be separated by single blank lines)."""
    out, start, last = [], None, None
    for i, line in enumerate(lines + [""]):
        if ITEM.match(line):
            start, last = (i if start is None else start), i
        elif line.strip() or (i - (last if last is not None else i)) > 1:
            if start is not None:
                out.append((start, last))
            start = last = None
    return out


def _heading_names(text: str) -> frozenset:
    return frozenset(_norm(ln.lstrip("#")) for ln in text.splitlines() if ln.startswith("#")) - {""}


def drop_contents(markdown: str, protect: frozenset = frozenset()) -> str:
    """The Markdown without contents lists. A list mirrors the document's headings when its items are headings of OTHER chapters
    (a chapter that lists its own tabs is ordinary text); `protect` adds heading names known from the plan."""
    chapters = re.split(r"(?m)^(?=## )", markdown)
    out = []
    for n, chapter in enumerate(chapters):
        others = frozenset().union(*(_heading_names(c) for i, c in enumerate(chapters) if i != n)) | set(protect)
        own = _heading_names(chapter) - {_norm(chapter.splitlines()[0].lstrip("#"))} if chapter.startswith("## ") else frozenset()
        known = others - own
        lines = chapter.splitlines()
        drop: set[int] = set()
        for first, last in _blocks(lines):
            items = [ITEM.match(ln).group(1) for ln in lines[first:last + 1] if ITEM.match(ln)]
            if is_contents(items, known):
                drop.update(range(first, last + 1))
        if not drop:
            out.append(chapter)
            continue
        kept = [ln for i, ln in enumerate(lines) if i not in drop]
        if chapter.startswith("## ") and not any(ln.strip() and not ln.startswith("#") for ln in kept) and not any(ln.startswith("###") for ln in kept):
            continue
        out.append("\n".join(kept) + "\n")
    return re.sub(r"\n{3,}", "\n\n", "".join(out))
