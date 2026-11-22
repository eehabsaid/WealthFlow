

import json
from unittest.mock import patch

from ai.models import AISetting
from ai.models.ai_conversation import AIConversation
from ai.models.ai_message import AIMessage
from ai.integrations.ai_provider import OllamaProvider
from .ai_chat_views_support import AIChatViewsBase


class AIChatViewsInvestigationTest(AIChatViewsBase):
    def test_ai_chat_view_unauthenticated(self):
        res = self.client.post("/api/financial-advisor/ai/chat/", json.dumps({"message": "Hi"}), content_type="application/json")
        self.assertEqual(res.status_code, 401)

    def test_ai_chat_view_user_message_saved_when_disabled(self):
        self.client.force_login(self.user)
        AISetting.set("ai_enabled", "false")

        res = self.client.post(
            "/api/financial-advisor/ai/chat/",
            json.dumps({"message": "What is my cash flow?"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["ok"])
        self.assertEqual(data["error_key"], "ai_chat_disabled_desc")
        self.assertIn("user_message", data)

        # Confirm user message was saved to database
        conv_id = data["conversation_id"]
        conv = AIConversation.objects.get(id=conv_id)
        user_msgs = conv.messages.filter(role="user")
        self.assertEqual(user_msgs.count(), 1)
        self.assertEqual(user_msgs.first().content, "What is my cash flow?")

    @patch.object(OllamaProvider, "generate")
    def test_ai_chat_view_success_flow(self, mock_generate):
        mock_generate.return_value = {
            "content": "Your projected monthly cash flow is positive 5,000 EGP.",
            "error": None,
        }

        self.client.force_login(self.user)
        AISetting.set("ai_enabled", "true")
        AISetting.set("ai_provider", "ollama")
        AISetting.set("ai_history_window", "10")
        # This test canned-mocks an invented figure (5,000) that isn't in the user's data;
        # figure validation is covered in test_chat_pipeline.py.
        AISetting.set("ai_validate_mode", "off")

        res = self.client.post(
            "/api/financial-advisor/ai/chat/",
            json.dumps({"message": "Predict my cash flow"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["ok"])
        self.assertIn("message", data)
        self.assertEqual(data["message"]["content"], "Your projected monthly cash flow is positive 5,000 EGP.")
        self.assertIn("sources", data)

    def test_ai_conversation_list_and_detail_views(self):
        self.client.force_login(self.user)
        conv = AIConversation.objects.create(user=self.user, title="Test Conversation")
        AIMessage.objects.create(conversation=conv, role="user", content="Test question")

        # GET list
        res_list = self.client.get("/api/financial-advisor/ai/conversations/")
        self.assertEqual(res_list.status_code, 200)
        convs = res_list.json()["conversations"]
        self.assertEqual(len(convs), 1)
        self.assertEqual(convs[0]["id"], conv.id)

        # GET detail
        res_detail = self.client.get(f"/api/financial-advisor/ai/conversations/{conv.id}/")
        self.assertEqual(res_detail.status_code, 200)
        detail_data = res_detail.json()["conversation"]
        self.assertEqual(len(detail_data["messages"]), 1)

        # DELETE soft-delete
        res_del = self.client.delete(f"/api/financial-advisor/ai/conversations/{conv.id}/")
        self.assertEqual(res_del.status_code, 200)
        self.assertTrue(res_del.json()["ok"])

        # Confirm soft-deleted
        conv.refresh_from_db()
        self.assertTrue(conv.is_deleted)
