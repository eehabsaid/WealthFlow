"""Ask mode hands a "write the user guide as a file" request to Agent mode and the chat's mode bar follows (response key chat_mode).
Real chat view + real OllamaProvider + the fake Ollama server (tests/support/fake_ollama.py): the model is scripted, the pipeline is not."""

from __future__ import annotations

import json
from unittest.mock import patch

from django.test import TestCase

from core.integrations.ai_provider.ollama_provider import OllamaProvider
from core.models import AppSettings
from core.services.ai.agent import get_chat_mode, set_chat_mode
from core.services.ai.domains import APP, BUSINESS
from core.services.ai.investigation.compose_sections import units
from core.tests.billing.test_support import grant_ai_workspace_access
from tests.support import fake_ollama as fo

from .investigation.support import make_user
from .investigation.test_compose_guide import GuideProvider
from .test_chat_domains import GP, VIEW

CTX = ([{"role": "system", "content": "SYS"}, {"role": "user", "content": "q"}], [])
GUIDE = "generate the user guide for the entire app as HTML"


class AskMovesGuideToAgentTest(TestCase):
    answer_about_app = True

    def setUp(self):
        self.user = make_user("ask_to_agent", sysadmin=True)
        grant_ai_workspace_access(self.user)
        self.client.force_login(self.user)
        for key, value in (("ai_enabled", "true"), ("ai_direct_answers", "false"), ("ai_agent_enabled", "true")):
            AppSettings.set(key, value)
        set_chat_mode(self.user, "ask")
        script = GuideProvider()
        script.user = self.user
        self.plan = units(self.user)
        about_app = self.answer_about_app

        def handler(payload):
            if "exactly one word" in str(payload["messages"][0]["content"]):
                return fo.reply("YES" if about_app else "NO")
            if payload.get("tools"):
                return fo.reply("Let me write the guide now.")
            return fo.reply(script.generate(payload["messages"])["content"])

        self.server = fo.FakeOllama(handler=handler).start()
        self.addCleanup(self.server.stop)
        self.provider = OllamaProvider(base_url=self.server.url, model=fo.MODEL, timeout=60)

    def ask(self, domain: str, text: str = GUIDE, mode: str = "ask") -> dict:
        body = {"message": text, "question_domain": domain, "chat_mode": mode}
        with patch(f"{VIEW}.get_active_ai_provider", return_value=self.provider), patch(GP, return_value=CTX), \
                patch("core.tests.ai.investigation.test_compose_guide.units", return_value=self.plan):
            res = self.client.post("/api/financial-advisor/ai/chat/", json.dumps(body), content_type="application/json")
        return res.json()


class MovedTest(AskMovesGuideToAgentTest):
    def test_guide_request_in_ask_mode_runs_in_agent_mode_and_the_bar_follows(self):
        data = self.ask(BUSINESS)
        self.assertEqual(data.get("chat_mode"), "agent")
        self.assertEqual(get_chat_mode(self.user), "agent")
        self.assertTrue(data["message"]["content"].startswith("# WealthFlow user guide"), data["message"]["content"][:200])
        self.assertEqual(self.client.get(f"/api/financial-advisor/ai/messages/{data['message']['id']}/export/html/").status_code, 200)

    def test_already_in_agent_mode_nothing_to_move(self):
        set_chat_mode(self.user, "agent")
        self.assertNotIn("chat_mode", self.ask(BUSINESS, mode="agent"))

    def test_the_app_domain_keeps_its_refusal_and_stays_in_ask_mode(self):
        data = self.ask(APP)
        self.assertNotIn("chat_mode", data)
        self.assertEqual(get_chat_mode(self.user), "ask")
        self.assertNotIn("/export/", data["message"]["content"])

    def test_agent_mode_switched_off_by_the_administrator_means_no_move(self):
        AppSettings.set("ai_agent_enabled", "false")
        self.assertNotIn("chat_mode", self.ask(BUSINESS))
        self.assertEqual(get_chat_mode(self.user), "ask")


class NotAboutTheAppTest(AskMovesGuideToAgentTest):
    answer_about_app = False

    def test_a_file_request_that_is_not_about_the_app_stays_in_ask_mode(self):
        data = self.ask(BUSINESS, "export my expenses of this month to a Word document")
        self.assertNotIn("chat_mode", data)
        self.assertEqual(get_chat_mode(self.user), "ask")
