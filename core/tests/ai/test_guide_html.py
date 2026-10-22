"""The user guide as a styled single-page HTML file: contents rail linked to every chapter and sub-section, steps and notes, RTL, safe escaping."""

from __future__ import annotations

import re

from django.test import SimpleTestCase

from core.services.ai.exports.builders.guide_html import build_guide_html, is_guide
from core.services.ai.exports.document import ExportDocument, parse_markdown
from core.services.ai.exports.registry import get_format

MD = """## Getting started

Create your account first.

1. Open the app.
2. Click **Sign up**.

- Passwords need 8 characters.

### Create account

Fill the form.

#### Terms

Accept them.

## Balance

Track banks.

### Banks

| Bank | Currency |
|---|---|
| A | EGP |

## Reports

Totals per month <b>x</b>.
"""


def doc(md=MD, lang="en", title="WealthFlow User Guide"):
    return ExportDocument(title=title, generated="Generated on 21 October 2026", lang=lang, blocks=parse_markdown(md), source=md)


class GuideHtmlTest(SimpleTestCase):
    def test_structure_contents_links_and_numbers(self):
        html = build_guide_html(doc(), "en").decode()
        ids = set(re.findall(r'id="([^"]+)"', html))
        hrefs = re.findall(r'href="#([^"]+)"', html)
        self.assertTrue(set(hrefs) - {"main-content"} <= ids)                        # every contents link has a target
        self.assertEqual(len(re.findall(r'<section id="sec-\d+-', html)), 3)
        for n, title in enumerate(("Getting started", "Balance", "Reports"), 1):
            self.assertIn(f">{n} {title}</a>", html)                                 # numbered contents entries ...
            self.assertIn(f'class="section-heading">{n} {title}</h2>', html)         # ... and chapter headings
        self.assertIn('<ol class="steps"><li>Open the app.</li><li>Click <strong>Sign up</strong>.</li></ol>', html)
        self.assertIn('<ul class="notes"><li>Passwords need 8 characters.</li></ul>', html)
        self.assertIn('<h4 id="sec-1-2-terms" class="sub-heading l4">Terms</h4>', html)
        self.assertIn("<table>", html)
        self.assertIn("<title>WealthFlow User Guide</title>", html)
        self.assertIn("IntersectionObserver", html)                                  # the chapter being read is highlighted
        self.assertNotIn("http://", html.replace("http://www.w3.org", ""))             # self-contained: no network

    def test_text_is_escaped(self):
        html = build_guide_html(doc(), "en").decode()
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", html)
        self.assertNotIn("<b>x</b>", html)

    def test_repeated_paragraphs_are_rendered_once_across_chapters(self):
        text = "Track bank certificate maturity schedules and expected interest yields."
        html = build_guide_html(doc(f"## Certificates\n\n{text}\n\n## Reports\n\n{text}\n"), "en").decode()
        self.assertEqual(html.count(text), 1)

    def test_arabic_is_right_to_left_with_arabic_labels_and_anchors(self):
        md = "## البدء\n\nنص.\n\n### إنشاء حساب\n\nنص.\n\n## الرصيد\n\nنص.\n\n## التقارير\n\nنص.\n"
        html = build_guide_html(doc(md, "ar", "دليل WealthFlow"), "ar").decode()
        self.assertIn('<html lang="ar" dir="rtl">', html)
        self.assertIn("المحتويات", html)
        self.assertIn('id="sec-1-البدء"', html)

    def test_only_a_multi_chapter_document_is_a_guide(self):
        self.assertTrue(is_guide(doc()))
        self.assertFalse(is_guide(doc("## One\n\ntext\n\n## Two\n\ntext\n")))
        self.assertFalse(is_guide(doc("## A\n\n```html\n<p>x</p>\n```\n\n## B\n\nx\n\n## C\n\ny\n")))

    def test_the_html_format_builds_a_guide_and_keeps_code_as_code(self):
        fmt = get_format("html")
        self.assertIn(b'class="toc-rail"', fmt.builder(doc(), "en"))
        code = ExportDocument(title="T", blocks=parse_markdown("Here:\n```html\n<p>hi</p>\n```"), source="Here:\n```html\n<p>hi</p>\n```")
        self.assertEqual(fmt.builder(code, "en"), b"<p>hi</p>\n")

    def test_html_guide_wording_is_detected_as_a_request(self):
        from core.services.ai.exports.intent import detect

        for text in (
            "generate an html user guide for the app",
            "make the guide as an html document",
            "اكتب دليل مستخدم للتطبيق بصيغة HTML",
            "Rédige un guide utilisateur en HTML pour l’application",
            "Schreibe eine HTML-Bedienungsanleitung für die App",
        ):
            with self.subTest(text=text):
                self.assertIn("html", [f.key for f in detect(text)])
