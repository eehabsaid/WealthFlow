"""Net worth forecast: "how much will my wealth be on 30-Nov-2026?" is answered from the app's own wealth-growth
projection (same numbers as the Wealth Growth screen), in four languages, with and without Instant Answers, and the
context builder no longer lets one data-heavy topic push another matched source out silently."""

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from core.integrations.ai_provider import OllamaProvider
from core.models import AppSettings
from core.services.ai.context_builder_service.service import _fit_blocks
from core.services.ai.query_engine import route
from core.services.financial_advisor.registry import get_financial_advisor_payload
from . import qe_fixtures as fx

NO_LLM = patch.object(OllamaProvider, "generate", side_effect=AssertionError("LLM must not be called"))
GP = "core.views.ai_chat.ai_chat_core_views.generation_pipeline.build_context"
VIEW = "core.views.ai_chat.ai_chat_core_views"
REPORTED = "please analyze my wealth and tell me how much will it be on 30-Nov-2026, in details"
QUESTIONS = {
    "en": "How much will my wealth be on 30 November 2026?",
    "ar": "كم ستكون ثروتي في 30 نوفمبر 2026 بالتفصيل",
    "fr": "Quel sera mon patrimoine net le 30 novembre 2026 ?",
    "de": "Wie hoch ist mein Nettovermögen am 30. November 2026?",
}


def money(v):
    return f"{float(v):,.2f} EGP"


class RoutingTests(SimpleTestCase):
    def test_every_language_routes_to_the_forecast_with_the_month(self):
        for lang, q in QUESTIONS.items():
            with self.subTest(lang=lang):
                r = route(q)
                self.assertEqual((r.status, r.capability, r.request.periods), ("ready", "wealth_forecast", [(2026, 11)]))
        self.assertEqual(route(REPORTED).status, "ready")      # "analyze" / "in details" no longer make it advice

    def test_what_if_and_neighbours_are_untouched(self):
        self.assertEqual(route("what if I move 100,000 to gold, what will my wealth be").status, "analytic")
        self.assertEqual(route("what is my total balance").capability, "balance")
        self.assertEqual(route("how many months does my emergency fund cover").capability, "emergency_fund")


class ForecastChatTests(TestCase):
    def setUp(self):
        fx.build(self)
        self.payload = get_financial_advisor_payload("wealth_growth", self.user)
        self.nov = next(p for p in self.payload["series"]["expected"]["points"] if p["month_end"] == "2026-11-30")

    def ask(self, q):
        with NO_LLM as gen:
            content = fx.ask(self, q, conversation=False)["message"]["content"]
            gen.assert_not_called()
        return content

    def test_the_reported_question_gets_the_real_projection_not_expenses(self):
        text = self.ask(REPORTED)
        self.assertIn(money(self.nov["net_worth"]), text)
        self.assertIn(money(self.payload["current_net_worth"]), text)
        for k in ("liquid_cash", "certificates", "fixed_assets"):
            self.assertIn(money(self.nov[k]), text)
        self.assertNotIn("Total All-Time Spending", text)

    def test_all_languages_show_the_same_numbers(self):
        for lang, q in QUESTIONS.items():
            with self.subTest(lang=lang):
                self.assertIn(money(self.nov["net_worth"]), self.ask(q))

    def test_other_tenants_data_is_never_included(self):
        self.assertNotIn("9,999,999", self.ask(REPORTED))

    def test_file_request_in_the_same_question_gets_the_link(self):
        text = self.ask(REPORTED + " and export it to word")
        self.assertIn(money(self.nov["net_worth"]), text)
        self.assertIn("/export/docx/", text)
        self.assertNotIn("no earlier answer", text)

    def test_date_inside_a_month_beyond_the_horizon_and_in_the_past(self):
        self.assertIn("projects month-end values", self.ask("how much will my wealth be on 15-Nov-2026"))
        far = self.ask("how much will my wealth be on 31-Dec-2031")
        self.assertIn("The forecast model reaches", far)
        self.assertIn(money(self.payload["series"]["expected"]["points"][-1]["net_worth"]), far)
        self.assertIn("is not in the future", self.ask("my wealth on 30-Sep-2026"))

    def test_no_date_shows_today_and_the_checkpoints(self):
        text = self.ask("what is my net worth")
        self.assertIn(money(self.payload["current_net_worth"]), text)
        self.assertIn(money(self.payload["checkpoints"]["month_12"]), text)

    def test_no_data_says_so_instead_of_inventing(self):
        empty = get_user_model().objects.create_user(username="qe_empty", password="pw123456")
        from core.tests.billing.test_support import grant_ai_workspace_access
        grant_ai_workspace_access(empty)
        self.client.force_login(empty)
        self.assertIn("not enough data", self.ask(REPORTED))

    def test_model_path_with_instant_answers_off_receives_the_exact_projection(self):
        AppSettings.set("ai_direct_answers", "false")
        prov = MagicMock()
        prov.supports_tools = True
        prov.generate.side_effect = lambda *a, **k: {"content": "ok", "tool_calls": None, "error": None}
        ctx = ([{"role": "system", "content": "SYS === FINANCIAL CONTEXT DATA === expenses only"}, {"role": "user", "content": "q"}], ["expenses"])
        with patch(f"{VIEW}.get_active_ai_provider", return_value=prov), patch(GP, return_value=ctx):
            fx.ask(self, REPORTED, conversation=False)
        sent = "\n".join(str(m.get("content")) for call in prov.generate.call_args_list for m in call[0][0])
        self.assertIn("VERIFIED DATA", sent)
        self.assertIn(money(self.nov["net_worth"]), sent)


class ContextBudgetTests(SimpleTestCase):
    def test_one_heavy_source_cannot_starve_another(self):
        heavy = [f"H{i}" + "x" * 400 for i in range(10)]        # 10 blocks of ~400 chars from "expenses"
        wealth = ["W" + "y" * 300]
        owner = {id(b): "expenses" for b in heavy} | {id(wealth[0]): "wealth_growth"}
        blocks, included = _fit_blocks(heavy + wealth, [], 1500, owner)
        self.assertIn("wealth_growth", included)
        self.assertIn(wealth[0], blocks)
        self.assertLessEqual(sum(len(b) for b in blocks), 1500)

    def test_a_block_that_does_not_fit_is_skipped_and_never_listed_as_a_source(self):
        big, small = "B" * 900, "s" * 100
        owner = {id(big): "huge", id(small): "tiny"}
        blocks, included = _fit_blocks([big, small], [], 500, owner)
        self.assertEqual((blocks, included), ([small], {"tiny"}))

    def test_low_priority_blocks_follow_and_order_is_preserved(self):
        a, b, c = "a" * 100, "b" * 100, "c" * 100
        owner = {id(a): "one", id(b): "two", id(c): "one"}
        blocks, _ = _fit_blocks([a, b], [c], 1000, owner)
        self.assertEqual(blocks, [a, b, c])
