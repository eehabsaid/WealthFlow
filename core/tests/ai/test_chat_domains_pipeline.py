"""Chat domains in the chat pipeline: Ask mode, Agent mode and the user guide (see test_chat_domains.py for the settings and rules)."""

from __future__ import annotations

import datetime
import json
from unittest.mock import MagicMock, patch

from django.test import TestCase

from core.models import AppSettings
from core.services.ai.domains import APP, BUSINESS, DATA_TOOLS
from core.services.ai.investigation.compose import compose_document
from core.services.ai.investigation.compose_sections import knowledge, units
from core.tests.billing.test_support import grant_ai_workspace_access

from .investigation.support import make_user, seed_tenant, tool_call
from .investigation.test_compose_guide import ASK, GuideProvider, Result
from core.services.ai.domain_scope import no_info

from .test_chat_domains import GP, VIEW, names, set_domains


class DomainChatBase(TestCase):
    def setUp(self):
        self.user = make_user("dom_chat_user")
        seed_tenant(self.user, "D", expenses=2, amount="50.00")
        grant_ai_workspace_access(self.user)
        self.client.force_login(self.user)
        AppSettings.set("ai_enabled", "true")
        AppSettings.set("ai_direct_answers", "false")

    def ask(self, text, script, ctx="=== FINANCIAL CONTEXT DATA ===\nBalance: 12,345.67 EGP.", sources=("balance",), **body):
        prov = MagicMock()
        prov.supports_tools = True
        prov.model = "scripted"
        prov.generate.side_effect = [{"content": s, "tool_calls": [], "error": None} if isinstance(s, str)
                                     else {"content": "", "tool_calls": [], "error": None, **s} for s in script]
        context = ([{"role": "system", "content": "SYS\n" + ctx}, {"role": "user", "content": text}], list(sources))
        with patch(f"{VIEW}.get_active_ai_provider", return_value=prov), patch(GP, return_value=context):
            res = self.client.post("/api/financial-advisor/ai/chat/", json.dumps({"message": text, **body}), content_type="application/json")
        return res.json()["message"]["content"], prov


class AskModeDomainTest(DomainChatBase):
    def test_the_app_domain_never_receives_the_users_data_and_invented_figures_become_no_information(self):
        content, prov = self.ask("list my expenses of october", ["Your October expenses: 4,500.00 EGP in total."], question_domain=APP)
        self.assertEqual(content, no_info("list my expenses of october", APP))
        sent = json.dumps(prov.generate.call_args_list[0].args[0])
        self.assertNotIn("12,345.67", sent)
        self.assertIn(datetime.date.today().isoformat(), sent)

    def test_the_business_domain_gets_no_technical_tool_and_an_out_of_scope_question_is_not_escalated(self):
        set_domains(True, False)
        content, prov = self.ask("how is the application built?", ["OUT_OF_SCOPE"], ctx="", sources=(), question_domain=APP)   # the browser's choice is ignored
        self.assertEqual(content, no_info("how is the application built?", BUSINESS))   # only Business is on: it says so and who can enable the other
        self.assertEqual(prov.generate.call_count, 1)                  # no investigator run on top
        offered = names(prov.generate.call_args_list[0].kwargs["tools"])
        self.assertFalse(offered & {"read_application_codebase", "read_live_app_structure", "suggest_app_feature"})

    def test_invented_future_rows_never_reach_the_user(self):
        today = datetime.date.today()
        real, fake = today - datetime.timedelta(days=2), today + datetime.timedelta(days=6)
        ctx = f"=== FINANCIAL CONTEXT DATA ===\n{real.isoformat()} food 50.00"
        answer = f"- {real.isoformat()} food 50.00\n- {fake.isoformat()} rent 900.00\n- {fake.isoformat()} fuel 40.00"
        content, _ = self.ask("list my expenses this month", [answer], ctx=ctx, question_domain=BUSINESS)
        self.assertIn(real.isoformat(), content)
        self.assertNotIn(fake.isoformat(), content)


class AgentModeDomainTest(DomainChatBase):
    def agent(self, text, script, **body):
        with patch("core.services.ai.agent.agent_active", return_value=True), \
                patch("core.views.ai_chat.ai_chat_core_views.agent_stage.agent_active", return_value=True):
            return self.ask(text, script, chat_mode="agent", **body)

    def test_business_only_agent_has_data_tools_only_and_no_code_in_its_prompt(self):
        set_domains(True, False)
        content, prov = self.agent("what is my balance?", [tool_call("app_data_models"), "You have 12,345.67 EGP."], question_domain=APP)
        first = prov.generate.call_args_list[0]
        offered = names(first.kwargs["tools"])
        self.assertTrue(offered <= set(DATA_TOOLS) | {"generate_file", "read_memory"}, offered)
        system = first.args[0][0]["content"]
        self.assertIn("SCOPE:", system)
        self.assertIn(datetime.date.today().isoformat(), system)
        self.assertNotIn("source code", system.split("SCOPE:")[0].split("HARD")[0].lower().replace("sysadmin", ""))

    def test_app_only_agent_has_no_data_tool_and_an_out_of_scope_question_gets_no_information(self):
        set_domains(False, True)
        content, prov = self.agent("what did I spend in october?", ["OUT_OF_SCOPE"])
        self.assertEqual(content, no_info("what did I spend in october?", APP))
        self.assertFalse(names(prov.generate.call_args_list[0].kwargs["tools"]) & set(DATA_TOOLS))


class GuideDomainTest(TestCase):
    def test_the_user_guide_is_a_business_document_and_the_app_domain_refuses_it(self):
        admin = make_user("dom_guide_admin", sysadmin=True)
        prov = GuideProvider()
        prov.user = admin
        self.assertEqual(compose_document(prov, ASK, Result(), 24000, admin, None, domain=APP), no_info(ASK, APP))
        self.assertTrue(compose_document(prov, ASK, Result(), 24000, admin, None, domain=BUSINESS).startswith("# WealthFlow user guide"))

    def test_with_technical_information_switched_off_the_guide_uses_the_documented_screen_text_only(self):
        admin = make_user("dom_know_admin", sysadmin=True)
        unit = units(admin)[0]
        with patch("core.services.ai.tools.validate_and_execute_tool", return_value=({}, {"results": ["technical text"]})):
            self.assertIn("technical", knowledge(admin, unit) + "technical")      # on: the search runs
            set_domains(True, False)
            self.assertEqual(knowledge(admin, unit), "")
