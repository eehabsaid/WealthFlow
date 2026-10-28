"""Cross-chat AI memory: notes the model writes itself, the budgeted index in the prompt, the read_memory tool,
the background writer, and the view/edit/delete API."""

import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import AIConversation, AIMemoryNote, AIMessage, AppSettings
from core.services.ai.context_builder_service import ContextBuilderService
from core.services.ai.memory import apply_edits, build_memory_block, schedule_memory_update, update_memory
from core.services.ai.memory.scheduler import _run
from core.services.ai.memory.store import MAX_NOTES
from core.services.ai.tools import validate_and_execute_tool
from core.services.ai.tools.defs import get_registered_tool_schemas
from core.tests.billing.test_support import grant_ai_workspace_access

User = get_user_model()
API = "/api/financial-advisor/ai/memory/"


def _provider(content):
    provider = MagicMock()
    provider.generate.return_value = {"content": content, "error": None}
    return provider


class MemoryTestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="member", password="pw12345!")
        self.other = User.objects.create_user(username="other", password="pw12345!")
        self.conv = AIConversation.objects.create(user=self.user)
        AIMessage.objects.create(conversation=self.conv, role="user", content="My goal is to save 500000 EGP by June 2027")
        AIMessage.objects.create(conversation=self.conv, role="assistant", content="At your current pace you reach it in August 2027.")


class StoreTests(MemoryTestBase):
    def test_create_then_update_in_place_without_duplicating(self):
        first = apply_edits(self.user, {"notes": [{"id": None, "title": "Savings goal", "body": "500000 EGP by June 2027"}]}, self.conv.id)[0]
        again = apply_edits(self.user, {"notes": [{"id": first.id, "title": "Savings goal", "body": "500000 EGP by June 2027; pace says August 2027 (2026-10-27)"}]})
        self.assertEqual(AIMemoryNote.objects.filter(user=self.user).count(), 1)
        self.assertEqual(again[0].id, first.id)
        self.assertIn("August 2027", AIMemoryNote.objects.get(pk=first.id).body)

    def test_foreign_id_never_edits_or_deletes_another_users_note(self):
        mine = AIMemoryNote.objects.create(user=self.other, title="Private", body="secret")
        apply_edits(self.user, {"notes": [{"id": mine.id, "title": "x", "body": "hijack"}], "delete": [mine.id]})
        self.assertEqual(AIMemoryNote.objects.get(pk=mine.id).body, "secret")
        self.assertEqual(AIMemoryNote.objects.filter(user=self.user).count(), 1)   # became the caller's own new note

    def test_delete_own_note_and_ignore_bad_items(self):
        note = AIMemoryNote.objects.create(user=self.user, title="Old", body="old")
        apply_edits(self.user, {"notes": [{"title": "", "body": "no title"}, "junk", {"title": "t"}], "delete": [note.id, "x"]})
        self.assertEqual(AIMemoryNote.objects.filter(user=self.user).count(), 0)

    def test_notes_are_capped_oldest_first(self):
        for i in range(MAX_NOTES + 3):
            AIMemoryNote.objects.create(user=self.user, title=f"n{i}", body="b")
        apply_edits(self.user, {"notes": [{"title": "newest", "body": "b"}]})
        titles = set(AIMemoryNote.objects.filter(user=self.user).values_list("title", flat=True))
        self.assertEqual(len(titles), MAX_NOTES)
        self.assertIn("newest", titles)
        self.assertNotIn("n0", titles)


class WriterTests(MemoryTestBase):
    def test_model_decides_and_notes_are_saved(self):
        reply = '```json\n{"notes": [{"id": null, "title": "Savings goal", "body": "500000 EGP by June 2027; on pace for August 2027 (2026-10-27)"}], "delete": []}\n```'
        saved = update_memory(self.user, self.conv, _provider(reply))
        self.assertEqual([n.title for n in saved], ["Savings goal"])
        self.assertEqual(AIMemoryNote.objects.get().source_conversation_id, self.conv.id)

    def test_nothing_worth_remembering_stores_nothing(self):
        self.assertEqual(update_memory(self.user, self.conv, _provider('{"notes": [], "delete": []}')), [])
        self.assertEqual(AIMemoryNote.objects.count(), 0)

    def test_garbage_and_provider_errors_store_nothing(self):
        self.assertEqual(update_memory(self.user, self.conv, _provider("I think you should save more")), [])
        failing = MagicMock()
        failing.generate.return_value = {"content": "", "error": "timeout"}
        self.assertEqual(update_memory(self.user, self.conv, failing), [])
        self.assertEqual(update_memory(self.user, self.conv, None), [])

    def test_existing_notes_are_shown_to_the_model_so_it_can_edit_them(self):
        note = AIMemoryNote.objects.create(user=self.user, title="Savings goal", body="500000 EGP by June 2027")
        provider = _provider('{"notes": [], "delete": []}')
        update_memory(self.user, self.conv, provider)
        sent = provider.generate.call_args[0][0]
        self.assertIn(f"#{note.id}", sent[1]["content"])
        self.assertIn("500000 EGP by June 2027", sent[1]["content"])

    def test_prompt_size_follows_the_ui_token_budget(self):
        for i in range(40):
            AIMemoryNote.objects.create(user=self.user, title=f"t{i}", body="x" * 600)
        provider = _provider('{"notes": []}')
        update_memory(self.user, self.conv, provider)
        small = len(provider.generate.call_args[0][0][1]["content"])
        AppSettings.set("ai_context_token_budget", "16000")
        provider2 = _provider('{"notes": []}')
        update_memory(self.user, self.conv, provider2)
        self.assertGreater(len(provider2.generate.call_args[0][0][1]["content"]), small)
        self.assertLessEqual(small, 2048 * 4)

    def test_chat_without_an_answer_is_skipped(self):
        empty = AIConversation.objects.create(user=self.user)
        AIMessage.objects.create(conversation=empty, role="user", content="hi")
        provider = _provider("{}")
        self.assertEqual(update_memory(self.user, empty, provider), [])
        provider.generate.assert_not_called()


class IndexAndPromptTests(MemoryTestBase):
    def test_no_notes_still_tells_the_model_it_has_memory(self):
        block = build_memory_block(self.user, "anything")
        self.assertIn("You remember across chats", block)
        self.assertIn("No notes are saved yet", block)

    def test_writer_sets_no_small_output_cap_so_a_thinking_model_can_answer(self):
        provider = _provider('{"notes": [], "delete": []}')
        update_memory(self.user, self.conv, provider)
        self.assertNotIn("max_tokens", provider.generate.call_args.kwargs)

    def test_index_is_one_dated_line_per_note_and_user_scoped(self):
        note = AIMemoryNote.objects.create(user=self.user, title="Savings goal", body="500000 EGP by June 2027")
        AIMemoryNote.objects.create(user=self.other, title="Other person's note", body="x")
        block = build_memory_block(self.user, "")
        self.assertIn(f"#{note.id} [{note.updated_at:%Y-%m-%d}] Savings goal", block)
        self.assertNotIn("Other person", block)
        self.assertNotIn("500000", block)   # the body stays closed until the model opens it

    def test_index_never_exceeds_the_given_budget(self):
        for i in range(200):
            AIMemoryNote.objects.create(user=self.user, title=f"A fairly long note title number {i}", body="b")
        self.assertLessEqual(len(build_memory_block(self.user, "", token_limit=150)), 150 * 4)
        self.assertIn("older notes", build_memory_block(self.user, "", token_limit=150))

    def test_matching_notes_are_preloaded_for_weak_tool_callers(self):
        AIMemoryNote.objects.create(user=self.user, title="Savings goal", body="500000 EGP by June 2027")
        AIMemoryNote.objects.create(user=self.user, title="Car loan", body="installment 7000 EGP monthly")
        block = build_memory_block(self.user, "what is my savings goal for June?")
        self.assertIn("500000 EGP by June 2027", block)
        self.assertNotIn("installment", block)

    def test_system_prompt_carries_the_index_sized_from_the_ui_budget(self):
        AIMemoryNote.objects.create(user=self.user, title="Savings goal", body="500000 EGP by June 2027")
        self.assertIn("Savings goal", ContextBuilderService().build_system_prompt(user=self.user, query="hello"))
        self.assertNotIn("Savings goal", ContextBuilderService().build_system_prompt(user=self.other, query="hello"))

    def test_memory_reaches_a_new_chat_through_assemble_messages(self):
        AIMemoryNote.objects.create(user=self.user, title="Savings goal", body="500000 EGP by June 2027")
        messages, _sources = ContextBuilderService().assemble_messages("hello", [], user=self.user)
        self.assertIn("LONG-TERM MEMORY", messages[0]["content"])


class ReadMemoryToolTests(MemoryTestBase):
    def test_tool_is_offered_in_every_domain(self):
        for domain in (None, "business_data_analysis", "app_features_architecture"):
            names = {s["function"]["name"] for s in get_registered_tool_schemas(domain=domain)}
            self.assertIn("read_memory", names, domain)

    def test_open_by_id_and_by_query_for_own_notes_only(self):
        mine = AIMemoryNote.objects.create(user=self.user, title="Savings goal", body="500000 EGP by June 2027")
        theirs = AIMemoryNote.objects.create(user=self.other, title="Savings goal", body="secret figure")
        audit, res = validate_and_execute_tool("read_memory", {"ids": [mine.id, theirs.id]}, self.user)
        self.assertEqual(audit["status"], "success")
        texts = [n["text"] for n in res["data"]["notes"]]
        self.assertEqual(texts, ["500000 EGP by June 2027"])
        _audit, by_query = validate_and_execute_tool("read_memory", {"query": "savings goal June"}, self.user)
        self.assertEqual(len(by_query["data"]["notes"]), 1)
        self.assertIn("reminders", res["data"]["note"])


class SchedulerTests(MemoryTestBase):
    def test_not_started_under_tests(self):
        self.assertFalse(schedule_memory_update(self.user.id, self.conv.id))

    def test_background_pass_runs_the_writer_with_the_users_provider(self):
        provider = _provider('{"notes": [{"title": "Savings goal", "body": "500000 EGP by June 2027"}]}')
        with patch("core.integrations.ai_provider.get_active_ai_provider", return_value=provider), patch("django.db.close_old_connections"):
            _run(self.user.id, self.conv.id)
        self.assertEqual(AIMemoryNote.objects.get(user=self.user).title, "Savings goal")

    def test_background_failure_never_raises(self):
        with patch("core.integrations.ai_provider.get_active_ai_provider", side_effect=RuntimeError("boom")), patch("django.db.close_old_connections"):
            _run(self.user.id, self.conv.id)

    def test_chat_reply_schedules_a_memory_pass(self):
        grant_ai_workspace_access(self.user)
        AppSettings.set("ai_direct_answers", "false")
        self.client.force_login(self.user)
        chat_provider = MagicMock()
        chat_provider.supports_tools = True
        chat_provider.generate.return_value = {"content": "ok", "tool_calls": None, "prompt_tokens": 1, "completion_tokens": 1, "error": None}
        with patch("core.views.ai_chat.ai_chat_core_views.get_active_ai_provider", return_value=chat_provider), \
                patch("core.services.ai.memory.schedule_memory_update") as scheduled:
            res = self.client.post("/api/financial-advisor/ai/chat/", json.dumps({"message": "hello there"}), content_type="application/json")
        self.assertTrue(res.json()["ok"])
        self.assertIn("memory_since", res.json())
        scheduled.assert_called_once()
        self.assertEqual(scheduled.call_args[0][0], self.user.id)


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
        AppSettings.set("ai_read_only", "true")
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
        AppSettings.set("ai_direct_answers", "false")
        self.client.force_login(self.user)
        chat_provider = MagicMock()
        chat_provider.supports_tools = True
        chat_provider.generate.return_value = {"content": "ok", "tool_calls": None, "prompt_tokens": 1, "completion_tokens": 1, "error": None}
        with patch("core.views.ai_chat.ai_chat_core_views.get_active_ai_provider", return_value=chat_provider):
            res = self.client.post("/api/financial-advisor/ai/chat/", json.dumps({"message": "remember my goal"}), content_type="application/json").json()
        self.assertEqual(res["memory_since"], res["user_message"]["created_at"])

    def test_page_can_toggle_always(self):
        grant_ai_workspace_access(self.user)
        self.client.force_login(self.user)
        note = AIMemoryNote.objects.create(user=self.user, title="t", body="b")
        res = self.client.patch(f"{API}{note.id}/", json.dumps({"always": True}), content_type="application/json")
        self.assertTrue(res.json()["item"]["always"])
