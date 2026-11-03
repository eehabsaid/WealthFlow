"""The AI expense card is a form: category / subcategory (from the user's own Expense Categories) and every other value can be changed before Confirm."""

import json
from decimal import Decimal

from core.models import AIChatBlock, Expense, ExpenseCategory, ExpenseSubcategory
from core.services.ai.actions import propose_action
from core.tests.ai.test_ai_actions_charts import API, Base

ADD = {"record": "expense", "op": "add", "values": {"amount": "50", "currency": "EGP", "description": "coffee", "payment_method": "Other", "date": "2026-03-05"}}


class ExpenseCardFormTests(Base):
    def setUp(self):
        super().setUp()
        self.coffee = ExpenseSubcategory.objects.create(category=self.cat, name="Coffee")
        self.drinks = ExpenseCategory.objects.create(owner=self.user, name="Drinks")
        self.tea = ExpenseSubcategory.objects.create(category=self.drinks, name="Tea")

    def card(self, **over):
        return AIChatBlock.objects.get(pk=propose_action(self.user, {**ADD, **over})["card_id"])

    def confirm(self, block, edits=None):
        return self.client.post(API + f"blocks/{block.id}/confirm/", data=json.dumps({"edits": edits}), content_type="application/json")

    def test_an_add_card_is_editable_and_always_shows_category_and_subcategory(self):
        payload = self.card().payload
        labels = [r["label"] for r in payload["rows"]]
        self.assertTrue(payload["editable"])
        self.assertTrue({"category", "subcategory"} <= set(labels))
        self.assertEqual(next(r["value"] for r in payload["rows"] if r["label"] == "subcategory"), "")

    def test_the_model_can_pick_the_subcategory_by_name_from_the_users_own_list(self):
        rows = {r["label"]: r["value"] for r in self.card(values={**ADD["values"], "category": "food", "subcategory": "coffee"}).payload["rows"]}
        self.assertEqual((rows["category"], rows["subcategory"]), ("Food", "Coffee"))

    def test_a_new_subcategory_added_in_expense_categories_is_accepted_at_once(self):
        ExpenseSubcategory.objects.create(category=self.cat, name="Snacks")
        rows = {r["label"]: r["value"] for r in self.card(values={**ADD["values"], "category": "Food", "subcategory": "Snacks"}).payload["rows"]}
        self.assertEqual(rows["subcategory"], "Snacks")

    def test_unknown_subcategory_tells_the_model_the_real_ones(self):
        err = propose_action(self.user, {**ADD, "values": {**ADD["values"], "category": "Food", "subcategory": "Nope"}})["error"]
        self.assertIn("Coffee", err)

    def test_confirm_saves_what_the_user_chose_on_the_card(self):
        block = self.card()
        res = self.confirm(block, {"amount": "75.5", "description": "latte", "category": "Food", "subcategory": "Coffee", "currency": "EGP", "payment_method": "Other", "date": "2026-03-06", "bank": ""})
        self.assertEqual(res.status_code, 200)
        exp = Expense.objects.get()
        self.assertEqual((exp.amount, exp.description, exp.category, exp.subcategory, str(exp.date)), (Decimal("75.50"), "latte", self.cat, self.coffee, "2026-03-06"))
        rows = {r["label"]: r["value"] for r in res.json()["block"]["payload"]["rows"]}
        self.assertEqual((rows["amount"], rows["subcategory"]), ("75.5", "Coffee"))   # the finished card shows what was saved

    def test_changing_the_category_without_a_subcategory_clears_it(self):
        exp_data = self.confirm(self.card(), {"category": "Drinks", "subcategory": ""})
        self.assertEqual(exp_data.status_code, 200)
        exp = Expense.objects.get()
        self.assertEqual((exp.category, exp.subcategory), (self.drinks, None))

    def test_a_subcategory_of_another_category_is_refused_and_the_card_stays_pending(self):
        block = self.card()
        res = self.confirm(block, {"category": "Food", "subcategory": "Tea"})
        self.assertEqual(res.status_code, 422)
        self.assertIn("Coffee", res.json()["error"])
        block.refresh_from_db()
        self.assertEqual(block.status, "pending")
        self.assertEqual(Expense.objects.count(), 0)

    def test_values_that_are_not_in_the_users_lists_are_refused(self):
        for edits in ({"category": "Nope"}, {"currency": "XXX"}, {"payment_method": "Gold"}, {"amount": "abc"}, {"amount": "-3"}, {"date": "tomorrow"}):
            block = self.card()
            self.assertEqual(self.confirm(block, edits).status_code, 422, edits)
            block.refresh_from_db()
            self.assertEqual(block.status, "pending")
        self.assertEqual(Expense.objects.count(), 0)

    def test_another_users_category_cannot_be_used(self):
        ExpenseCategory.objects.create(owner=self.other, name="Secret")
        self.assertEqual(self.confirm(self.card(), {"category": "Secret"}).status_code, 422)

    def test_confirm_without_edits_still_saves_the_proposal_and_unknown_fields_are_ignored(self):
        res = self.confirm(self.card(), {"owner": "x", "is_readonly": "1"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Expense.objects.get().owner, self.user)

    def test_an_edit_card_lets_the_user_change_the_after_value(self):
        exp = self.expense(amount="100")
        block = AIChatBlock.objects.get(pk=propose_action(self.user, {"record": "expense", "op": "edit", "target": {"id": exp.id}, "values": {"amount": "120"}})["card_id"])
        self.assertTrue(block.payload["editable"])
        self.assertEqual(self.confirm(block, {"amount": "130", "category": "Food", "subcategory": "Coffee"}).status_code, 200)
        exp.refresh_from_db()
        self.assertEqual((exp.amount, exp.subcategory), (Decimal("130.00"), self.coffee))

    def test_cancel_never_applies_edits_and_other_cards_are_not_editable(self):
        block = self.card()
        self.client.post(API + f"blocks/{block.id}/cancel/", data=json.dumps({"edits": {"amount": "1"}}), content_type="application/json")
        self.assertEqual((AIChatBlock.objects.get(pk=block.id).status, Expense.objects.count()), ("cancelled", 0))
        rem = AIChatBlock.objects.get(pk=propose_action(self.user, {"record": "reminder", "op": "add", "values": {"name": "Rent"}})["card_id"])
        self.assertFalse(rem.payload.get("editable"))
