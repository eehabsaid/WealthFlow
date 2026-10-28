"""The contents of a PDF guide: one page. The entries are tried as one list, then in two columns (mirrored for right-to-left:
the first entries sit on the right), then as chapters only; the first layout that fits one page is used, measured on the real
entries (the tabs always stay in the PDF outline panel)."""

from __future__ import annotations

from io import BytesIO

from reportlab.lib.units import mm
from reportlab.platypus import Flowable, PageBreak, SimpleDocTemplate, Table, TableStyle

from .pdf_flow import TocLine

CHAPTER_LEVEL = 2
LAYOUTS = ("list", "columns", "chapters")
GAP = 8 * mm


class Mark(Flowable):
    """A zero-size flowable that records the page it lands on (to see whether the contents stayed on one page)."""

    def __init__(self, name: str, marks: dict):
        super().__init__()
        self.name, self.marks, self.width = name, marks, 0

    def wrap(self, availWidth, availHeight):
        return 0, 0

    def draw(self):
        pass

    def page_is(self, page: int):
        self.marks[self.name] = page


class Anchors(Flowable):
    """Defines the contents' link targets in a build that has no body (the measuring build)."""

    def __init__(self, keys: list[str]):
        super().__init__()
        self.keys, self.width = keys, 0

    def wrap(self, availWidth, availHeight):
        return 0, 0

    def draw(self):
        for key in self.keys:
            self.canv.bookmarkPage(key)


def _height(line: TocLine) -> float:
    return line.size * (1.9 if line.level == CHAPTER_LEVEL else 1.4)


def _columns(lines: list[TocLine], rtl: bool, width: float) -> Table:
    """Two balanced columns, split before a chapter when possible."""
    heights = [_height(x) for x in lines]
    best = min(range(1, len(lines)), key=lambda i: (max(sum(heights[:i]), sum(heights[i:])) + (0 if lines[i].level == CHAPTER_LEVEL else 40), i), default=len(lines))
    halves = [lines[:best], lines[best:]]
    cells, pads = (halves[::-1], (0, GAP)) if rtl else (halves, (GAP, 0))
    table = Table([cells], colWidths=[width / 2] * 2)
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (0, 0), pads[0]), ("LEFTPADDING", (1, 0), (1, 0), pads[1])]))
    return table


def contents_flowables(entries: list, layout: str, rtl: bool, font: str, width: float) -> list:
    shown = [e for e in entries if e[0] == CHAPTER_LEVEL] if layout == "chapters" else entries
    lines = [TocLine(lv, t, pg, key, rtl, font, 10.5 if lv == CHAPTER_LEVEL else 9) for lv, t, pg, key in shown]
    return [_columns(lines, rtl, width)] if layout == "columns" and lines else lines


def pick_layout(entries: list, max_entries: int, intro, title, rtl: bool, font: str, page, margin: float) -> str:
    """The first layout whose contents (after the intro) end on the page they start on; the last one when none does."""
    options = LAYOUTS[-1:] if len(entries) > max_entries else LAYOUTS
    for layout in options:
        marks: dict = {}
        start, end = Mark("start", marks), Mark("end", marks)
        story = [*intro(), start, title(), *contents_flowables(entries, layout, rtl, font, page[0] - 2 * margin), end, PageBreak(), Anchors([e[3] for e in entries])]
        doc = SimpleDocTemplate(BytesIO(), pagesize=page, leftMargin=margin, rightMargin=margin, topMargin=margin, bottomMargin=margin + 6 * mm)
        doc.afterFlowable = lambda f: f.page_is(doc.page) if isinstance(f, Mark) else None
        doc.build(story)
        if marks.get("start") == marks.get("end"):
            return layout
    return options[-1]
