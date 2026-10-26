"""Stop during document writing, progress that survives a page refresh, the invented own-file guide and an empty classifier."""

from __future__ import annotations

from django.test import TestCase

from core.services.ai.cache_manager import AICacheManager
from core.services.ai.investigation.compose_sections import units
from core.services.ai.investigation.loop_helpers import publish_legacy
from core.views.ai_chat.chat_pipeline.investigate import ensure_document

from core.tests.billing.test_support import grant_ai_workspace_access

from .support import make_user
from .test_compose_guide import ASK, GuideProvider, Result


class DocStopAndProgressTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("stop_admin", sysadmin=True)

    def test_stop_ends_the_guide_without_more_model_calls_and_marks_the_run_cancelled(self):
        prov, res, flag = GuideProvider(), Result(), {"stop": False}
        prov.user = self.admin
        original = prov.generate

        def generate(messages, tools=None, **kw):
            if "Write ONLY this section" in messages[-1]["content"]:
                flag["stop"] = True           # Stop pressed while the first section is being written
            return original(messages, tools, **kw)

        prov.generate = generate
        self.assertFalse(ensure_document(prov, ASK, res, 24000, self.admin, None, cancel_check=lambda: flag["stop"]))
        self.assertEqual((res.reason, res.content), ("cancelled", ""))
        self.assertLess(len([c for c in prov.calls if "Write ONLY this section" in c["ask"]]), 3)

    def test_document_progress_keeps_the_agent_steps_and_stop_button_for_a_refreshed_page(self):
        key = f"ai_loop_progress:{self.admin.id}:77"
        steps = [{"n": 1, "tool": "app_data_models", "label": "Looking", "status": "ok", "target": ""}]
        AICacheManager().set(key, {"status": "running", "steps": steps, "can_stop": True, "started_at": 1000.0}, ttl_seconds=60.0)
        publish_legacy(self.admin, 77, 4, 24, "document_section", "Writing the document: Financial Advisor", 0.0)
        state = AICacheManager().get(key)
        self.assertEqual((state["steps"], state["can_stop"], state["started_at"]), (steps, True, 1000.0))
        self.assertEqual(state["label"], "Writing the document: Financial Advisor")

    def test_the_progress_endpoint_returns_them_to_a_new_page_load(self):
        from core.models import AIConversation

        conv = AIConversation.objects.create(user=self.admin, title="t")
        key = f"ai_loop_progress:{self.admin.id}:{conv.id}"
        AICacheManager().set(key, {"status": "running", "steps": [{"n": 1, "status": "ok"}], "can_stop": True, "started_at": 1.0}, ttl_seconds=60.0)
        publish_legacy(self.admin, conv.id, 2, 24, "document_section", "Writing", 0.0)
        grant_ai_workspace_access(self.admin)
        self.client.force_login(self.admin)
        data = self.client.get("/api/financial-advisor/ai/progress/", {"conversation_id": conv.id}).json()
        self.assertEqual((data["status"], data["can_stop"], len(data["steps"])), ("running", True, 1))

    def test_an_own_file_written_from_no_evidence_is_replaced_by_the_real_guide(self):
        prov, res = GuideProvider(about_app="NO"), Result()
        prov.user = self.admin
        res.content = "Done. " * 400                    # a long invented guide the model wrote itself
        res.steps = [{"tool": "generate_file", "status": "success", "arguments": {"content": "# Invented\n\nchapters nobody has"}}]
        self.assertTrue(ensure_document(prov, ASK, res, 24000, self.admin, None))
        self.assertTrue(res.content.startswith("# WealthFlow user guide"))

    def test_an_empty_classifier_answer_is_asked_once_more_with_reasoning(self):
        seen = []

        class Prov(GuideProvider):
            def generate(self, messages, tools=None, **kw):
                if "exactly one word" in messages[0]["content"]:
                    seen.append(kw.get("reasoning"))
                    return {"content": "" if len(seen) == 1 else "YES"}
                return super().generate(messages, tools, **kw)

        prov, res = Prov(), Result()
        prov.user = self.admin
        self.assertTrue(ensure_document(prov, ASK, res, 24000, self.admin, None))
        self.assertEqual(seen, ["off", "on"])


class HtmlRequestTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("html_admin", sysadmin=True)

    def test_an_html_guide_request_runs_the_guide_and_a_code_request_keeps_the_models_answer(self):
        prov, res = GuideProvider(about_app="YES"), Result()
        prov.user = self.admin
        self.assertTrue(ensure_document(prov, "generate an html user guide for the app", res, 24000, self.admin, None))
        self.assertTrue(res.content.startswith("# WealthFlow user guide"))
        prov, res = GuideProvider(about_app="NO"), Result()
        prov.user = self.admin
        res.content = '<!doctype html><form><input name="email"><input type="password"><button>Log in</button></form>'
        self.assertFalse(ensure_document(prov, "Write me an HTML login page.", res, 24000, self.admin, None))
        self.assertEqual(res.content, '<!doctype html><form><input name="email"><input type="password"><button>Log in</button></form>')

    def test_html_guide_uses_the_evidence_fallback_after_a_classifier_no(self):
        prov, res = GuideProvider(about_app="NO"), Result()
        prov.user = self.admin
        self.assertTrue(ensure_document(prov, "اكتب دليل مستخدم كامل للتطبيق بصيغة HTML", res, 24000, self.admin, None))
        self.assertEqual(res.content.count("\n## "), len({u["heading"] for u in units(self.admin) if u["heading"]}))

    def test_an_html_login_form_keeps_the_models_generated_page(self):
        prov, res = GuideProvider(about_app="NO"), Result()
        prov.user = self.admin
        res.content = "Done."
        res.steps = [{"tool": "generate_file", "status": "success", "arguments": {
            "content": '<!doctype html><form><input name="email"><input type="password"><button>Log in</button></form>'}}]
        self.assertFalse(ensure_document(prov, "Write me an HTML login page.", res, 24000, self.admin, None))
        self.assertEqual(res.content, "Done.")
