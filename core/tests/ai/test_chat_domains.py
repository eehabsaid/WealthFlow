"""Chat domains (Settings > AI Advisor > Chat domains): which domains exist, what each may touch (tools, context, guide) in Ask and
Agent mode, and the answers a question outside the domain gets (short, no technical detail, no mention of another domain)."""

from __future__ import annotations

import datetime

from django.test import TestCase

from core.models import AppSettings
from core.services.ai import domain_scope as scope
from core.services.ai.domains import APP, BUSINESS, DATA_TOOLS, enabled_domains, resolve_domain
from core.services.ai.investigation.defs import investigation_tool_schemas
from core.tests.billing.test_support import grant_ai_workspace_access
from core.views.settings.ai.ai_pipeline_settings import get_pipeline_settings, persist_pipeline_settings, validate_pipeline_settings

from .investigation.support import make_user

VIEW = "core.views.ai_chat.ai_chat_core_views"
GP = f"{VIEW}.generation_pipeline.build_context"
NO_INFO = scope.no_info("")


def names(schemas):
    return {s["function"]["name"] for s in schemas}


def set_domains(business: bool, app: bool) -> None:
    AppSettings.set("ai_domain_business", "true" if business else "false", user=None)
    AppSettings.set("ai_domain_app", "true" if app else "false", user=None)


class DomainSettingsTest(TestCase):
    def test_both_domains_are_on_by_default_and_one_always_stays_on(self):
        self.assertEqual(enabled_domains(), (BUSINESS, APP))
        set_domains(False, False)
        self.assertEqual(enabled_domains(), (BUSINESS, APP))        # never none

    def test_one_domain_forces_the_chat_and_two_leave_the_choice(self):
        set_domains(True, False)
        self.assertEqual(resolve_domain(APP), BUSINESS)              # the browser's choice is ignored
        self.assertEqual(resolve_domain(""), BUSINESS)
        set_domains(False, True)
        self.assertEqual(resolve_domain(BUSINESS), APP)
        set_domains(True, True)
        self.assertEqual(resolve_domain(APP), APP)
        self.assertEqual(resolve_domain(""), "")                     # inferred as before

    def test_the_settings_refuse_none_and_save_the_choice(self):
        bad, error = validate_pipeline_settings({"ai_domain_business": False, "ai_domain_app": False})
        self.assertIsNone(bad)
        self.assertEqual(error.status_code, 400)
        ok, error = validate_pipeline_settings({"ai_domain_business": True, "ai_domain_app": "false"})
        self.assertIsNone(error)
        persist_pipeline_settings(ok)
        settings = get_pipeline_settings()
        self.assertTrue(settings["ai_domain_business"])
        self.assertFalse(settings["ai_domain_app"])

    def test_the_workspace_is_told_the_allowed_domains(self):
        user = make_user("dom_user")
        grant_ai_workspace_access(user)
        self.client.force_login(user)
        self.assertEqual(self.client.get("/api/financial-advisor/ai/chat-mode/").json()["domains"], [BUSINESS, APP])
        set_domains(False, True)
        self.assertEqual(self.client.get("/api/financial-advisor/ai/chat-mode/").json()["domains"], [APP])


class DomainToolsTest(TestCase):
    def test_business_gets_only_data_tools_and_the_app_domain_none_of_them(self):
        admin = make_user("dom_admin", sysadmin=True)
        business, app, everything = (names(investigation_tool_schemas(admin, d)) for d in (BUSINESS, APP, ""))
        self.assertTrue(business >= {"app_data_query", "app_data_models"})
        self.assertTrue(business <= set(DATA_TOOLS) | {"generate_file"}, business)
        for technical in ("app_read_file", "app_grep", "app_routes", "app_knowledge_search", "app_i18n_search"):
            self.assertNotIn(technical, business)
            self.assertIn(technical, app)
        self.assertFalse(app & set(DATA_TOOLS))
        self.assertTrue(everything >= business | app)


class ScopeTest(TestCase):
    def test_the_app_domain_loses_the_users_data_and_every_domain_gets_today(self):
        msgs = [{"role": "system", "content": "SYS\n=== FINANCIAL CONTEXT DATA ===\nBalance 9,999.00"}, {"role": "user", "content": "q"}]
        scope.apply_scope(msgs, APP)
        self.assertNotIn("9,999", msgs[0]["content"])
        self.assertIn(datetime.date.today().isoformat(), msgs[-1]["content"])
        keep = [{"role": "system", "content": "SYS\n=== FINANCIAL CONTEXT DATA ===\nBalance 9,999.00"}]
        scope.apply_scope(keep, BUSINESS)
        self.assertIn("9,999", keep[0]["content"])

    def test_a_question_outside_the_domain_gets_a_short_answer_in_the_users_language_that_names_where_to_switch(self):
        english = scope.guard_answer(BUSINESS, "OUT_OF_SCOPE", "how is it built?", "")
        self.assertEqual(english, scope.no_info("how is it built?", BUSINESS))
        self.assertIn("Application Features & Architecture", english)      # the UI's own name of the domain to switch to
        arabic = scope.guard_answer(APP, "`OUT_OF_SCOPE`.", "كم رصيدي؟", "")
        self.assertTrue(any("\u0600" <= c <= "\u06ff" for c in arabic))
        self.assertIn("تحليل الأعمال والبيانات", arabic)
        for text in (english, arabic):
            self.assertTrue(scope.is_no_info(text))

    def test_rows_dated_after_today_that_the_data_does_not_hold_are_dropped(self):
        today = datetime.date.today()
        real, fake = today - datetime.timedelta(days=3), today + datetime.timedelta(days=4)
        answer = f"Expenses:\n- {real.isoformat()} food 50.00\n- {fake.isoformat()} rent 900.00\n- {fake.strftime('%d/%m/%Y')} fuel 40.00\n"
        out = scope.guard_answer(BUSINESS, answer, "list my expenses this month", f"{real.isoformat()} food 50.00")
        self.assertIn(real.isoformat(), out)
        self.assertNotIn(fake.isoformat(), out)
        self.assertNotIn("fuel", out)

    def test_a_future_date_the_data_or_the_question_holds_is_kept(self):
        fake = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
        self.assertIn(fake, scope.guard_answer(BUSINESS, f"- {fake} rent due 900.00", "x", f"{fake} rent due 900.00"))
        self.assertIn(fake, scope.guard_answer(BUSINESS, f"- {fake} rent due", f"what is due on {fake}", ""))

    def test_the_app_domain_never_states_a_figure_it_cannot_have(self):
        self.assertEqual(scope.guard_answer(APP, "Your October expenses are 4,500.00 EGP.", "list my expenses", "docs"), scope.no_info("list my expenses", APP))
        self.assertEqual(scope.guard_answer(APP, "The Balance screen has three tabs.", "what is on the screen", "docs"),
                         "The Balance screen has three tabs.")
