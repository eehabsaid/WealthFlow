"""PDF (.pdf) via ReportLab: title block, then headings / paragraphs / bullets / tables in answer order.
Uses the app's shared Arabic-capable font + reshaping (core/reports/pdf_font_utils), mirrors tables and
right-aligns text for Arabic, and goes landscape for wide tables."""

from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.reports.pdf_font_utils import get_arabic_pdf_font, process_pdf_text

from ..document import ExportDocument, is_bold_cell, plain, runs
from ..registry import ExportFormat, register
from .common import intro_lines, is_wide, numbered_guide_blocks
from .guide_html import is_guide
from .pdf_flow import HeadingLtr, HeadingRtl, RtlParagraph
from .pdf_guide import build_guide

_MARGIN = 15 * mm
_HEADER_BG = colors.HexColor("#1F4E78")
_GRID = colors.HexColor("#B7C3D0")
_MIN_COL_CHARS = 6
_MAX_COL_CHARS = 40
_SIZES = {"title": 18, "question": 11, "meta": 9, "heading": 13, "body": 10, "cell": 9}


def _styles(rtl: bool):
    font, bold = get_arabic_pdf_font()
    align = TA_RIGHT if rtl else TA_LEFT

    def style(name, size, face=font, **kw):
        return ParagraphStyle(name, fontName=face, fontSize=size, leading=size * 1.35, alignment=align, **kw)

    return {
        "title": style("t", _SIZES["title"], bold, spaceAfter=4), "question": style("q", _SIZES["question"], bold, spaceAfter=2),
        "meta": style("m", _SIZES["meta"], textColor=colors.grey, spaceAfter=8),
        "heading": style("h", _SIZES["heading"], bold, spaceBefore=8, spaceAfter=4, keepWithNext=1),
        "body": style("b", _SIZES["body"], spaceAfter=3), "cell": style("c", _SIZES["cell"]),
        "cell_bold": style("cb", _SIZES["cell"], bold), "head_cell": style("hc", _SIZES["cell"], bold, textColor=colors.white),
    }


def _para(text: str, style, rtl: bool, bold_all: bool = False, heading_level: int = 0) -> Paragraph:
    """A paragraph. Right-to-left text is wrapped on its logical words and reordered per line (core/reports/pdf_rtl.py): reordering
    a whole paragraph before ReportLab wraps it shows the lines in reverse order."""
    parts_runs = runs(text) or [(plain(text), False)]
    if rtl:
        font, bold = get_arabic_pdf_font()
        para = (HeadingRtl if heading_level else RtlParagraph)(None, style, runs=parts_runs, faces=(font, bold), bold_all=bold_all)
    else:
        parts = []
        for chunk, is_bold in parts_runs:
            safe = escape(process_pdf_text(chunk) if any("\u0600" <= ch <= "\u06FF" for ch in chunk) else chunk)
            parts.append(f"<b>{safe}</b>" if is_bold and not bold_all else safe)
        para = (HeadingLtr if heading_level else Paragraph)("".join(parts), style)
    if heading_level:
        para.level, para.title = heading_level, plain(text)
    return para


def _col_widths(block, total: float) -> list[float]:
    width = len(block.header) if block.header else max(len(r) for r in block.rows)
    weights = []
    for c in range(width):
        cells = ([block.header[c]] if block.header else []) + [r[c] for r in block.rows if c < len(r)]
        longest = max((len(plain(x)) for x in cells), default=0)
        weights.append(min(max(longest, _MIN_COL_CHARS), _MAX_COL_CHARS))
    return [total * w / sum(weights) for w in weights]


def _table(block, styles, rtl: bool, total: float) -> Table:
    rows = []
    if block.header:
        rows.append([_para(h, styles["head_cell"], rtl, True) for h in block.header])
    for r in block.rows:
        bold = any(is_bold_cell(c) for c in r)
        rows.append([_para(c, styles["cell_bold" if bold else "cell"], rtl, bold) for c in r])
    widths = _col_widths(block, total)
    if rtl:
        rows, widths = [list(reversed(r)) for r in rows], list(reversed(widths))
    table = Table(rows, colWidths=widths, repeatRows=1 if block.header else 0)
    commands = [("GRID", (0, 0), (-1, -1), 0.4, _GRID), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1 if block.header else 0), (-1, -1), [colors.white, colors.HexColor("#F3F6FA")])]
    if block.header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG))
    table.setStyle(TableStyle(commands))
    return table


def _story(doc: ExportDocument, styles, rtl: bool, page, guide: bool, from_body: bool) -> list:
    """The flowables of the intro (title block + text before the first chapter) or of the body (everything after)."""
    blocks, story, started = (numbered_guide_blocks(doc) if guide else doc.blocks), [], False
    chapters = 0
    if not from_body:
        story = [_para(text, styles[role], rtl) for role, text in intro_lines(doc)]
    for block in blocks:
        started = started or (block.kind == "heading" and block.level == 2) or not guide
        if guide and started != from_body:
            continue
        if block.kind == "table":
            if block.rows or block.header:
                story += [_table(block, styles, rtl, page[0] - 2 * _MARGIN), Spacer(1, 6)]
        elif block.kind == "heading":
            chapters += 1 if guide and block.level == 2 else 0
            if guide and block.level == 2 and chapters > 1:
                story.append(PageBreak())   # every chapter starts on its own page (the first follows the contents page)
            story.append(_para(block.text, styles["heading"], rtl, heading_level=block.level if guide else 0))
        else:
            story.append(_para(("• " if block.kind == "bullet" else "") + block.text, styles["body"], rtl))
    return story


def _build(doc: ExportDocument, lang: str) -> bytes:
    rtl = lang == "ar"
    page = landscape(A4) if is_wide(doc) else A4
    styles = _styles(rtl)
    guide = is_guide(doc)
    if guide:
        from .guide_html_assets import LABELS

        font = get_arabic_pdf_font()[0]
        title = LABELS.get(lang, LABELS["en"])["contents"]
        return build_guide(lambda: _story(doc, styles, rtl, page, True, False), lambda: _story(doc, styles, rtl, page, True, True),
                           lambda: _para(title, styles["heading"], rtl), rtl, font, _MARGIN, plain(doc.title), page)
    story = _story(doc, styles, rtl, page, False, False)
    buf = BytesIO()
    SimpleDocTemplate(buf, pagesize=page, leftMargin=_MARGIN, rightMargin=_MARGIN, topMargin=_MARGIN, bottomMargin=_MARGIN,
                      title=plain(doc.title)).build(story or [Spacer(1, 1)])
    return buf.getvalue()


register(ExportFormat(
    key="pdf", label="PDF (.pdf)", extension="pdf", mime="application/pdf", builder=_build, order=30,
    terms=(r"\bpdf\b", r"بي دي اف|بدف"),
))
