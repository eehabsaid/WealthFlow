"""ReportLab flowables for the PDF builder: a right-to-left paragraph that wraps before it reorders, outline headings,
and a contents line (title, dotted leader, page number) that mirrors for right-to-left documents."""

from __future__ import annotations

from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, Paragraph

from core.reports.pdf_rtl import rtl_markup, visual


class RtlParagraph(Paragraph):
    """Text is wrapped on its logical words for the width it is given, then each line is reshaped + bidi'd on its own."""

    def __init__(self, text, style, runs=None, faces=None, bold_all=False, **kw):
        self._runs, self._faces, self._bold_all, self._for_width = runs, faces, bold_all, None
        super().__init__(text if runs is None else "", style, **kw)

    def wrap(self, availWidth, availHeight):
        if self._runs is not None and self._for_width != availWidth:
            width = availWidth - self.style.leftIndent - self.style.rightIndent
            Paragraph.__init__(self, rtl_markup(self._runs, self._faces, self.style.fontSize, width, self._bold_all), self.style)
            self._for_width = availWidth
        return super().wrap(availWidth, availHeight)


class _Outline:
    level: int = 0
    title: str = ""


class HeadingLtr(_Outline, Paragraph):
    pass


class HeadingRtl(_Outline, RtlParagraph):
    pass


class TocLine(Flowable):
    """One contents entry: title, dotted leader, page number; a click jumps to the heading (mirrored when rtl)."""

    def __init__(self, level: int, title: str, page: int, key: str, rtl: bool, face: str, size: float = 10):
        super().__init__()
        self.level, self.title, self.page, self.key, self.rtl, self.face, self.size = level, title, page, key, rtl, face, size
        self.width = self.height = 0

    def wrap(self, availWidth, availHeight):
        self.width, self.height = availWidth, self.size * 1.7
        return self.width, self.height

    def draw(self):
        c, size, indent = self.canv, self.size, (self.level - 2) * 5 * mm
        shown, num = (visual(self.title) if self.rtl else self.title), str(self.page)
        room = self.width - indent - stringWidth(num, self.face, size) - 12
        while len(shown) > 4 and stringWidth(shown, self.face, size) > room:
            shown = shown[1:] if self.rtl else shown[:-1]
        c.setFont(self.face, size)
        title_w, num_w, y = stringWidth(shown, self.face, size), stringWidth(num, self.face, size), self.height * 0.3
        if self.rtl:
            c.drawRightString(self.width - indent, y, shown)
            c.drawString(0, y, num)
            start, end = num_w + 4, self.width - indent - title_w - 4
        else:
            c.drawString(indent, y, shown)
            c.drawRightString(self.width, y, num)
            start, end = indent + title_w + 4, self.width - num_w - 4
        if end > start:
            c.saveState()
            c.setDash(0.5, 2.5)
            c.line(start, y + 1.5, end, y + 1.5)
            c.restoreState()
        c.linkRect("", self.key, (0, 0, self.width, self.height), relative=1, thickness=0)
