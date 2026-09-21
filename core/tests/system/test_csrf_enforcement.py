import json
import pathlib

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

User = get_user_model()
CORE = pathlib.Path(__file__).resolve().parents[2]


class CsrfEnforcementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="csrf_user", password="pw12345")
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.user)

    def _post(self, **extra):
        return self.client.post(
            "/api/onboarding/complete/", data=json.dumps({}), content_type="application/json", **extra
        )

    def test_post_without_token_is_rejected(self):
        self.assertEqual(self._post().status_code, 403)

    def test_post_with_token_is_accepted(self):
        self.client.get("/")  # index sets the csrftoken cookie
        token = self.client.cookies["csrftoken"].value
        response = self._post(HTTP_X_CSRFTOKEN=token)
        self.assertNotEqual(response.status_code, 403)

    def test_index_sets_csrf_cookie(self):
        self.client.get("/")
        self.assertIn("csrftoken", self.client.cookies)

    def test_paymob_webhook_stays_exempt_and_hmac_protected(self):
        anon = Client(enforce_csrf_checks=True)
        response = anon.post("/api/billing/paymob/webhook/", data="{}", content_type="application/json")
        self.assertEqual(response.json(), {"error": "Invalid signature"})

    def test_only_paymob_webhook_uses_csrf_exempt(self):
        offenders = []
        for path in CORE.rglob("*.py"):
            if "tests" in path.parts:
                continue
            if "csrf_exempt" in path.read_text(encoding="utf-8"):
                offenders.append(path.name)
        self.assertEqual(offenders, ["billing_views.py"])
