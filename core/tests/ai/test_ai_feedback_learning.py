"""Zip 2 C: thumbs up/down on answers; approved how-to answers become retrievable examples; thumbs-down never reused."""

from __future__ import annotations

import json

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

from core.models import AIAnswerFeedback, AIConversation, AIMessage
from core.services.ai.app_knowledge import find_examples
from core.tests.ai.test_ai_workflow_chat import LAPTOP, PROVIDER, stub_provider
from core.tests.ai import qe_fixtures as fx
from core.tests.billing.test_support import grant_ai_workspace_access
from unittest.mock import patch

User = get_user_model()
SIMILAR = "I just bought a laptop, should I record its price in assets or in expenses?"


def feedback_url(pk):
    return f"/api/financial-advisor/ai/messages/{pk}/feedback/"


class FeedbackBase(TestCase):
    def setUp(self):
        fx.build(self)
        grant_ai_workspace_access(self.other)   # so the cross-tenant checks reach the view, not the plan gate
        self.conv = AIConversation.objects.create(user=self.user, title="t")
        AIMessage.objects.create(conversation=self.conv, role="user", content=LAPTOP)
        self.up = AIMessage.objects.create(conversation=self.conv, role="assistant", content="Record it as an asset.", sources=["app_knowledge"])

    def rate(self, pk, rating, client=None):
        return (client or self.client).post(feedback_url(pk), json.dumps({"rating": rating}), content_type="application/json")


class FeedbackApiTests(FeedbackBase):
    def test_up_down_flip_and_clear(self):
        self.assertEqual(self.rate(self.up.id, 1).json(), {"ok": True, "rating": 1})
        row = AIAnswerFeedback.objects.get(owner=self.user)
        self.assertEqual((row.rating, row.kind, row.question, row.answer), (1, "workflow", LAPTOP, "Record it as an asset."))
        self.assertEqual(self.rate(self.up.id, -1).json()["rating"], -1)
        self.assertEqual(AIAnswerFeedback.objects.filter(owner=self.user).count(), 1)   # flipped, not duplicated
        self.assertEqual(self.rate(self.up.id, 0).json(), {"ok": True, "rating": 0})
        self.assertEqual(AIAnswerFeedback.objects.count(), 0)

    def test_data_answers_are_marked_data_kind(self):
        msg = AIMessage.objects.create(conversation=self.conv, role="assistant", content="You have 5.", sources=["balance"])
        self.rate(msg.id, 1)
        self.assertEqual(AIAnswerFeedback.objects.get(message=msg).kind, "data")

    def test_validation_and_ownership(self):
        self.assertEqual(self.rate(self.up.id, 5).status_code, 400)
        self.assertEqual(self.client.post(feedback_url(self.up.id), "nope", content_type="application/json").status_code, 400)
        self.assertEqual(self.rate(99999999, 1).status_code, 404)
        user_msg = self.conv.messages.filter(role="user").first()
        self.assertEqual(self.rate(user_msg.id, 1).status_code, 404)   # only assistant answers can be rated
        self.client.force_login(self.other)
        self.assertEqual(self.rate(self.up.id, 1).status_code, 404)    # another tenant's answer
        self.assertEqual(AIAnswerFeedback.objects.count(), 0)

    def test_list_is_owner_scoped_and_conversation_detail_shows_rating(self):
        self.rate(self.up.id, 1)
        items = self.client.get("/api/financial-advisor/ai/feedback/").json()["items"]
        self.assertEqual([(i["message_id"], i["rating"]) for i in items], [(self.up.id, 1)])
        detail = self.client.get(f"/api/financial-advisor/ai/conversations/{self.conv.id}/").json()["conversation"]["messages"]
        self.assertEqual({m["id"]: m["feedback"] for m in detail}[self.up.id], 1)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get("/api/financial-advisor/ai/feedback/").json()["items"], [])

    def test_anonymous_is_rejected(self):
        self.client.logout()
        self.assertIn(self.client.get("/api/financial-advisor/ai/feedback/").status_code, (302, 401, 403))


class LearningTests(FeedbackBase):
    def test_approved_workflow_answer_is_found_for_similar_question(self):
        self.rate(self.up.id, 1)
        found = find_examples(self.user, SIMILAR)
        self.assertEqual([e["answer"] for e in found], ["Record it as an asset."])

    def test_unrelated_question_finds_nothing(self):
        self.rate(self.up.id, 1)
        self.assertEqual(find_examples(self.user, "where do I record my credit card payment?"), [])

    def test_thumbs_down_is_never_reused(self):
        self.rate(self.up.id, -1)
        self.assertEqual(find_examples(self.user, SIMILAR), [])
        self.assertEqual(find_examples(self.user, LAPTOP), [])

    def test_same_text_as_a_rejected_answer_is_not_reused_even_if_approved_elsewhere(self):
        twin = AIMessage.objects.create(conversation=self.conv, role="assistant", content="Record it as an asset.", sources=["app_knowledge"])
        self.rate(self.up.id, 1)
        self.rate(twin.id, -1)
        self.assertEqual(find_examples(self.user, SIMILAR), [])

    def test_cleared_rating_is_not_reused(self):
        self.rate(self.up.id, 1)
        self.rate(self.up.id, 0)
        self.assertEqual(find_examples(self.user, SIMILAR), [])

    def test_other_users_never_see_my_examples(self):
        self.rate(self.up.id, 1)
        self.assertEqual(find_examples(self.other, SIMILAR), [])

    def test_data_answers_are_not_reused(self):
        data_msg = AIMessage.objects.create(conversation=self.conv, role="assistant", content="You spent 1,000 EGP.", sources=["expenses"])
        AIAnswerFeedback.objects.create(owner=self.user, message=data_msg, question=LAPTOP, answer="You spent 1,000 EGP.", rating=1, kind="data")
        self.assertEqual(find_examples(self.user, SIMILAR), [])

    def test_approved_answer_reaches_the_prompt_in_a_real_chat_turn(self):
        self.rate(self.up.id, 1)
        prov = stub_provider()
        with patch(PROVIDER, return_value=prov):
            fx.ask(self, SIMILAR)
        system = prov.calls[0]["messages"][0]["content"]
        self.assertIn("ANSWERS THE USER APPROVED", system)
        self.assertIn("Record it as an asset.", system)

    def test_rejected_answer_never_reaches_the_prompt(self):
        self.rate(self.up.id, -1)
        prov = stub_provider()
        with patch(PROVIDER, return_value=prov):
            fx.ask(self, SIMILAR)
        self.assertNotIn("Record it as an asset.", prov.calls[0]["messages"][0]["content"])


class FallbackAnswerLearningTests(FeedbackBase):
    def test_retrieval_only_answer_can_be_rated_but_is_never_reused(self):
        cache.clear()
        with patch(PROVIDER, return_value=stub_provider(error="timed out")):
            data = fx.ask(self, LAPTOP)
        msg_id = data["message"]["id"]
        self.assertEqual(self.rate(msg_id, 1).json()["rating"], 1)
        self.assertEqual(AIAnswerFeedback.objects.get(message_id=msg_id).kind, "data")   # not "workflow"
        self.assertEqual(find_examples(self.user, SIMILAR), [])
