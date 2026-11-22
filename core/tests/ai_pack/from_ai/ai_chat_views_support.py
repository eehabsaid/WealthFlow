"""Shared base for the AI chat view tests."""


from django.contrib.auth import get_user_model
from django.test import TestCase

from ai.tests.support import grant_ai_workspace_access


User = get_user_model()


class AIChatViewsBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test_user", password="password123")
        self.admin = User.objects.create_user(username="admin_user", password="password123", is_staff=True)
        grant_ai_workspace_access(self.user)
