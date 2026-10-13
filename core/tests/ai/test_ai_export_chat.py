"""Downloadable answers in the chat: links on every topic (instant answers and model answers), "export it"
follow-ups, the download endpoint's ownership rules, and the chat's link rendering."""

import shutil
import subprocess
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import SimpleTestCase, TestCase
from docx import Document
from openpyxl import load_workbook

from core.integrations.ai_provider import OllamaProvider
from core.models import AIMessage, AppSettings
from core.tests.billing.test_support import grant_ai_workspace_access
from . import qe_fixtures as fx

NO_LLM = patch.object(OllamaProvider, "generate", side_effect=AssertionError("LLM must not be called"))
GP = "core.views.ai_chat.ai_chat_core_views.generation_pipeline.build_context"
VIEW = "core.views.ai_chat.ai_chat_core_views"
URL = "/api/financial-advisor/ai/messages/{id}/export/{fmt}/"
MIME = {"xlsx": "spreadsheetml", "docx": "wordprocessingml", "pdf": "application/pdf", "csv": "text/csv", "txt": "text/plain"}
# (question, format, text the downloaded file must contain). Topics: salary, gold, exchange rates, expenses, balance, certificates, assets.
TOPICS = [
    ("please list the paid salaries for year 2026, and export it in excel sheet", "xlsx", "87643.86"),
    ("export the gold prices to pdf", "pdf", ""),
    ("download exchange rates as word", "docx", "USD"),
    ("list my expenses for June 2026 and export to excel", "xlsx", "Rice"),
    ("what is my total balance, save it as csv", "csv", "1,000.00"),
    ("show my certificates as a text file", "txt", "100,000"),
    ("list my fixed assets and export to pdf", "pdf", ""),
]


def link_ids(content):
    import re

    return re.findall(r"/api/financial-advisor/ai/messages/(\d+)/export/(\w+)/", content)


def file_text(fmt, body):
    if fmt == "xlsx":
        return " ".join(str(c.value) for row in load_workbook(BytesIO(body)).active.iter_rows() for c in row if c.value is not None)
    if fmt == "docx":
        doc = Document(BytesIO(body))
        return " ".join([p.text for p in doc.paragraphs] + [c.text for t in doc.tables for r in t.rows for c in r.cells])
    return body.decode("utf-8", "ignore") if fmt in ("csv", "txt") else ""


class ChatExportTests(TestCase):
    def setUp(self):
        fx.build(self)

    def download(self, message_id, fmt, client=None):
        return (client or self.client).get(URL.format(id=message_id, fmt=fmt))

    def test_every_topic_gets_working_links_without_calling_the_model(self):
        for question, fmt, needle in TOPICS:
            with self.subTest(question=question), NO_LLM as gen:
                data = fx.ask(self, question, conversation=False)
                content = data["message"]["content"]
                self.assertEqual(link_ids(content), [(str(data["message"]["id"]), fmt)])
                gen.assert_not_called()
                res = self.download(data["message"]["id"], fmt)
                self.assertEqual(res.status_code, 200)
                self.assertIn(MIME[fmt], res["Content-Type"])
                self.assertIn(f".{fmt}", res["Content-Disposition"])
                self.assertGreater(len(res.content), 100)
                self.assertIn(needle, file_text(fmt, res.content))
                if fmt in ("xlsx", "docx", "csv", "txt"):
                    self.assertNotIn("/export/", file_text(fmt, res.content))

    def test_named_formats_and_the_default_set(self):
        with NO_LLM:
            both = fx.ask(self, "list salaries 2026, export to pdf and word", conversation=False)["message"]["content"]
            default = fx.ask(self, "list salaries 2026 and export it", conversation=False)["message"]["content"]
            none = fx.ask(self, "list salaries 2026", conversation=False)["message"]["content"]
        self.assertEqual([f for _, f in link_ids(both)], ["docx", "pdf"])
        self.assertEqual([f for _, f in link_ids(default)], ["xlsx", "docx", "pdf"])
        self.assertEqual(link_ids(none), [])

    def test_link_text_follows_the_question_language(self):
        with NO_LLM:
            ar = fx.ask(self, "اعرض رواتب 2026 وصدرها في ملف اكسل", conversation=False)["message"]["content"]
            fr = fx.ask(self, "liste mes salaires 2026 et exporte en excel", conversation=False)["message"]["content"]
            de = fx.ask(self, "Gehälter 2026 auflisten und als Excel herunterladen", conversation=False)["message"]["content"]
        self.assertIn("[تنزيل بصيغة Excel (.xlsx)]", ar)
        self.assertIn("[Télécharger en Excel (.xlsx)]", fr)
        self.assertIn("[Als Excel (.xlsx) herunterladen]", de)

    def test_bare_export_follows_up_on_the_previous_answer_without_the_model(self):
        with NO_LLM as gen:
            first = fx.ask(self, "list the paid salaries for year 2026")["message"]
            pdf = fx.ask(self, "export it to pdf")["message"]
            word = fx.ask(self, "and as word?")["message"]
            gen.assert_not_called()
        for follow, fmt in ((pdf, "pdf"), (word, "docx")):
            self.assertEqual(link_ids(follow["content"]), [(str(first["id"]), fmt)])
            self.assertIn("Download the previous answer", follow["content"])
            self.assertEqual(follow["tool_calls"][0]["tool"], "export_followup")
        body = self.download(first["id"], "docx").content
        self.assertIn("87,643.86 EGP", file_text("docx", body))

    def test_follow_up_with_nothing_to_export(self):
        with NO_LLM:
            content = fx.ask(self, "export it to excel")["message"]["content"]
        self.assertIn("no earlier answer", content)
        self.assertEqual(link_ids(content), [])

    def test_a_data_topic_is_not_mistaken_for_a_follow_up(self):
        with NO_LLM:
            fx.ask(self, "list the paid salaries for year 2026")
            content = fx.ask(self, "export the gold prices to pdf")["message"]["content"]
        self.assertIn("Gold", content)
        self.assertNotIn("Download the previous answer", content)

    def test_ownership_and_validation(self):
        with NO_LLM:
            msg = fx.ask(self, "list salaries 2026 and export to excel", conversation=False)["message"]
        self.assertEqual(self.download(msg["id"], "xlsx").status_code, 200)
        self.assertEqual(self.download(msg["id"], "exe").status_code, 404)
        self.assertEqual(self.download(msg["id"] + 999, "xlsx").status_code, 404)
        user_msg = AIMessage.objects.filter(role="user").first()
        self.assertEqual(self.download(user_msg.id, "xlsx").status_code, 404)
        grant_ai_workspace_access(self.other)
        self.client.force_login(self.other)
        self.assertEqual(self.download(msg["id"], "xlsx").status_code, 404)
        self.client.logout()
        self.assertIn(self.download(msg["id"], "xlsx").status_code, (401, 403))

    def test_deleted_messages_and_conversations_cannot_be_downloaded(self):
        with NO_LLM:
            msg = fx.ask(self, "list salaries 2026 and export to excel", conversation=False)["message"]
        AIMessage.objects.filter(id=msg["id"]).update(is_deleted=True)
        self.assertEqual(self.download(msg["id"], "xlsx").status_code, 404)

    def test_model_path_gets_the_same_links_and_a_notice(self):
        """Direct Answers OFF: the model answers; the app still attaches the links and tells the model it will."""
        AppSettings.set("ai_direct_answers", "false")
        prov = MagicMock()
        prov.supports_tools = False
        answer = "| Month | Paid |\n|---|---|\n| Jan 2026 | 87,643.86 EGP |"
        prov.generate.side_effect = [{"content": answer, "tool_calls": None, "error": None}] * 3
        ctx = ([{"role": "system", "content": "SYS"}, {"role": "user", "content": "q"}], ["salary"])
        with patch(f"{VIEW}.get_active_ai_provider", return_value=prov), patch(GP, return_value=ctx):
            data = fx.ask(self, "list the salaries for 2026 and export it in excel", conversation=False)
        content = data["message"]["content"]
        self.assertEqual(link_ids(content), [(str(data["message"]["id"]), "xlsx")])
        self.assertIn("FILE EXPORT", prov.generate.call_args[0][0][0]["content"])
        ws = load_workbook(BytesIO(self.download(data["message"]["id"], "xlsx").content)).active
        self.assertIn(87643.86, [c.value for row in ws.iter_rows() for c in row])


class ChatMarkdownLinkTests(SimpleTestCase):
    """static/js/ai/ai_markdown.js renders the app's download links and nothing external."""

    def render(self, text):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        js = Path(settings.BASE_DIR, "static/js/ai/ai_markdown.js").read_text(encoding="utf-8")
        return subprocess.run([node, "-e", js + "\nprocess.stdout.write(_renderMarkdown(process.argv[1]));", text],
                              capture_output=True, text=True, check=True).stdout

    def test_download_links_become_anchors_side_by_side(self):
        html = self.render("[Download as Excel (.xlsx)](/api/x/export/xlsx/) · [Download as PDF (.pdf)](/api/x/export/pdf/)")
        self.assertEqual(html.count('<a class="ai-ws-link"'), 2)
        self.assertIn('href="/api/x/export/pdf/" download', html)

    def test_external_and_script_links_stay_text(self):
        self.assertNotIn("<a ", self.render("[a](https://evil.example/x) [b](javascript:alert(1)) [c](//evil.example)"))
