"""The guide screenshot URL: only the owner can open an image (host side: needs the plan feature)."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from ai.services.guide_shots import store
from core.tests.billing.test_support import grant_ai_workspace_access

User = get_user_model()


class GuideShotViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("shot_user", password="x")
        self.other = User.objects.create_user("other_user", password="x")
        grant_ai_workspace_access(self.user)
        grant_ai_workspace_access(self.other)
        store.save(self.user.pk, "aaaaaaaaaaaa", b"\xff\xd8\xff")

    def test_view_is_owner_scoped(self):
        url = store.URL.format(key="aaaaaaaaaaaa")
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(store.URL.format(key="../../etc")).status_code, 404)


