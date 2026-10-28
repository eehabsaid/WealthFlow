"""PDF extras for a user guide: a contents page with page numbers and links, a PDF outline (chapters -> tabs), page numbers in
the footer and headings that never end a page alone. Right-to-left guides are mirrored. Built in passes until the contents'
page numbers are stable (the contents' own length shifts them)."""

from __future__ import annotations

from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, SimpleDocTemplate

from .pdf_contents import contents_flowables, pick_layout
from .pdf_flow import HeadingLtr, HeadingRtl

OUTLINE_LEVELS = (2, 3)       # markdown heading levels listed in the outline and the contents: chapters, tabs
MAX_PASSES = 4
MAX_TOC_ENTRIES = 80          # a longer guide lists only its chapters in the contents (the tabs stay in the outline panel)


class _GuideDoc(SimpleDocTemplate):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.entries: list[tuple[int, str, int, str]] = []

    def afterFlowable(self, flowable):
        level = getattr(flowable, "level", 0)
        if level in OUTLINE_LEVELS and isinstance(flowable, (HeadingLtr, HeadingRtl)):
            key = f"h{len(self.entries)}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(flowable.title, key, level - OUTLINE_LEVELS[0], closed=False)
            self.entries.append((level, flowable.title, self.page, key))


def _footer(font: str):
    def draw(canvas, doc):
        canvas.saveState()
        canvas.setFont(font, 9)
        canvas.drawCentredString(doc.pagesize[0] / 2, 8 * mm, str(doc.page))
        canvas.restoreState()
    return draw


def build_guide(intro, body_factory, contents_title, rtl: bool, font: str, margin: float, title: str, page=A4) -> bytes:
    """`intro()` flowables, then the contents page(s), then `body_factory()` (fresh flowables each pass)."""
    known: list[tuple[int, str, int, str]] = []
    data, layout = b"", ""
    for _ in range(MAX_PASSES):
        if known and not layout:   # the contents is one page: the layout is chosen once, on the real entries
            layout = pick_layout(known, MAX_TOC_ENTRIES, intro, contents_title, rtl, font, page, margin)
        lines = contents_flowables(known, layout, rtl, font, page[0] - 2 * margin) if known else []
        story = intro() + ([contents_title(), *lines] if lines else []) + [PageBreak()] + body_factory()
        buf = BytesIO()
        doc = _GuideDoc(buf, pagesize=page, leftMargin=margin, rightMargin=margin, topMargin=margin, bottomMargin=margin + 6 * mm, title=title)
        doc.build(story, onFirstPage=_footer(font), onLaterPages=_footer(font))
        data = buf.getvalue()
        if [(lv, t, pg) for lv, t, pg, _ in doc.entries] == [(lv, t, pg) for lv, t, pg, _ in known]:
            break
        known = doc.entries
    return data

