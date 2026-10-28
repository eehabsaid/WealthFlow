"""The PDF guide's contents is one page for the current guide (18 chapters + 52 tabs), English and Arabic, and the tabs stay in the
PDF outline panel; a much longer guide lists only its chapters."""

from __future__ import annotations

from io import BytesIO

from django.test import SimpleTestCase
from pypdf import PdfReader

from core.services.ai.exports.document import ExportDocument, parse_markdown
from core.services.ai.exports.registry import get_format

NAMES = {"en": ("Screen", "Tab"), "ar": ("الشاشة", "التبويب")}


def pdf(lang: str, per_chapter: list[int]) -> PdfReader:
    screen, tab = NAMES[lang]
    md = "".join(f"## {screen} {i}\n\nText.\n\n" + "".join(f"### {tab} {i}-{j}\n\nText {j}\n\n" for j in range(n)) for i, n in enumerate(per_chapter, 1))
    doc = ExportDocument(title="Guide", generated="2026", lang=lang, blocks=parse_markdown(md), source=md)
    return PdfReader(BytesIO(get_format("pdf").builder(doc, lang)))


def outline(reader: PdfReader) -> list[tuple[str, int]]:
    found: list = []

    def walk(items):
        for item in items:
            walk(item) if isinstance(item, list) else found.append((item.title, reader.get_destination_page_number(item) + 1))
    walk(reader.outline)
    return found


class PdfContentsTests(SimpleTestCase):
    def test_current_guide_contents_is_one_page(self):
        for lang in ("en", "ar"):
            with self.subTest(lang=lang):
                reader = pdf(lang, [3] * 16 + [2, 2])
                entries = outline(reader)
                self.assertEqual(len(entries), 70)
                self.assertEqual(entries[0][1], 2)   # chapter 1 follows the one contents page

    def test_every_tab_is_in_the_contents_page_text_in_english(self):
        text = pdf("en", [3] * 16 + [2, 2]).pages[0].extract_text()
        self.assertIn("Tab 1-0", text)
        self.assertIn("Tab 17-1", text)

    def test_long_guide_lists_only_chapters(self):
        reader = pdf("en", [6] * 17)
        self.assertNotIn("Tab 3-2", reader.pages[0].extract_text())
        self.assertEqual(len(outline(reader)), 17 * 7)
