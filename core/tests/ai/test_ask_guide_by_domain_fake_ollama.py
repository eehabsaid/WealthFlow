"""What Ask mode really does with a user-guide request in each chat domain, through the chat view, the REAL OllamaProvider and the
fake Ollama server (tests/support/fake_ollama.py). Business: the guide is written and downloadable. App: a clear refusal that names the
domain to switch to, no file. A refusal never has download links and never downloads as a file."""

from __future__ import annotations

import json
from unittest.mock import patch

from django.test import TestCase

from core.integrations.ai_provider.ollama_provider import OllamaProvider
from core.models import AppSettings
from core.services.ai.domains import APP, BUSINESS
from core.services.ai.investigation.compose_sections import units
from core.tests.billing.test_support import grant_ai_workspace_access
from tests.support import fake_ollama as fo

from .investigation.support import make_user
from .investigation.test_compose_guide import GuideProvider
from .test_chat_domains import GP, VIEW

CTX = ([{"role": "system", "content": "SYS"}, {"role": "user", "content": "q"}], [])
REQUEST = "write the user guide as a Word document"


class AskGuideByDomainTest(TestCase):
    def setUp(self):
        self.user = make_user("ask_domain_fake", sysadmin=True)
        grant_ai_workspace_access(self.user)
        self.client.force_login(self.user)
        AppSettings.set("ai_enabled", "true")
        AppSettings.set("ai_direct_answers", "false")
        script = GuideProvider()
        script.user = self.user
        self.plan = units(self.user)   # read on this thread: the fake server answers from another one

        def handler(payload):
            if payload.get("tools"):
                return fo.reply("Let me write the guide now.")   # the model announces instead of writing: the app writes the document
            return fo.reply(script.generate(payload["messages"])["content"])

        self.server = fo.FakeOllama(handler=handler).start()
        self.addCleanup(self.server.stop)
        self.provider = OllamaProvider(base_url=self.server.url, model=fo.MODEL, timeout=60)

    def ask(self, domain: str, text: str = REQUEST):
        with patch(f"{VIEW}.get_active_ai_provider", return_value=self.provider), patch(GP, return_value=CTX), \
                patch("core.tests.ai.investigation.test_compose_guide.units", return_value=self.plan):
            res = self.client.post("/api/financial-advisor/ai/chat/", json.dumps({"message": text, "question_domain": domain}), content_type="application/json")
        return res.json()["message"]

    def test_business_domain_writes_the_guide_and_it_downloads(self):
        message = self.ask(BUSINESS)
        self.assertTrue(message["content"].startswith("# WealthFlow user guide"), message["content"][:200])
        for fmt in ("docx", "pdf", "html"):
            res = self.client.get(f"/api/financial-advisor/ai/messages/{message['id']}/export/{fmt}/")
            self.assertEqual(res.status_code, 200, fmt)
        asked = [r for r in self.server.requests if "exactly one word" in r["system"]]
        self.assertTrue(asked and not any(r["think"] for r in asked))   # the classifier question never thinks in auto mode

    def test_app_domain_refuses_clearly_names_the_domain_to_switch_to_and_attaches_no_file(self):
        message = self.ask(APP)
        self.assertIn("Business / Data Analysis", message["content"])
        self.assertNotIn("/export/", message["content"])
        for fmt in ("docx", "html"):
            self.assertEqual(self.client.get(f"/api/financial-advisor/ai/messages/{message['id']}/export/{fmt}/").status_code, 404)

    def test_an_html_request_with_the_word_html_in_a_refusal_never_becomes_a_file(self):
        message = self.ask(APP, "write the user guide as an html file")
        self.assertNotIn("/export/", message["content"])
        self.assertEqual(self.client.get(f"/api/financial-advisor/ai/messages/{message['id']}/export/html/").status_code, 404)
