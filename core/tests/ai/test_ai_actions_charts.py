"""AI actions with confirmation (add / edit / delete) and charts from real data."""

import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import AIChatBlock, AIConversation, AIMessage, Currency, Expense, ExpenseCategory, ReminderRule
from core.services.ai.actions import attach_blocks, decide, propose_action
from core.services.ai.actions.charts import show_chart
from core.services.ai.tools import validate_and_execute_tool
from core.tests.billing.test_support import grant_ai_workspace_access

User = get_user_model()
API = "/api/financial-advisor/ai/"


class Base(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="member", password="pw12345!")
        self.other = User.objects.create_user(username="other", password="pw12345!")
        grant_ai_workspace_access(self.user)
        grant_ai_workspace_access(self.other)
        self.egp, _ = Currency.objects.get_or_create(owner=self.user, code="EGP", defaults={"name": "Pound"})
        self.cat, _ = ExpenseCategory.objects.get_or_create(owner=self.user, name="Food")
        self.client.force_login(self.user)

    def expense(self, amount="100", day=None, desc="lunch", owner=None):
        d = day or datetime.date(2026, 3, 5)
        return Expense.objects.create(owner=owner or self.user, date=d, year=d.year, month=d.month, category=self.cat, description=desc,
                                      amount=Decimal(amount), amount_base=Decimal(amount), currency=self.egp, payment_method="Other")


class ProposeNeverWritesTests(Base):
    def test_add_expense_proposal_creates_card_but_no_expense(self):
        res = propose_action(self.user, {"record": "expense", "op": "add", "values": {"amount": "200", "currency": "EGP", "description": "coffee", "category": "Food", "payment_method": "Other"}})
        self.assertTrue(res["pending_confirmation"])
        self.assertEqual(Expense.objects.count(), 0)
        block = AIChatBlock.objects.get()
        self.assertEqual((block.status, block.payload["op"]), ("pending", "add"))

    def test_missing_amount_and_unknown_category_return_errors_for_the_model(self):
        self.assertIn("amount", propose_action(self.user, {"record": "expense", "op": "add", "values": {"description": "x"}})["error"])
        err = propose_action(self.user, {"record": "expense", "op": "add", "values": {"amount": "5", "category": "Nope"}})["error"]
        self.assertIn("Food", err)
        self.assertEqual(AIChatBlock.objects.count(), 0)

    def test_bad_amounts_rejected(self):
        for bad in ("abc", "-5", "0", "NaN", "1e99"):
            self.assertIn("error", propose_action(self.user, {"record": "expense", "op": "add", "values": {"amount": bad}}), bad)

    def test_tool_runs_through_the_registry_in_read_only_mode(self):
        audit, result = validate_and_execute_tool("propose_action", {"record": "reminder", "op": "add", "values": {"name": "Rent"}}, self.user)
        self.assertEqual(audit["status"], "success")
        self.assertTrue(result["data"]["pending_confirmation"])
        self.assertEqual(ReminderRule.objects.count(), 0)


class ConfirmTests(Base):
    def card(self, **kw):
        return AIChatBlock.objects.get(pk=propose_action(self.user, kw)["card_id"])

    def test_confirm_adds_the_expense_for_the_owner_only(self):
        b = self.card(record="expense", op="add", values={"amount": "200", "currency": "EGP", "description": "coffee", "category": "Food", "payment_method": "Other", "date": "2026-03-05"})
        res = self.client.post(API + f"blocks/{b.id}/confirm/")
        self.assertEqual(res.status_code, 200)
        exp = Expense.objects.get()
        self.assertEqual((exp.owner, exp.amount, exp.description, exp.month), (self.user, Decimal("200.00"), "coffee", 3))
        self.assertEqual(res.json()["block"]["status"], "confirmed")

    def test_cancel_changes_nothing_and_a_card_is_decided_once(self):
        b = self.card(record="reminder", op="add", values={"name": "Rent"})
        self.assertEqual(self.client.post(API + f"blocks/{b.id}/cancel/").json()["block"]["status"], "cancelled")
        self.assertEqual(self.client.post(API + f"blocks/{b.id}/confirm/").status_code, 409)
        self.assertEqual(ReminderRule.objects.count(), 0)

    def test_confirm_twice_never_duplicates(self):
        b = self.card(record="reminder", op="add", values={"name": "Rent"})
        self.client.post(API + f"blocks/{b.id}/confirm/")
        self.assertEqual(self.client.post(API + f"blocks/{b.id}/confirm/").status_code, 409)
        self.assertEqual(ReminderRule.objects.count(), 1)

    def test_other_user_cannot_decide_my_card(self):
        b = self.card(record="reminder", op="add", values={"name": "Rent"})
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(API + f"blocks/{b.id}/confirm/").status_code, 404)
        self.assertEqual(AIChatBlock.objects.get(pk=b.id).status, "pending")

    def test_failed_save_is_reported_not_raised(self):
        b = self.card(record="expense", op="add", values={"amount": "200", "currency": "EGP", "payment_method": "Card"})
        res = self.client.post(API + f"blocks/{b.id}/confirm/")
        self.assertEqual(res.json()["block"]["status"], "failed")
        self.assertEqual(Expense.objects.count(), 0)


class EditDeleteTests(Base):
    def test_edit_shows_before_after_and_applies_on_confirm(self):
        e = self.expense("100", desc="lunch")
        res = propose_action(self.user, {"record": "expense", "op": "edit", "target": {"id": e.id}, "values": {"description": "dinner"}})
        block = AIChatBlock.objects.get(pk=res["card_id"])
        self.assertEqual(block.payload["rows"], [{"label": "description", "before": "lunch", "after": "dinner"}])
        self.assertEqual(Expense.objects.get().description, "lunch")
        decide(self.user, block.id, True)
        self.assertEqual(Expense.objects.get().description, "dinner")

    def test_ambiguous_target_asks_instead_of_guessing(self):
        self.expense("100")
        self.expense("100", desc="lunch again")
        err = propose_action(self.user, {"record": "expense", "op": "delete", "target": {"amount": "100"}, "values": {}})["error"]
        self.assertIn("2 expenses match", err)
        self.assertEqual(AIChatBlock.objects.count(), 0)

    def test_delete_removes_only_my_expense_and_never_someone_elses(self):
        mine, theirs = self.expense("100"), self.expense("100", owner=self.other)
        err = propose_action(self.user, {"record": "expense", "op": "delete", "target": {"id": theirs.id}})["error"]
        self.assertIn("no expense matches", err)
        res = propose_action(self.user, {"record": "expense", "op": "delete", "target": {"id": mine.id}})
        decide(self.user, res["card_id"], True)
        self.assertEqual(list(Expense.objects.values_list("id", flat=True)), [theirs.id])

    def test_reminder_edit_and_delete(self):
        r = ReminderRule.objects.create(owner=self.user, name="Rent", rule_type="custom")
        res = propose_action(self.user, {"record": "reminder", "op": "edit", "target": {"name": "Rent"}, "values": {"name": "Rent day", "days_before": 3}})
        decide(self.user, res["card_id"], True)
        r.refresh_from_db()
        self.assertEqual((r.name, r.days_before), ("Rent day", 3))
        res = propose_action(self.user, {"record": "reminder", "op": "delete", "target": {"id": r.id}})
        decide(self.user, res["card_id"], True)
        self.assertEqual(ReminderRule.objects.count(), 0)

    def test_salary_add_is_refused(self):
        self.assertIn("generated", propose_action(self.user, {"record": "income", "op": "add", "values": {"paid": "1"}})["error"])


class AttachTests(Base):
    def test_blocks_made_while_answering_attach_to_the_answer_and_come_back_in_history(self):
        conv = AIConversation.objects.create(user=self.user)
        um = AIMessage.objects.create(conversation=conv, role="user", content="add coffee 5")
        propose_action(self.user, {"record": "reminder", "op": "add", "values": {"name": "x"}})
        am = AIMessage.objects.create(conversation=conv, role="assistant", content="Please confirm")
        attach_blocks(self.user, um.created_at, am)
        data = self.client.get(API + f"conversations/{conv.id}/").json()["conversation"]["messages"]
        self.assertEqual([len(m["blocks"]) for m in data], [0, 1])


class ChartTests(Base):
    def test_chart_numbers_come_from_the_database(self):
        self.expense("100")
        self.expense("300", day=datetime.date(2026, 4, 1))
        res = show_chart(self.user, {"chart": "expenses_by_month", "year": 2026})
        self.assertEqual(res["values"][2:4], [100.0, 300.0])
        self.assertEqual(res["unit"] if "unit" in res else AIChatBlock.objects.get().payload["unit"], "EGP")

    def test_category_pie_for_one_month_and_other_users_data_excluded(self):
        self.expense("100")
        self.expense("999", owner=self.other)
        res = show_chart(self.user, {"chart": "expenses_by_category", "year": 2026, "month": 3})
        self.assertEqual((res["labels"], res["values"]), (["Food"], [100.0]))

    def test_no_data_means_no_chart(self):
        self.assertIn("error", show_chart(self.user, {"chart": "expenses_by_month", "year": 1999}))
        self.assertEqual(AIChatBlock.objects.count(), 0)

    def test_unknown_chart_rejected(self):
        self.assertIn("error", show_chart(self.user, {"chart": "bitcoin"}))
