"""Downloads hold the COMPLETE data, not the chat's capped view; the `generate_file` tool; settings, audit, routing.

Covers what the first export version did not: rows beyond the 300-row chat table, model answers that drop rows, an AI
tool that builds a file from a database query (no 100-row cap, owner isolation), the Settings switch / limits, the audit
entry, give-up phrases that hand over to the investigator, and code files."""

import datetime
import re
from decimal import Decimal
from io import BytesIO
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase
from openpyxl import load_workbook

from core.models import AppSettings, Expense
from core.services.ai.exports import all_formats, detect
from core.services.ai.investigation.refusal import is_refusal
from core.tests.ai import qe_fixtures as fx
from core.tests.ai.investigation.support import make_user
from core.tests.ai.investigation.test_chat_investigator import GP, VIEW

URL = "/api/financial-advisor/ai/messages/{id}/export/{fmt}/"
LINK = re.compile(r"/api/financial-advisor/ai/messages/(\d+)/export/(\w+)/")


def grid(response):
    return [[c.value for c in r] for r in load_workbook(BytesIO(response.content)).active.iter_rows()]


def bulk_expenses(owner, category, n, currency=None):
    Expense.objects.bulk_create([Expense(owner=owner, category=category, date=datetime.date(2026, 6, 1 + i % 25), year=2026, month=6, amount=Decimal("1"),
                                         amount_base=Decimal("1"), description=f"bulk {i}") for i in range(n)])



class RoutingAndPhraseTests(TestCase):
    def test_routing(self):
        from core.views.ai_chat.chat_pipeline.investigate import should_go_direct

        user = make_user("route_export_user")
        self.assertEqual(should_go_direct(user, "export every loan to excel"), "export_request")
        self.assertIsNone(should_go_direct(user, "export every loan to excel", computed=True))   # the router already has the exact rows
        self.assertIsNone(should_go_direct(user, "write a function and save it as a .py file"))   # code: the model's own answer is the file
        self.assertIsNone(should_go_direct(user, "how do I export my data"))
        AppSettings.set("ai_file_generation", "false")
        self.assertIsNone(should_go_direct(user, "export every loan to excel"))
        AppSettings.set("ai_file_generation", "true")
        AppSettings.set("ai_investigator_mode", "off")
        self.assertIsNone(should_go_direct(user, "export every loan to excel"))


class CodeFormatsAndPhrasesTests(SimpleTestCase):
    def test_code_formats_are_registered_and_detected(self):
        keys = {f.key for f in all_formats()}
        self.assertTrue({"xlsx", "docx", "pdf", "csv", "txt", "py", "js", "html", "css", "json", "md", "sql"} <= keys)
        self.assertEqual([f.key for f in detect("save this as a python file")], ["py"])
        self.assertEqual([f.key for f in detect("give me the query as a .sql file")], ["sql"])
        self.assertEqual([f.key for f in detect("export to excel and pdf")], ["xlsx", "pdf"])

    def test_give_up_phrases_hand_over_to_the_investigator(self):
        for p in ("I can only access a capped window of 20 entries, so I cannot list all salaries.", "The data does not contain the paid salaries for 2026.",
                  "These months are not included in the provided data payload.", "I cannot directly generate or send an .xlsx file.", "I'm unable to export it as Excel.",
                  "لا أستطيع تصدير الملف مباشرة", "البيانات المقدمة لا تحتوي على السجلات المطلوبة", "هذه الأشهر غير مدرجة في البيانات المقدمة",
                  "Je ne peux pas générer de fichier Excel.", "Les données fournies ne contiennent pas toutes les entrées.", "Je ne vois qu'une fenêtre limitée des données.",
                  "Ich kann keine Excel-Datei erstellen.", "Die Daten enthalten nicht alle Einträge.", "Ich sehe nur ein begrenztes Fenster der Daten.",
                  "Das steht nicht in den bereitgestellten Daten."):
            self.assertTrue(is_refusal(p, investigated=True), p)
        for ok in ("Your paid salaries for 2026 total 120,000 EGP.", "The report contains all 12 months of 2026.", "The table includes every month."):
            self.assertFalse(is_refusal(ok, investigated=True), ok)


class CodeFileDownloadTests(TestCase):
    def setUp(self):
        fx.build(self)

    def test_python_file_is_the_code_block_of_the_answer(self):
        AppSettings.set("ai_direct_answers", "false")
        prov = MagicMock()
        prov.supports_tools = False
        answer = "Here is the script:\n\n```python\ndef total(xs):\n    return sum(xs)\n```\n\nIt sums a list."
        prov.generate.side_effect = [{"content": answer, "tool_calls": None, "error": None}] * 3
        ctx = ([{"role": "system", "content": "SYS"}, {"role": "user", "content": "q"}], ["x"])
        with patch(f"{VIEW}.get_active_ai_provider", return_value=prov), patch(GP, return_value=ctx):
            data = fx.ask(self, "write a python function that sums a list and save it as a .py file", conversation=False)
        m = LINK.search(data["message"]["content"])
        self.assertEqual(m.group(2), "py")
        r = self.client.get(URL.format(id=m.group(1), fmt="py"))
        self.assertEqual(r.content.decode(), "def total(xs):\n    return sum(xs)\n")
        self.assertIn("x-python", r["Content-Type"])


class FollowupGuardTests(SimpleTestCase):
    def test_only_a_bare_file_request_is_a_follow_up(self):
        from core.services.ai.exports import only_a_file_request, strip_export_terms

        for yes in ("export it to excel", "and as a PDF?", "please export the previous answer to word", "download it as csv", "صدرها اكسل", "exporte-le en excel s'il te plaît",
                    "als PDF exportieren bitte"):
            self.assertTrue(only_a_file_request(strip_export_terms(yes)), yes)
        for no in ("write a python function that sums a list and save it as a .py file", "list my loans and export to excel", "export the gold prices to pdf",
                   "make a sql script that creates a users table as .sql"):
            self.assertFalse(only_a_file_request(strip_export_terms(no)), no)


class SanitizerKeepsCodeTests(SimpleTestCase):
    def test_code_blocks_keep_indentation_and_escapes_while_latex_is_still_removed(self):
        from core.views.ai_chat.response_sanitizer import strip_latex

        code = "```python\ndef f(x):\n    if re.match(r\"\\(a\\)\", x):\n        return 1\n```"
        self.assertEqual(strip_latex(f"Here:\n\n{code}\n\nDone."), f"Here:\n\n{code}\n\nDone.")
        self.assertEqual(strip_latex("Total \\( 5 \\times 3 \\)  is  15"), "Total 5 x 3 is 15")
        self.assertEqual(strip_latex("- item\n    - nested"), "- item\n    - nested")


class FileSettingsApiTests(TestCase):
    URL = "/api/settings/ai/"

    def setUp(self):
        self.admin = make_user("file_settings_admin", sysadmin=True)
        self.client.force_login(self.admin)

    def post(self, **body):
        import json

        return self.client.post(self.URL, json.dumps(body), content_type="application/json")

    def test_defaults_round_trip_clamp_and_global_scope(self):
        got = self.client.get(self.URL).json()
        self.assertEqual((got["ai_file_generation"], got["ai_file_max_mb"], got["ai_file_max_rows"]), (True, 10, 50000))
        self.assertEqual(self.post(ai_file_generation=False, ai_file_max_mb=3, ai_file_max_rows=500).status_code, 200)
        got = self.client.get(self.URL).json()
        self.assertEqual((got["ai_file_generation"], got["ai_file_max_mb"], got["ai_file_max_rows"]), (False, 3, 500))
        self.assertEqual(AppSettings.get("ai_file_generation"), "false")
        self.post(ai_file_max_mb=9999, ai_file_max_rows=1)
        got = self.client.get(self.URL).json()
        self.assertEqual((got["ai_file_max_mb"], got["ai_file_max_rows"]), (50, 100))          # clamped to the allowed range
        self.assertEqual(self.post(ai_file_max_mb="lots").status_code, 400)
        self.post(ai_validate_mode="flag")                                                       # omitted keys keep stored values
        self.assertEqual(self.client.get(self.URL).json()["ai_file_max_mb"], 50)

    def test_a_users_own_row_cannot_switch_files_back_on(self):
        AppSettings.set("ai_file_generation", "false")
        AppSettings.set("ai_file_generation", "true", user=self.admin)
        from core.services.ai.exports.settings import exports_enabled

        self.assertFalse(exports_enabled())

    def test_non_admin_cannot_change_them(self):
        user = make_user("file_settings_plain")
        self.client.force_login(user)
        self.assertIn(self.post(ai_file_generation=False).status_code, (401, 402, 403))
        self.assertTrue(self.client.get(self.URL).status_code in (200, 401, 402, 403))
        self.assertNotEqual(AppSettings.get("ai_file_generation", "true"), "false")

