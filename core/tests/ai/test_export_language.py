"""A document follows the language of its own text: an English request for a guide written in Arabic downloads right-to-left."""

from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from docx import Document

from core.services.ai.exports import build
from core.services.ai.exports.registry import get_format

AR_GUIDE = "# دليل المستخدم\n\n## مقدمة\n\nهذا الدليل يشرح كيفية استخدام التطبيق.\n\n- خطوة أولى\n- خطوة ثانية"


class ExportLanguageTest(SimpleTestCase):
    def doc(self, question, content):
        message = SimpleNamespace(content=content, conversation=SimpleNamespace(user=None))
        with patch.object(build, "_question_row", return_value=(1, question)), patch.object(build, "_previous_question", return_value=""), \
             patch.object(build, "from_tool_calls", return_value=None), patch.object(build, "from_question", return_value=None):
            return build.document_for(message)

    def test_an_english_request_for_an_arabic_document_is_right_to_left(self):
        doc = self.doc("write the user guide as a Word document in Arabic", AR_GUIDE)
        self.assertEqual(doc.lang, "ar")
        xml = Document(BytesIO(get_format("docx").builder(doc, doc.lang))).element.xml
        self.assertIn("w:bidi", xml)

    def test_an_english_document_stays_left_to_right(self):
        doc = self.doc("write the user guide as a Word document", "# User guide\n\n## Intro\n\nThis guide explains the app.")
        self.assertEqual(doc.lang, "en")
        self.assertNotIn("w:bidi", Document(BytesIO(get_format("docx").builder(doc, doc.lang))).element.xml)
