"""Shared fixtures for the AI memory tests."""


from unittest.mock import MagicMock

from django.contrib.auth import get_user_model
from django.test import TestCase

from ai.models.ai_conversation import AIConversation
from ai.models.ai_message import AIMessage


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
