"""The real failure: in Agent mode the model wrote the guide itself with generate_file, three times, and the Word file held
all three drafts back to back. Now the app writes the guide once (from the live screens) and the download has one copy."""

from __future__ import annotations

import io
import json
from unittest.mock import patch

import docx
from django.test import TestCase

from core.models import AppSettings
from core.services.ai.agent import set_chat_mode
from core.tests.ai.investigation.support import make_user
from core.tests.ai.investigation.test_compose_guide import GuideProvider
from core.tests.billing.test_support import grant_ai_workspace_access

VIEW = "core.views.ai_chat.ai_chat_core_views"
CTX = ([{"role": "system", "content": "SYS"}, {"role": "user", "content": "q"}], [])
DRAFT = "# دليل المستخدم — WealthFlow\n" + "\n".join(f"## الفصل {n}\n### الجزء {n}\nنص." for n in range(8))


class ScriptedAgent(GuideProvider):
    """Tool-loop turns come from the script; the app's own guide-writing prompts get the usual guide answers."""

    model = "scripted"
    supports_tools = True

    def __init__(self, script):
        super().__init__()
        self.script = list(script)

    def generate(self, messages, tools=None, **kwargs):
        if tools and self.script:
            return self.script.pop(0)
        if tools:
            return {"content": "تم إنشاء الدليل.", "tool_calls": [], "error": None}
        return super().generate(messages, tools, **kwargs)


def generate_file(content):
    return {"content": "", "error": None, "tool_calls": [{"function": {"name": "generate_file", "arguments": {"format": "docx", "title": "Guide", "content": content}}}]}


class AgentGuideDownloadTest(TestCase):
    def setUp(self):
        self.user = make_user("agent_guide_dl", sysadmin=True)
        grant_ai_workspace_access(self.user)
        self.client.force_login(self.user)
        AppSettings.set("ai_enabled", "true")
        set_chat_mode(self.user, "agent")

    def test_three_drafts_from_the_model_give_one_guide_in_the_word_file(self):
        prov = ScriptedAgent([generate_file(DRAFT), generate_file(DRAFT + "\n## زيادة"), generate_file(DRAFT)])
        prov.user = self.user
        with patch(f"{VIEW}.get_active_ai_provider", return_value=prov), patch(f"{VIEW}.generation_pipeline.build_context", return_value=CTX), \
                self.assertLogs("core.ai.pipeline", level="WARNING"):
            res = self.client.post("/api/financial-advisor/ai/chat/", json.dumps({"message": "write the user guide as a Word document"}),
                                   content_type="application/json")
        message = res.json()["message"]
        self.assertTrue(message["content"].startswith("# WealthFlow user guide"))
        file_res = self.client.get(f"/api/financial-advisor/ai/messages/{message['id']}/export/docx/")
        self.assertEqual(file_res.status_code, 200)
        document = docx.Document(io.BytesIO(b"".join(file_res.streaming_content) if file_res.streaming else file_res.content))
        paragraphs = [p.text for p in document.paragraphs if p.style.name.startswith(("Heading", "Title"))]   # the contents list repeats each title on purpose
        self.assertEqual(sum(1 for t in paragraphs if t.startswith("WealthFlow user guide")), 1)
        self.assertFalse([t for t in paragraphs if "الفصل" in t or "دليل المستخدم" in t])      # none of the model's own drafts
        self.assertEqual(sum(1 for t in paragraphs if t == "Signing up and signing in"), 1)     # every chapter once
