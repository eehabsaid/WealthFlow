"""Shared fixtures for the legal text tests."""


import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.authentication.services import AuthWorkflowService
from core.services.legal import clear_cache


User = get_user_model()


def _sections(*pairs):
    return [{"title": t, "body": b} for t, b in pairs]


class LegalTextBase(TestCase):
    def setUp(self):
        clear_cache()
        self.admin = User.objects.create_user(username="boss", password="pw12345")
        p = AuthWorkflowService.get_profile(self.admin)
        p.is_sysadmin = True
        p.save(update_fields=["is_sysadmin"])
        self.member = User.objects.create_user(username="mem", password="pw12345")
        AuthWorkflowService.get_profile(self.member)

    def tearDown(self):
        clear_cache()

    def publish(self, label="v1", reconsent=False, content=None, client=None):
        client = client or self.client
        client.force_login(self.admin)
        content = content or {"en": {"terms": {"title": "My Terms", "sections": _sections(("A", "Body A\nline2"))}}}
        return client.post(
            "/api/settings/legal/",
            data=json.dumps({"label": label, "content": content, "require_reconsent": reconsent}),
            content_type="application/json",
        )
