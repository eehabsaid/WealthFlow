"""AI memory tests: the view/edit/delete API and the management command."""


import json
from ai.models import AISetting
from unittest.mock import MagicMock, patch


from ai.models.ai_memory import AIMemoryNote
from ai.services.memory import apply_edits, build_memory_block, update_memory
from ai.services.memory.store import MAX_NOTES
from ai.services.tools import validate_and_execute_tool
from ai.services.tools.defs import get_registered_tool_schemas
from core.tests.billing.test_support import grant_ai_workspace_access
from .ai_memory_support import API, MemoryTestBase, _provider


class MemoryApiTests(MemoryTestBase):
    def setUp(self):
        super().setUp()
        grant_ai_workspace_access(self.user)
        self.client.force_login(self.user)
        self.note = AIMemoryNote.objects.create(user=self.user, title="Savings goal", body="500000 EGP by June 2027")
        self.theirs = AIMemoryNote.objects.create(user=self.other, title="Not mine", body="x")

    def test_requires_login(self):
        self.client.logout()
        self.assertIn(self.client.get(API).status_code, (401, 302, 403))

    def test_list_returns_only_own_notes(self):
        items = self.client.get(API).json()["items"]
        self.assertEqual([i["title"] for i in items], ["Savings goal"])

    def test_since_returns_only_newer_notes(self):
        stamp = self.note.updated_at.isoformat()
        self.assertEqual(self.client.get(API, {"since": stamp}).json()["items"], [])
        newer = AIMemoryNote.objects.create(user=self.user, title="Fresh", body="b")
        items = self.client.get(API, {"since": stamp}).json()["items"]
        self.assertEqual([i["id"] for i in items], [newer.id])

    def test_edit_own_note(self):
        res = self.client.patch(f"{API}{self.note.id}/", json.dumps({"body": "600000 EGP by Dec 2027"}), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(AIMemoryNote.objects.get(pk=self.note.id).body, "600000 EGP by Dec 2027")

    def test_edit_rejects_empty_and_foreign(self):
        empty = self.client.patch(f"{API}{self.note.id}/", json.dumps({"title": "  "}), content_type="application/json")
        self.assertEqual(empty.status_code, 400)
        foreign = self.client.patch(f"{API}{self.theirs.id}/", json.dumps({"body": "x"}), content_type="application/json")
        self.assertEqual(foreign.status_code, 404)
        self.assertEqual(self.client.patch(f"{API}{self.note.id}/", "not json", content_type="application/json").status_code, 400)

    def test_delete_own_note_only(self):
        self.assertEqual(self.client.delete(f"{API}{self.theirs.id}/").status_code, 404)
        self.assertEqual(self.client.delete(f"{API}{self.note.id}/").status_code, 200)
        self.assertFalse(AIMemoryNote.objects.filter(pk=self.note.id).exists())
        self.assertTrue(AIMemoryNote.objects.filter(pk=self.theirs.id).exists())


class MemoryCommandTests(MemoryTestBase):
    """The chat model obeys "remember / forget / from now on" during the chat itself, like Claude does."""

    def _call(self, name, params, user=None):
        return validate_and_execute_tool(name, params, user or self.user)

    def test_all_three_memory_tools_are_offered_in_every_domain(self):
        for domain in (None, "business_data_analysis", "app_features_architecture"):
            names = {s["function"]["name"] for s in get_registered_tool_schemas(domain=domain)}
            self.assertTrue({"read_memory", "save_memory", "forget_memory"} <= names, domain)

    def test_remember_saves_a_note_at_once(self):
        audit, res = self._call("save_memory", {"title": "Savings goal", "body": "500000 EGP by June 2027"})
        self.assertEqual(audit["status"], "success")
        self.assertTrue(res["data"]["ok"])
        self.assertEqual(AIMemoryNote.objects.get(user=self.user).body, "500000 EGP by June 2027")

    def test_remember_with_an_id_updates_instead_of_duplicating(self):
        note = AIMemoryNote.objects.create(user=self.user, title="Savings goal", body="old")
        self._call("save_memory", {"id": note.id, "title": "Savings goal", "body": "600000 EGP by Dec 2027"})
        self.assertEqual(AIMemoryNote.objects.filter(user=self.user).count(), 1)
        self.assertEqual(AIMemoryNote.objects.get(pk=note.id).body, "600000 EGP by Dec 2027")

    def test_standing_instruction_is_always_on_and_shown_in_full(self):
        self._call("save_memory", {"title": "Do not ask about currency", "body": "User wants EGP only; never ask which currency again.", "always": True})
        self.assertTrue(AIMemoryNote.objects.get(user=self.user).always)
        block = build_memory_block(self.user, "unrelated question")
        self.assertIn("STANDING INSTRUCTIONS", block)
        self.assertIn("never ask which currency again", block)

    def test_forget_deletes_the_users_own_note_only(self):
        mine = AIMemoryNote.objects.create(user=self.user, title="Car loan", body="7000 EGP monthly")
        theirs = AIMemoryNote.objects.create(user=self.other, title="Car loan", body="x")
        _audit, res = self._call("forget_memory", {"ids": [mine.id, theirs.id]})
        self.assertEqual(res["data"]["forgotten"], ["Car loan"])
        self.assertFalse(AIMemoryNote.objects.filter(pk=mine.id).exists())
        self.assertTrue(AIMemoryNote.objects.filter(pk=theirs.id).exists())
        _audit, none = self._call("forget_memory", {"ids": [theirs.id]})
        self.assertIn("error", none["data"])

    def test_missing_title_or_body_is_rejected(self):
        _audit, res = self._call("save_memory", {"title": "Only a title", "body": "  "})
        self.assertIn("error", res["data"])
        self.assertEqual(AIMemoryNote.objects.count(), 0)

    def test_memory_tools_work_in_read_only_mode(self):
        AISetting.set("ai_read_only", "true")
        audit, res = self._call("save_memory", {"title": "Goal", "body": "text"})
        self.assertEqual(audit["status"], "success")
        self.assertTrue(res["data"]["ok"])

    def test_prompt_tells_the_model_how_to_obey_memory_commands(self):
        for block in (build_memory_block(self.user), build_memory_block(self.user, "x") if AIMemoryNote.objects.create(user=self.user, title="t", body="b") else ""):
            self.assertIn("save_memory", block)
            self.assertIn("forget_memory", block)
            self.assertIn("always=true", block)

    def test_standing_notes_are_the_last_dropped_when_the_cap_is_reached(self):
        keep = AIMemoryNote.objects.create(user=self.user, title="Standing", body="b", always=True)
        for i in range(MAX_NOTES + 2):
            AIMemoryNote.objects.create(user=self.user, title=f"n{i}", body="b")
        apply_edits(self.user, {"notes": [{"title": "newest", "body": "b"}]})
        self.assertTrue(AIMemoryNote.objects.filter(pk=keep.id).exists())

    def test_writer_is_told_to_honour_forget_and_standing_requests_and_saves_always(self):
        provider = _provider('{"notes": [{"title": "No currency questions", "body": "EGP only", "always": true}], "delete": []}')
        saved = update_memory(self.user, self.conv, provider)
        system = provider.generate.call_args[0][0][0]["content"]
        self.assertIn("forget", system)
        self.assertIn("\"always\": true", system)
        self.assertTrue(saved[0].always)

    def test_chip_window_starts_at_the_users_message_so_a_note_saved_during_the_reply_counts(self):
        grant_ai_workspace_access(self.user)
        AISetting.set("ai_direct_answers", "false")
        self.client.force_login(self.user)
        chat_provider = MagicMock()
        chat_provider.supports_tools = True
        chat_provider.generate.return_value = {"content": "ok", "tool_calls": None, "prompt_tokens": 1, "completion_tokens": 1, "error": None}
        with patch("ai.views.ai_chat.ai_chat_core_views.get_active_ai_provider", return_value=chat_provider):
            res = self.client.post("/api/financial-advisor/ai/chat/", json.dumps({"message": "remember my goal"}), content_type="application/json").json()
        self.assertEqual(res["memory_since"], res["user_message"]["created_at"])

    def test_page_can_toggle_always(self):
        grant_ai_workspace_access(self.user)
        self.client.force_login(self.user)
        note = AIMemoryNote.objects.create(user=self.user, title="t", body="b")
        res = self.client.patch(f"{API}{note.id}/", json.dumps({"always": True}), content_type="application/json")
        self.assertTrue(res.json()["item"]["always"])
