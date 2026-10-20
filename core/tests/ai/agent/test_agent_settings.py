"""Agent mode settings, the per-user Ask/Agent switch, and the Stop endpoint."""

from __future__ import annotations

import json

from django.test import TestCase

from core.models import AIConversation, AppSettings
from core.services.ai.agent import agent_active, control, get_chat_mode
from core.services.ai.agent.instructions import DEFAULT_INSTRUCTIONS, effective_instructions
from core.services.ai.agent.settings import limits
from core.tests.ai.investigation.support import make_user
from core.tests.billing.test_support import grant_ai_workspace_access


class AgentSettingsApiTest(TestCase):
    URL = "/api/settings/ai/"

    def setUp(self):
        self.admin = make_user("agent_set_admin", sysadmin=True)
        self.client.force_login(self.admin)

    def post(self, **body):
        return self.client.post(self.URL, json.dumps(body), content_type="application/json")

    def test_defaults_come_with_the_default_instructions(self):
        got = self.client.get(self.URL).json()
        self.assertTrue(got["ai_agent_enabled"])
        self.assertEqual(got["ai_agent_instructions"], "")
        self.assertEqual(got["ai_agent_instructions_default"], DEFAULT_INSTRUCTIONS)
        self.assertEqual((got["ai_agent_max_steps"], got["ai_agent_budget_s"], got["ai_agent_max_reads"]), (15, 600, 12))
        self.assertEqual(effective_instructions(), DEFAULT_INSTRUCTIONS)

    def test_round_trip_clamps_limits_and_custom_instructions_win(self):
        res = self.post(ai_agent_enabled=False, ai_agent_instructions="Always read first.", ai_agent_max_steps=999,
                        ai_agent_budget_s=1, ai_agent_max_reads=5)
        self.assertEqual(res.status_code, 200)
        got = self.client.get(self.URL).json()
        self.assertFalse(got["ai_agent_enabled"])
        self.assertEqual((got["ai_agent_max_steps"], got["ai_agent_budget_s"], got["ai_agent_max_reads"]), (40, 60, 5))
        self.assertEqual(effective_instructions(), "Always read first.")
        self.assertEqual(limits()["ai_agent_max_steps"], 40)

    def test_empty_instructions_restore_the_default_and_bad_input_is_rejected(self):
        self.post(ai_agent_instructions="custom")
        self.post(ai_agent_instructions="")
        self.assertEqual(effective_instructions(), DEFAULT_INSTRUCTIONS)
        self.assertEqual(self.post(ai_agent_instructions="x" * 6001).status_code, 400)
        self.assertEqual(self.post(ai_agent_max_steps="many").status_code, 400)
        self.post(ai_validate_mode="flag")                       # omitted agent keys keep their stored values
        self.assertEqual(self.client.get(self.URL).json()["ai_agent_max_steps"], 15)

    def test_document_instructions_and_time_limit_are_editable_with_a_default(self):
        from core.services.ai.agent.instructions import DEFAULT_DOCUMENT_INSTRUCTIONS, effective_document_instructions
        from core.services.ai.agent.settings import document_budget_s

        got = self.client.get(self.URL).json()
        self.assertEqual((got["ai_document_instructions"], got["ai_document_instructions_default"], got["ai_document_budget_s"]),
                         ("", DEFAULT_DOCUMENT_INSTRUCTIONS, 1200))
        self.assertEqual(self.post(ai_document_instructions="Write short sections.", ai_document_budget_s=5).status_code, 200)
        self.assertEqual((effective_document_instructions(), document_budget_s()), ("Write short sections.", 120))
        self.post(ai_document_instructions="", ai_document_budget_s=99999)
        self.assertEqual((effective_document_instructions(), document_budget_s()), (DEFAULT_DOCUMENT_INSTRUCTIONS, 7200))
        self.assertEqual(self.post(ai_document_instructions="x" * 6001).status_code, 400)

    def test_document_output_limit_is_a_setting_capped_by_the_context_window(self):
        from core.services.ai.agent.settings import document_max_tokens

        self.assertEqual(self.client.get(self.URL).json()["ai_document_max_tokens"], 6000)
        self.assertEqual(self.post(ai_document_max_tokens=8000, ai_context_size=16384).status_code, 200)
        self.assertEqual(document_max_tokens(), 8000)
        self.assertEqual(self.post(ai_document_max_tokens=99999, ai_context_size=16384).status_code, 200)
        self.assertEqual(document_max_tokens(), 12884)                      # 16384 - 3500 reserved for the prompt
        self.assertEqual(self.post(ai_document_max_tokens=8000, ai_context_size=4096).status_code, 200)
        self.assertEqual(document_max_tokens(), 1024)                       # never below a usable minimum
        self.assertEqual(self.post(ai_document_max_tokens="lots").status_code, 400)

    def test_reasoning_setting_defaults_to_auto_validates_and_is_saved(self):
        from core.integrations.ai_provider.ollama_payload import think_setting

        self.assertEqual(self.client.get(self.URL).json()["ai_think"], "auto")
        self.assertEqual(self.post(ai_think="off").status_code, 200)
        self.assertEqual((think_setting(), self.client.get(self.URL).json()["ai_think"]), ("off", "off"))
        self.assertEqual(self.post(ai_think="sometimes").status_code, 400)
        self.assertEqual(think_setting(), "off")
        self.post(ai_think="auto")
        self.assertEqual(think_setting(), "auto")

    def test_a_member_cannot_read_or_change_the_agent_settings(self):
        member = make_user("agent_set_member")
        self.client.force_login(member)
        self.assertGreaterEqual(self.client.get(self.URL).status_code, 401)
        self.assertGreaterEqual(self.post(ai_agent_enabled=False).status_code, 401)
        self.assertNotEqual(AppSettings.get("ai_agent_enabled", "true", user=None), "false")


class ChatModeAndStopTest(TestCase):
    MODE, STOP = "/api/financial-advisor/ai/chat-mode/", "/api/financial-advisor/ai/stop/"

    def setUp(self):
        self.user, self.other = make_user("mode_user"), make_user("mode_other")
        for u in (self.user, self.other):
            grant_ai_workspace_access(u)
        self.client.force_login(self.user)

    def post(self, url, **body):
        return self.client.post(url, json.dumps(body), content_type="application/json")

    def test_every_user_defaults_to_ask_and_can_switch_to_agent(self):
        got = self.client.get(self.MODE).json()
        self.assertEqual((got["mode"], got["agent_enabled"], got["code_tools"]), ("ask", True, False))
        self.assertEqual(self.post(self.MODE, mode="agent").json()["mode"], "agent")
        self.assertEqual(get_chat_mode(self.user), "agent")
        self.assertEqual(get_chat_mode(self.other), "ask")        # remembered per user, not globally
        self.assertTrue(agent_active(self.user))
        self.assertFalse(agent_active(self.other))
        self.assertEqual(self.post(self.MODE, mode="turbo").status_code, 400)

    def test_the_request_can_override_the_saved_mode_and_the_global_switch_wins(self):
        self.assertTrue(agent_active(self.user, "agent"))
        self.post(self.MODE, mode="agent")
        self.assertFalse(agent_active(self.user, "ask"))
        AppSettings.set("ai_agent_enabled", "false")
        self.assertFalse(agent_active(self.user, "agent"))
        self.assertFalse(self.client.get(self.MODE).json()["agent_enabled"])

    def test_sysadmin_sees_that_code_tools_are_available(self):
        admin = make_user("mode_admin", sysadmin=True)
        grant_ai_workspace_access(admin)
        self.client.force_login(admin)
        self.assertTrue(self.client.get(self.MODE).json()["code_tools"])

    def test_stop_only_works_on_your_own_conversation(self):
        conv = AIConversation.objects.create(user=self.user, title="t")
        self.assertEqual(self.post(self.STOP, conversation_id=conv.id).status_code, 200)
        self.assertTrue(control.is_stopped(self.user, conv.id))
        self.assertFalse(control.is_stopped(self.other, conv.id))
        control.clear_stop(self.user, conv.id)
        self.assertFalse(control.is_stopped(self.user, conv.id))
        self.client.force_login(self.other)
        self.assertEqual(self.post(self.STOP, conversation_id=conv.id).status_code, 404)
        self.assertFalse(control.is_stopped(self.user, conv.id))
        self.assertEqual(self.post(self.STOP).status_code, 400)

    def test_anonymous_requests_are_refused(self):
        self.client.logout()
        self.assertGreaterEqual(self.client.get(self.MODE).status_code, 401)
        self.assertGreaterEqual(self.post(self.STOP, conversation_id=1).status_code, 401)
