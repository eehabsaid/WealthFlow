"""Second round: duplicate cards, cancelling stale cards on edit-and-resend, the action tools in Agent mode, the "you CAN change records" notice,
and the voice-sample status."""

import os
import shutil
import tempfile
from unittest.mock import MagicMock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from ai.models.ai_chat_block import AIChatBlock
from ai.models.ai_conversation import AIConversation
from ai.models.ai_message import AIMessage
from ai.services.actions import propose_action
from ai.services.actions.notice import NOTICE, ActionNoticeProvider
from ai.services.domains import BUSINESS
from ai.services.investigation import investigation_tool_schemas
from ai.services.speech.voice_sample import delete_voice_sample, save_voice_sample, voice_sample_info
from core.tests.ai_pack.test_ai_actions_charts import API, Base

COFFEE = {"record": "expense", "op": "add", "values": {"amount": "50", "currency": "EGP", "description": "coffee", "category": "Food", "payment_method": "Cash"}}


def same_but_capitalised():
    return {**COFFEE, "values": {**COFFEE["values"], "description": "Coffee"}}


class DuplicateCardTests(Base):
    def test_the_same_proposal_twice_shows_one_card_even_with_different_capitals(self):
        first = propose_action(self.user, COFFEE)
        second = propose_action(self.user, same_but_capitalised())
        self.assertEqual(first["card_id"], second["card_id"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(AIChatBlock.objects.count(), 1)

    def test_a_different_amount_is_a_different_card(self):
        propose_action(self.user, COFFEE)
        propose_action(self.user, {**COFFEE, "values": {**COFFEE["values"], "amount": "60"}})
        self.assertEqual(AIChatBlock.objects.count(), 2)

    def test_another_users_card_is_never_reused(self):
        propose_action(self.user, COFFEE)
        self.assertEqual(AIChatBlock.objects.filter(user=self.other).count(), 0)

    def test_propose_action_cannot_write_code(self):
        res = propose_action(self.user, {"record": "code_file", "op": "edit", "values": {}})
        self.assertIn("error", res)
        self.assertEqual(AIChatBlock.objects.count(), 0)


class RewindCancelsCardsTests(Base):
    def test_unconfirmed_cards_of_hidden_messages_are_cancelled_and_confirmed_ones_stay(self):
        conv = AIConversation.objects.create(user=self.user, title="c")
        user_msg = AIMessage.objects.create(conversation=conv, role="user", content="add coffee 50")
        reply = AIMessage.objects.create(conversation=conv, role="assistant", content="card below")
        pending = propose_action(self.user, COFFEE)["card_id"]
        done = propose_action(self.user, {**COFFEE, "values": {**COFFEE["values"], "amount": "70"}})["card_id"]
        AIChatBlock.objects.filter(pk=done).update(status="confirmed")
        AIChatBlock.objects.filter(pk__in=[pending, done]).update(message=reply)
        self.assertEqual(self.client.post(API + f"messages/{user_msg.id}/rewind/").status_code, 200)
        self.assertEqual(AIChatBlock.objects.get(pk=pending).status, "cancelled")
        self.assertEqual(AIChatBlock.objects.get(pk=done).status, "confirmed")
        self.assertEqual(self.client.post(API + f"blocks/{pending}/confirm/").status_code, 409)


class AgentToolsAndNoticeTests(Base):
    def test_agent_loop_offers_the_action_and_chart_tools_in_every_domain(self):
        for domain in ("", BUSINESS):
            names = {s["function"]["name"] for s in investigation_tool_schemas(self.user, domain)}
            self.assertTrue({"propose_action", "show_chart"} <= names, domain)

    def test_the_notice_is_added_to_the_system_message_and_calls_are_passed_through(self):
        inner = MagicMock()
        inner.generate.return_value = {"content": "ok"}
        inner.supports_tools = True
        wrapped = ActionNoticeProvider(inner)
        out = wrapped.generate([{"role": "system", "content": "SYS"}, {"role": "user", "content": "add"}], tools=[1], temperature=0.1)
        sent = inner.generate.call_args.args[0]
        self.assertTrue(sent[0]["content"].startswith("SYS") and NOTICE in sent[0]["content"])
        self.assertEqual((out, inner.generate.call_args.kwargs, wrapped.supports_tools), ({"content": "ok"}, {"tools": [1], "temperature": 0.1}, True))

    def test_no_system_message_gets_one(self):
        inner = MagicMock()
        ActionNoticeProvider(inner).generate([{"role": "user", "content": "x"}])
        self.assertEqual(inner.generate.call_args.args[0][0], {"role": "system", "content": NOTICE})

    def test_the_notice_says_never_claim_read_only_and_names_both_tools(self):
        for needle in ("propose_action", "show_chart", "read-only", "Confirm"):
            self.assertIn(needle, NOTICE)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class VoiceSampleStatusTests(Base):
    def tearDown(self):
        from django.conf import settings
        shutil.rmtree(os.path.join(settings.MEDIA_ROOT, "voice_samples"), ignore_errors=True)

    def test_info_names_the_uploaded_file_and_its_size(self):
        self.assertEqual(voice_sample_info(), {"has_sample": False, "name": "", "size_kb": 0})
        save_voice_sample("my voice.wav", b"RIFF" + b"\x00" * 40000)
        info = voice_sample_info()
        self.assertEqual((info["has_sample"], info["name"], info["size_kb"]), (True, "my voice.wav", 39))
        delete_voice_sample()
        self.assertEqual(voice_sample_info()["name"], "")

    def test_upload_response_carries_the_name_so_the_page_can_say_it_was_saved(self):
        from core.authentication.services import AuthWorkflowService
        profile = AuthWorkflowService.get_profile(self.user)
        profile.is_sysadmin = True
        profile.save()
        url = "/api/settings/ai/speech/voice-sample/"
        res = self.client.post(url, {"file": SimpleUploadedFile("me.wav", b"RIFF" + b"\x00" * 40000)})
        self.assertEqual((res.status_code, res.json()["name"], res.json()["has_sample"]), (201, "me.wav", True))
        short = self.client.post(url, {"file": SimpleUploadedFile("tiny.wav", b"RIFF")})
        self.assertEqual(short.status_code, 400)
        self.assertNotIn("10 seconds", short.json()["message"])


class ChatViewAppliesNoticeTests(Base):
    def test_ask_mode_model_call_for_a_change_request_carries_the_notice(self):
        from unittest.mock import patch

        prov = MagicMock()
        prov.supports_tools = True
        prov.generate.side_effect = lambda *a, **k: {"content": "ok", "tool_calls": None, "error": None}
        with patch("ai.views.ai_chat.ai_chat_core_views.get_active_ai_provider", return_value=prov):
            res = self.client.post(API + "chat/", {"message": "add an expense of 50 for coffee today", "chat_mode": "ask"}, content_type="application/json")
        self.assertEqual(res.status_code, 200)
        sent = "\n".join(str(m.get("content")) for call in prov.generate.call_args_list for m in call.args[0])
        self.assertIn(NOTICE, sent)
