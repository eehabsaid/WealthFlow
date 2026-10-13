"""ExportDocument: an assistant answer (markdown) parsed into headings, paragraphs, bullets and tables.

Every answer, whichever topic or path produced it (instant engine table, model prose, investigator),
is plain markdown, so one parser feeds every file format. The download links the app appends to an
answer are dropped here so the file never contains them."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

EXPORT_PATH_MARK = "/export/"          # every export link URL contains this (checked against reverse() in tests)
_LINK = re.compile(r"\[([^\]\n]*)\]\(([^)\s]*)\)")
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET = re.compile(r"^\s*[-*•]\s+(.*)$")
_ORDERED = re.compile(r"^\s*(\d+)[.)]\s+(.*)$")
_QUOTE = re.compile(r"^\s*>\s?(?:\[!\w+\]\s*)?(.*)$")
_RULE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
_SEPARATOR_CELL = re.compile(r"^:?-{3,}:?$")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_INLINE = re.compile(r"`([^`]*)`|__(.+?)__")


@dataclass
class Block:
    kind: str                                   # heading | text | bullet | table
    text: str = ""
    level: int = 1
    header: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)


@dataclass
class ExportDocument:
    title: str = ""
    question: str = ""
    generated: str = ""
    lang: str = "en"
    blocks: list[Block] = field(default_factory=list)

    def tables(self) -> list[Block]:
        return [b for b in self.blocks if b.kind == "table"]


def plain(text: str) -> str:
    """Markdown inline syntax removed: **bold**, `code`, [text](url)."""
    text = _LINK.sub(lambda m: m.group(1), str(text or ""))
    text = _BOLD.sub(lambda m: m.group(1), text)
    text = _INLINE.sub(lambda m: m.group(1) or m.group(2) or "", text)
    return text.replace("**", "").strip()


def runs(text: str) -> list[tuple[str, bool]]:
    """[(text, bold)] so Word / PDF keep the answer's bold emphasis."""
    text = _LINK.sub(lambda m: m.group(1), str(text or ""))
    out, pos = [], 0
    for m in _BOLD.finditer(text):
        if m.start() > pos:
            out.append((_INLINE.sub(lambda x: x.group(1) or x.group(2) or "", text[pos:m.start()]), False))
        out.append((m.group(1), True))
        pos = m.end()
    if pos < len(text):
        out.append((_INLINE.sub(lambda x: x.group(1) or x.group(2) or "", text[pos:]), False))
    return [(t, b) for t, b in out if t]


def is_bold_cell(cell: str) -> bool:
    c = str(cell or "").strip()
    return len(c) > 4 and c.startswith("**") and c.endswith("**") and c.count("**") == 2


def strip_export_lines(content: str) -> str:
    """Remove lines that consist only of the app's own download links."""
    kept = []
    for line in str(content or "").splitlines():
        links = _LINK.findall(line)
        if links and all(EXPORT_PATH_MARK in url for _, url in links):
            rest = _LINK.sub("", line)
            if not re.sub(r"[\s·|,;/\-–—•]+", "", rest):
                continue
        kept.append(line)
    return "\n".join(kept)


def _cells(line: str) -> list[str]:
    inner = line.strip()
    inner = inner[1:] if inner.startswith("|") else inner
    inner = inner[:-1] if inner.endswith("|") else inner
    return [c.strip() for c in inner.split("|")]


def _table(lines: list[str]) -> Block:
    rows = [_cells(line) for line in lines]
    header: list[str] = []
    if len(rows) > 1 and all(_SEPARATOR_CELL.match(c) for c in rows[1] if c):
        header, rows = rows[0], rows[2:]
    else:
        rows = [r for r in rows if not all(_SEPARATOR_CELL.match(c) for c in r if c)]
    width = max([len(header), *(len(r) for r in rows)] or [0])
    pad = lambda r: r + [""] * (width - len(r))  # noqa: E731
    return Block("table", header=pad(header) if header else [], rows=[pad(r) for r in rows])


def parse_markdown(content: str) -> list[Block]:
    blocks: list[Block] = []
    pending: list[str] = []
    in_code = False

    def flush():
        if pending:
            blocks.append(_table(pending[:]))
            pending.clear()

    for raw in strip_export_lines(content).splitlines():
        line = raw.rstrip()
        if line.strip().startswith("```"):
            flush()
            in_code = not in_code
            continue
        if not in_code and line.lstrip().startswith("|"):
            pending.append(line)
            continue
        flush()
        if not line.strip() or (not in_code and _RULE.match(line)):
            continue
        if in_code:
            blocks.append(Block("text", text=line))
        elif m := _HEADING.match(line):
            blocks.append(Block("heading", text=plain(m.group(2)), level=len(m.group(1))))
        elif m := _BULLET.match(line):
            blocks.append(Block("bullet", text=m.group(1).strip()))
        elif m := _ORDERED.match(line):
            blocks.append(Block("text", text=f"{m.group(1)}. {m.group(2).strip()}"))
        elif m := _QUOTE.match(line):
            blocks.append(Block("text", text=m.group(1).strip()))
        else:
            blocks.append(Block("text", text=line.strip()))
    flush()
    return blocks
