"""Settings > Billing 'Test connection' for SAR/AED Paymob accounts. Network is always mocked."""

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import AppSettings
from core.services.ai.credential_encryption import encrypt_credential
from core.services.billing.paymob_gateway import PaymobGateway, region_key

User = get_user_model()
HTTP = "core.services.billing.paymob_gateway.make_json_http_request"


def _save(code="SAR", host="ksa.paymob.com", key="pm-key"):
    AppSettings.set(region_key(code, "base_url"), host)
    AppSettings.set(region_key(code, "api_key"), encrypt_credential(key) if key else "")


class PaymobTestConnectionServiceTests(TestCase):
    def test_not_configured(self):
        self.assertEqual(PaymobGateway.test_connection("SAR")["error_key"], "paymob_test_not_configured")

    def test_bad_host_never_calls_network(self):
        _save(host="evil.example.com")
        with patch(HTTP) as http:
            res = PaymobGateway.test_connection("SAR")
        self.assertEqual(res["error_key"], "paymob_test_bad_host")
        http.assert_not_called()

    def test_success_uses_the_regional_host(self):
        _save()
        with patch(HTTP, return_value=({"token": "t"}, 201, None)) as http:
            res = PaymobGateway.test_connection("SAR")
        self.assertTrue(res["ok"])
        self.assertEqual(res["host"], "ksa.paymob.com")
        self.assertTrue(http.call_args[0][0].startswith("https://ksa.paymob.com/api/auth/tokens"))

    def test_rejection_is_clear_and_redacts_the_key(self):
        _save(key="super-secret-key")
        with patch(HTTP, return_value=(None, 401, "bad super-secret-key")):
            res = PaymobGateway.test_connection("SAR")
        self.assertEqual(res["error_key"], "paymob_test_auth_failed")
        self.assertNotIn("super-secret-key", res["detail"])


class PaymobTestEndpointTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("root", "r@example.com", "Pass12345!")
        self.admin.profile.is_sysadmin = True
        self.admin.profile.save(update_fields=["is_sysadmin"])

    def _post(self, body):
        return self.client.post("/api/settings/billing/gateway/test/", json.dumps(body), content_type="application/json")

    def test_requires_admin(self):
        self.assertIn(self._post({"currency": "SAR"}).status_code, (302, 401, 403))

    def test_only_regional_currencies(self):
        self.client.force_login(self.admin)
        self.assertEqual(self._post({"currency": "EGP"}).status_code, 400)

    def test_returns_result(self):
        self.client.force_login(self.admin)
        _save("AED", "uae.paymob.com")
        with patch(HTTP, return_value=({"token": "t"}, 201, None)):
            body = self._post({"currency": "aed"}).json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["host"], "uae.paymob.com")
