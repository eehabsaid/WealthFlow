"""D3: questions that must NOT be answered by an instant lookup (what-if, app help, challenging a previous answer),
the deterministic emergency-fund answer, the structure tool's real screens, and the knowledge-chunk fixes."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from core.integrations.ai_provider import OllamaProvider
from core.models import Expense, ExpenseCategory
from core.services.ai.query_engine import route
from core.services.ai.query_engine.executors.emergency import target_months

from . import qe_fixtures as fx

NO_LLM = patch.object(OllamaProvider, "generate", side_effect=AssertionError("LLM must not be called"))

WHAT_IF = [
    "What if I move 100k from cash to gold, how does my net worth change?",
    "If I sold my gold what would my total balance be",
    "Suppose I convert my savings to USD, what is the impact on my balance",
    "ماذا لو حولت مدخراتي الى ذهب",
]
APP_HELP = [
    "What happens when I delete my account?", "Which screen shows my exchange rates?", "Where do I change my default currency?",
    "where can I see my balance screen", "فين اغير العملة الافتراضية", "ماذا يحدث عند حذف الحساب",
]
CHALLENGES = [
    "you said my balance is 5000, from where did you get that", "From where you get this number?", "you answered wrong",
    "how did you calculate my expenses", "that is wrong", "are you sure about my balance", "انت قلت ان رصيدي كبير",
    "من اين حصلت على رصيد البنك", "كيف حسبت المصروفات", "هل انت متاكد من الرصيد",
]
STILL_LOOKUPS = [
    ("what is my total balance", "balance"), ("balance for each bank", "balance"), ("how much did I spend in September 2026", "expenses"),
    ("gold 21k price", "gold_price"), ("كم رصيدي", "balance"), ("ما هو راتبي في يناير 2026", "salary"),
    ("what is the balance if any", "balance"), ("my certificates", "certificates"),
]


class RoutingGuardTests(SimpleTestCase):
    def test_what_if_questions_are_analytic_not_lookups(self):
        for q in WHAT_IF:
            with self.subTest(q=q):
                self.assertNotEqual(route(q).status, "ready")

    def test_app_help_questions_are_blocked_from_data_lookups(self):
        for q in APP_HELP:
            with self.subTest(q=q):
                r = route(q)
                self.assertNotEqual(r.status, "ready")
                self.assertEqual(r.reason, "app_help")

    def test_questions_about_the_previous_answer_go_to_the_model(self):
        for q in CHALLENGES:
            with self.subTest(q=q):
                r = route(q)
                self.assertEqual((r.status, r.reason), ("blocked", "refers_to_previous_answer"))

    def test_normal_lookups_are_unchanged(self):
        for q, cap in STILL_LOOKUPS:
            with self.subTest(q=q):
                r = route(q)
                self.assertEqual((r.status, r.capability), ("ready", cap))


class EmergencyRoutingTests(SimpleTestCase):
    def test_four_languages_route_to_the_capability(self):
        for q in ("Is my emergency fund enough for 6 months of expenses?", "كم شهر تغطي سيولتي من المصروفات",
                  "Mon fonds d'urgence est-il suffisant pour 6 mois ?", "Ist mein Notgroschen für 6 Monate Ausgaben ausreichend?"):
            with self.subTest(q=q):
                r = route(q)
                self.assertEqual((r.status, r.capability), ("ready", "emergency_fund"))

    def test_target_months_parsing(self):
        self.assertEqual(target_months("enough for 3 months?"), 3)
        self.assertEqual(target_months("كافي لـ 12 شهر"), 12)
        self.assertEqual(target_months("is it enough"), 6)
        self.assertEqual(target_months("for 99 months"), 6)


class EmergencyAnswerTests(TestCase):
    """cash 1,000 + certificate 100,000 (fixture); expenses of 600 and 400 in two recent months -> average 500."""

    def setUp(self):
        fx.build(self)
        cat = ExpenseCategory.objects.filter(owner=self.user, name="Food").first()
        Expense.objects.filter(owner=self.user).delete()   # fixture rows are dated 2026 and would fall inside the 180-day window
        today = date.today()
        prev = date(today.year - 1, 12, 15) if today.month == 1 else date(today.year, today.month - 1, 15)
        for d, amt in ((today, "600.00"), (prev, "400.00")):
            Expense.objects.create(owner=self.user, category=cat, date=d, year=d.year, month=d.month, amount=Decimal(amt),
                                   amount_base=Decimal(amt), description="recent")

    def test_answer_states_every_input_and_never_uses_the_llm(self):
        with NO_LLM as gen:
            data = fx.ask(self, "Is my emergency fund enough for 6 months of my average expenses?")
            text = data["message"]["content"]
            gen.assert_not_called()
        self.assertIn("101,000.00 EGP", text)
        self.assertIn("Average monthly expenses: 500.00 EGP", text)
        self.assertIn("2 month(s)", text)
        self.assertIn("covers 202.0 months", text)
        self.assertIn("Target of 6 months = 3,000.00 EGP", text)
        self.assertTrue(data["message"]["tool_calls"][0]["direct_answer"])
        self.assertNotIn("777,777", text)
        self.assertNotIn("999,999", text)

    def test_arabic_answer(self):
        with NO_LLM:
            text = fx.ask(self, "هل صندوق الطوارئ كافي لـ 6 اشهر؟")["message"]["content"]
        self.assertIn("صندوق الطوارئ لديك يغطي", text)
        self.assertIn("500.00 EGP", text)

    def test_payload_keys_are_additive_and_consistent(self):
        from core.services.financial_advisor.registry import get_financial_advisor_payload

        base = get_financial_advisor_payload("portfolio_optimizer", self.user)["expense_baseline"]
        for key in ("avg_monthly_expenses", "emergency_fund_months"):   # pre-existing keys keep their meaning
            self.assertIn(key, base)
        self.assertEqual(base["baseline_window_days"], 180)
        self.assertEqual(base["baseline_months"], 2)
        self.assertAlmostEqual(base["liquid_for_emergency"] / base["avg_monthly_expenses"], base["emergency_fund_months"], places=1)


class EmergencyNoDataTests(TestCase):
    def test_without_expenses_it_says_so(self):
        fx.build(self)
        Expense.objects.all().delete()
        with NO_LLM:
            text = fx.ask(self, "how many months of expenses does my cash cover")["message"]["content"]
        self.assertIn("No expenses are recorded yet", text)


class AppPagesTests(SimpleTestCase):
    def test_structure_context_lists_the_real_screens(self):
        from core.services.ai.app_pages import app_pages

        pages = app_pages()
        self.assertGreaterEqual(len(pages), 15)
        for p in pages:
            self.assertTrue({"route", "title", "open"} <= set(p) <= {"route", "title", "open", "tabs", "actions", "admin_only"})
        routes = {p["route"] for p in pages}
        self.assertTrue(any("settings" in r for r in routes))

    def test_structure_tool_returns_app_pages(self):
        from core.services.ai.context_builder import AIContextBuilder

        out = AIContextBuilder.build_structure_context(user=None, force_refresh=True)
        self.assertIn("app_pages", out)


class KnowledgeChunkTests(SimpleTestCase):
    def test_long_pages_are_split_not_clipped_and_stubs_are_skipped(self):
        from core.services.ai.app_knowledge.chunk_sources import MAX_CHUNK_CHARS, page_chunks

        chunks = page_chunks()
        self.assertTrue(all(len(c["text"]) <= MAX_CHUNK_CHARS + 60 for c in chunks))
        self.assertFalse([c for c in chunks if c["text"].startswith("Configure the administrative settings and preferences for ")])
        ids = [c["id"] for c in chunks]
        self.assertEqual(len(ids), len(set(ids)))
        deletion = " ".join(c["text"] for c in chunks if c["id"].startswith("page:billing-plans"))
        self.assertIn("DELETE", deletion)
        self.assertIn("Restore my account", deletion)

    def test_currency_page_documents_set_as_default(self):
        from core.services.ai.app_knowledge.chunk_sources import page_chunks

        text = " ".join(c["text"] for c in page_chunks() if c["id"].startswith("page:settings::settings-currency"))
        self.assertIn("Set as default", text)
