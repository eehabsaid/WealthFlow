"""Every generated Word file ends each page with the document title and a PAGE field; Arabic files get a right-to-left footer."""

import zipfile
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from docx import Document

from core.services.ai.exports import build
from core.services.ai.exports.registry import get_format

EN = "# User guide\n\n## Intro\n\nThis guide explains the app.\n\n- one\n- two"
AR = "# دليل المستخدم\n\n## مقدمة\n\nهذا الدليل يشرح كيفية استخدام التطبيق.\n\n- خطوة أولى"
WIDE = "# Report\n\n| a | b | c | d | e | f | g | h |\n|---|---|---|---|---|---|---|---|\n| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |\n"


class DocxFooterTest(SimpleTestCase):
    def footer_xml(self, question, content):
        message = SimpleNamespace(content=content, conversation=SimpleNamespace(user=None))
        with patch.object(build, "_question_row", return_value=(1, question)), patch.object(build, "_previous_question", return_value=""), \
             patch.object(build, "from_tool_calls", return_value=None), patch.object(build, "from_question", return_value=None):
            doc = build.document_for(message)
        data = get_format("docx").builder(doc, doc.lang)
        with zipfile.ZipFile(BytesIO(data)) as z:
            names = [n for n in z.namelist() if n.startswith("word/footer")]
            return doc, data, "".join(z.read(n).decode("utf8") for n in names)

    def test_footer_has_title_and_a_page_field(self):
        doc, _, xml = self.footer_xml("write the user guide as a Word document", EN)
        self.assertIn("PAGE", xml)
        self.assertIn(doc.title, xml)
        self.assertNotIn("w:bidi", xml)

    def test_arabic_footer_is_right_to_left(self):
        doc, _, xml = self.footer_xml("write the user guide as a Word document in Arabic", AR)
        self.assertEqual(doc.lang, "ar")
        self.assertIn("w:bidi", xml)
        self.assertIn("PAGE", xml)

    def test_wide_landscape_document_keeps_the_footer_and_still_opens(self):
        _, data, xml = self.footer_xml("export the table to word", WIDE)
        self.assertIn("PAGE", xml)
        Document(BytesIO(data))
