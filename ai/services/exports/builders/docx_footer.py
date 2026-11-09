"""Footer for every Word file: the document title and a live PAGE field (Word / LibreOffice fill in the number), centred.
It carries no wording of its own, so there is nothing to translate; an Arabic document gets a right-to-left paragraph."""

from __future__ import annotations

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

SEPARATOR = "  |  "


def _field(paragraph, instruction: str, cached: str = "1") -> None:
    """begin / instruction / separate / cached result / end, as Word writes a simple PAGE field."""
    for kind in ("begin", "instr", "separate", "text", "end"):
        run = paragraph.add_run()
        if kind == "instr":
            node = OxmlElement("w:instrText")
            node.set(qn("xml:space"), "preserve")
            node.text = f" {instruction} "
        elif kind == "text":
            node = OxmlElement("w:t")
            node.text = cached
        else:
            node = OxmlElement("w:fldChar")
            node.set(qn("w:fldCharType"), kind)
        run._r.append(node)


def add_page_footer(document, title: str, rtl: bool) -> None:
    """Every section gets the footer (a wide table switches only the orientation of the first one)."""
    for section in document.sections:
        paragraph = section.footer.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if title:
            paragraph.add_run(f"{title}{SEPARATOR}")
        _field(paragraph, "PAGE")
        if rtl:
            paragraph._p.get_or_add_pPr().append(OxmlElement("w:bidi"))
