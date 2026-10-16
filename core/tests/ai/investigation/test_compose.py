"""A requested document is never the model's "let me write it" sentence: one dedicated call writes the full text."""

from __future__ import annotations

from types import SimpleNamespace

from django.test import TestCase

from core.services.ai.investigation.compose import compose_document, needs_document
from core.views.ai_chat.chat_pipeline.investigate import ensure_document, wants_written_document

from .support import ScriptedProvider

GUIDE = "# WealthFlow user guide\n\n" + "\n\n".join(f"## Section {i}\nYou can manage your money here. " * 12 for i in range(1, 8)).strip()


def result(content, steps=(), results=(("app_routes", {}, "dashboard, expenses, assets"),)):
    return SimpleNamespace(content=content, steps=list(steps), results=list(results), reason="answered", llm_calls=0)


class ComposeTest(TestCase):
    ASK = "can you generate a word document for the app business as user guide?"

    def test_any_announcement_wording_is_replaced_by_the_full_document(self):
        for stub in ("Now I have a solid picture. Let me compose the Word document.", "Done researching.", "ok"):
            prov, res = ScriptedProvider([{"content": GUIDE}]), result(stub)
            self.assertTrue(ensure_document(prov, self.ASK, res, 24000))
            self.assertEqual(res.content, GUIDE)
            sent = "\n".join(m["content"] for m in prov.calls[0]["messages"])
            self.assertIn("dashboard, expenses, assets", sent)    # the evidence the tools returned
            self.assertIsNone(prov.calls[0]["tools"])
            self.assertEqual(res.llm_calls, 1)

    def test_a_built_file_or_a_real_long_answer_is_left_alone(self):
        built = result("Created the guide.", steps=[{"tool": "generate_file", "status": "success"}])
        failed = result("short", steps=[{"tool": "generate_file", "status": "failed"}])
        self.assertFalse(needs_document(built))
        self.assertTrue(needs_document(failed))
        self.assertFalse(needs_document(result(GUIDE)))
        prov = ScriptedProvider([{"content": GUIDE}])
        self.assertFalse(ensure_document(prov, self.ASK, built, 24000))
        self.assertEqual(prov.calls, [])

    def test_only_document_requests_and_never_when_stopped(self):
        self.assertTrue(wants_written_document("write the guide as a word document"))
        self.assertTrue(wants_written_document("export it to pdf"))
        self.assertFalse(wants_written_document("how much did I spend?"))
        self.assertFalse(wants_written_document("export my expenses to excel"))
        stopped = result("Let me")
        stopped.reason = "cancelled"
        self.assertFalse(ensure_document(ScriptedProvider([{"content": GUIDE}]), self.ASK, stopped, 24000))

    def test_failed_composition_keeps_the_original_answer(self):
        for reply in ({"content": ""}, {"content": "I don't have access to that."}, {"error": "boom"}, {"content": "too short"}):
            res = result("Let me write it.")
            self.assertFalse(ensure_document(ScriptedProvider([reply]), self.ASK, res, 24000))
            self.assertEqual(res.content, "Let me write it.")
        self.assertEqual(compose_document(ScriptedProvider([{"content": "<think>x</think>" + GUIDE}]), self.ASK, result("x")), GUIDE)


class ComposeEvidenceAndHeaderTest(TestCase):
    def test_a_self_titled_document_replaces_the_generic_export_header(self):
        from core.models import AIConversation, AIMessage
        from core.services.ai.exports.build import document_for
        from core.tests.ai.investigation.support import make_user

        user = make_user("header_user")
        conv = AIConversation.objects.create(user=user, title="t")
        AIMessage.objects.create(conversation=conv, role="user", content="write the user guide as a word document", sources=[])
        guide = AIMessage.objects.create(conversation=conv, role="assistant", content=GUIDE, sources=[])
        doc = document_for(guide)
        self.assertEqual(doc.title, "WealthFlow user guide")
        self.assertEqual(doc.question, "")
        self.assertTrue(doc.generated)
        self.assertEqual(doc.blocks[0].kind, "heading")
        self.assertEqual(doc.blocks[0].level, 2)       # the old H1 became the title, sections keep their level
        plain_answer = AIMessage.objects.create(conversation=conv, role="assistant", content="## Totals\n\nYou spent 5.", sources=[])
        self.assertEqual(document_for(plain_answer).title, "WealthFlow AI")   # ordinary answers keep the usual header
