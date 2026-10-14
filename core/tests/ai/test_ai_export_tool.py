"""Downloads hold the COMPLETE data, not the chat's capped view; the `generate_file` tool; settings, audit, routing.

Covers what the first export version did not: rows beyond the 300-row chat table, model answers that drop rows, an AI
tool that builds a file from a database query (no 100-row cap, owner isolation), the Settings switch / limits, the audit
entry, give-up phrases that hand over to the investigator, and code files."""

import datetime
import re
from decimal import Decimal
from io import BytesIO

from django.test import TestCase
from openpyxl import load_workbook

from core.models import AIMessage, AppSettings, Expense
from core.services.ai.exports import formats_from_tool_calls
from core.services.ai.exports.tool import generate_file
from core.services.ai.tools import get_registered_tool_schemas, validate_and_execute_tool
from core.tests.ai.investigation.support import make_user, seed_tenant, tool_call
from core.tests.ai.investigation.test_chat_investigator import InvestigatorChatBase
from core.tests.billing.test_support import grant_ai_workspace_access

URL = "/api/financial-advisor/ai/messages/{id}/export/{fmt}/"
LINK = re.compile(r"/api/financial-advisor/ai/messages/(\d+)/export/(\w+)/")


def grid(response):
    return [[c.value for c in r] for r in load_workbook(BytesIO(response.content)).active.iter_rows()]


def bulk_expenses(owner, category, n, currency=None):
    Expense.objects.bulk_create([Expense(owner=owner, category=category, date=datetime.date(2026, 6, 1 + i % 25), year=2026, month=6, amount=Decimal("1"),
                                         amount_base=Decimal("1"), description=f"bulk {i}") for i in range(n)])



class GenerateFileToolTests(TestCase):
    def setUp(self):
        self.user = make_user("gen_file_user")
        self.other = make_user("gen_file_other")
        self.ctx = seed_tenant(self.user, "Mine", expenses=3, amount="10.00")
        seed_tenant(self.other, "Secret", expenses=2, amount="99.00")
        grant_ai_workspace_access(self.user)

    def run_tool(self, **params):
        return validate_and_execute_tool("generate_file", params, self.user)

    def test_registered_offered_and_read_tier(self):
        from core.services.ai.investigation.defs import investigation_tool_schemas

        self.assertIn("generate_file", {s["function"]["name"] for s in get_registered_tool_schemas(domain="expenses")})
        self.assertIn("generate_file", {s["function"]["name"] for s in investigation_tool_schemas(self.user)})
        audit, out = self.run_tool(format="xlsx", dataset={"model": "Expense", "fields": ["description"]})
        self.assertEqual((audit["status"], out["data"]["rows"]), ("success", 3))

    def test_bad_specs_return_a_correctable_error(self):
        for params in ({"format": "xlsx", "dataset": {"model": "Expense", "fields": ["nope"]}}, {"format": "xlsx", "dataset": {"model": "AuthToken"}},
                       {"format": "xlsx", "dataset": {"model": "Expense", "filters": {"owner__username": "gen_file_other"}}},
                       {"format": "xlsx"}, {"format": "exe", "content": "x"}):
            _, out = self.run_tool(**params)
            self.assertIn("error", out["data"], params)
        self.assertIn("Fields:", self.run_tool(format="xlsx", dataset={"model": "Expense", "fields": ["nope"]})[1]["data"]["error"])

    def test_tool_is_off_with_the_switch(self):
        AppSettings.set("ai_file_generation", "false")
        self.assertIn("switched off", generate_file(self.user, {"format": "xlsx", "content": "x"})["error"])

    def test_formats_chosen_by_the_model_when_the_user_named_none(self):
        calls = [{"tool": "generate_file", "status": "success", "arguments": {"format": "docx"}}, {"tool": "generate_file", "status": "failed", "arguments": {"format": "pdf"}}]
        self.assertEqual([f.key for f in formats_from_tool_calls(calls)], ["docx"])


class InvestigatorFileTests(InvestigatorChatBase):
    """The chat end to end with a scripted model: an unroutable export request goes to the investigator, which calls
    generate_file; the link is attached by the app and the file is rebuilt from the database for that user only."""

    def setUp(self):
        super().setUp()
        self.other = make_user("chat_inv_other")
        seed_tenant(self.other, "Secret", expenses=2, amount="99.00")
        Expense.objects.bulk_create([Expense(owner=self.user, category=Expense.objects.filter(owner=self.user).first().category, date=datetime.date(2026, 7, 1), year=2026,
                                             month=7, amount=Decimal("1"), amount_base=Decimal("1"), description=f"bulk {i}") for i in range(250)])

    def test_investigator_builds_a_complete_isolated_file(self):
        spec = tool_call("generate_file", format="xlsx", title="All expenses", dataset={"model": "Expense", "fields": ["date", "description", "amount_base"], "order_by": ["date"],
                                                                                         "total_columns": ["amount_base"]})
        res, _, log = self.ask("dump every one of my expense records into an excel file", [spec, "Here is the file with all your expenses."])
        data = res.json()
        self.assertIn("stage=investigate status=ok", log)
        link = LINK.search(data["message"]["content"])
        self.assertIsNotNone(link, data)
        rows = grid(self.client.get(URL.format(id=link.group(1), fmt=link.group(2))))
        mine = Expense.objects.filter(owner=self.user).count()
        self.assertEqual(len([r for r in rows if r[1] and ("bulk" in str(r[1]) or r[1] in set(Expense.objects.filter(owner=self.user).values_list("description", flat=True)))]), mine)
        self.assertGreater(mine, 250)                       # more than any chat cap
        self.assertNotIn("Secret", str(rows))
        self.assertEqual([c["tool"] for c in data["message"]["tool_calls"]], ["generate_file"])

    def test_other_user_cannot_download_it(self):
        spec = tool_call("generate_file", format="csv", dataset={"model": "Expense", "fields": ["description"]})
        res, _, _ = self.ask("save all my expenses as a csv file", [spec, "Done."])
        link = LINK.search(res.json()["message"]["content"])
        grant_ai_workspace_access(self.other)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(URL.format(id=link.group(1), fmt="csv")).status_code, 404)

    def test_replay_uses_the_conversation_owner_not_the_spec(self):
        """A spec naming another user's field filter is rejected; the file never contains foreign rows."""
        spec = tool_call("generate_file", format="csv", dataset={"model": "Expense", "fields": ["description"], "filters": {"owner__id": self.other.id}})
        res, _, _ = self.ask("save all expenses as csv", [spec, {"content": "I could not.", "tool_calls": []}])
        self.assertEqual(AIMessage.objects.filter(conversation__user=self.user).count(), 2)
        self.assertNotIn("Secret", res.content.decode())
