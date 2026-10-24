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
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.reports.pdf_font_utils import get_arabic_pdf_font, process_pdf_text

from ..document import ExportDocument, is_bold_cell, plain, runs
from ..registry import ExportFormat, register
from .common import intro_lines, is_wide

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
        "heading": style("h", _SIZES["heading"], bold, spaceBefore=8, spaceAfter=4),
        "body": style("b", _SIZES["body"], spaceAfter=3), "cell": style("c", _SIZES["cell"]),
        "cell_bold": style("cb", _SIZES["cell"], bold), "head_cell": style("hc", _SIZES["cell"], bold, textColor=colors.white),
    }


def _para(text: str, style, rtl: bool, bold_all: bool = False) -> Paragraph:
    """Create a ReportLab Paragraph handling RTL Arabic text correctly.

    For RTL languages we need to reverse the visual order per line while
    preserving bold styling. The original implementation applied ``process_pdf_text``
    to the whole paragraph before ReportLab performed line wrapping, which caused
    multi‑line Arabic paragraphs to appear with their lines reversed. This version
    splits the input into logical lines, processes each line individually, reverses
    the order of runs within each line, and then joins the lines with ``<br/>``
    tags so ReportLab can wrap them correctly.
    """
    if rtl:
        # Split on explicit line breaks; if none, treat whole text as a single line.
        lines = text.split('\n')
        processed_lines = []
        for line in lines:
            # ``runs`` returns a list of (segment, is_bold) preserving markdown bold.
            line_parts = []
            for chunk, bold in runs(line) or [(plain(line), False)]:
                # Apply Arabic reshaping and bidi handling.
                safe = escape(process_pdf_text(chunk))
                # Preserve bold styling after reversal.
                line_parts.append(f"<b>{safe}</b>" if bold and not bold_all else safe)
            # Reverse the visual order of the runs for RTL rendering.
            line_parts = list(reversed(line_parts))
            processed_lines.append(' '.join(line_parts))
        # Join lines with a line‑break tag so ReportLab respects the original line breaks.
        html = '<br/>'.join(processed_lines)
        return Paragraph(html, style)
    else:
        # Existing LTR handling.
        parts = []
        for chunk, bold in runs(text) or [(plain(text), False)]:
            safe = escape(process_pdf_text(chunk) if rtl or any("\u0600" <= ch <= "\u06FF" for ch in chunk) else chunk)
            parts.append(f"<b>{safe}</b>" if bold and not bold_all else safe)
        return Paragraph(''.join(parts), style)
    parts = []
    for chunk, bold in runs(text) or [(plain(text), False)]:
        safe = escape(process_pdf_text(chunk) if rtl or any("؀" <= ch <= "ۿ" for ch in chunk) else chunk)
        parts.append(f"<b>{safe}</b>" if bold and not bold_all else safe)
    return Paragraph("".join(parts), style)


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


def _build(doc: ExportDocument, lang: str) -> bytes:
    rtl = lang == "ar"
    page = landscape(A4) if is_wide(doc) else A4
    styles = _styles(rtl)
    story = [_para(text, styles[role], rtl) for role, text in intro_lines(doc)]
    for block in doc.blocks:
        if block.kind == "table":
            if block.rows or block.header:
                story += [_table(block, styles, rtl, page[0] - 2 * _MARGIN), Spacer(1, 6)]
        elif block.kind == "heading":
            story.append(_para(block.text, styles["heading"], rtl))
        else:
            story.append(_para(("• " if block.kind == "bullet" else "") + block.text, styles["body"], rtl))
    buf = BytesIO()
    SimpleDocTemplate(buf, pagesize=page, leftMargin=_MARGIN, rightMargin=_MARGIN, topMargin=_MARGIN, bottomMargin=_MARGIN,
                      title=plain(doc.title)).build(story or [Spacer(1, 1)])
    return buf.getvalue()


register(ExportFormat(
    key="pdf", label="PDF (.pdf)", extension="pdf", mime="application/pdf", builder=_build, order=30,
    terms=(r"\bpdf\b", r"بي دي اف|بدف"),
))
