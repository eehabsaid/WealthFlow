import json

from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class PaymobGatewaySettingsTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="gw_admin", password="pass12345", email="gw@a.com"
        )
        from core.authentication.services import AuthWorkflowService
        profile = AuthWorkflowService.get_profile(self.admin)
        profile.is_sysadmin = True
        profile.save(update_fields=["is_sysadmin"])
        self.plain_user = User.objects.create_user(username="gw_user", password="pass12345")

    def test_requires_admin(self):
        self.client.force_login(self.plain_user)
        res = self.client.get("/api/settings/billing/gateway/")
        self.assertIn(res.status_code, (401, 403))

    def test_starts_unconfigured(self):
        self.client.force_login(self.admin)
        res = self.client.get("/api/settings/billing/gateway/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["is_configured"])
        self.assertEqual(data["paymob_api_key"], "")

    def test_save_then_get_returns_masked_secret(self):
        self.client.force_login(self.admin)
        res = self.client.post(
            "/api/settings/billing/gateway/",
            data=json.dumps(
                {
                    "paymob_api_key": "sk_live_abcd1234",
                    "paymob_hmac_secret": "hmac_secret_wxyz9876",
                    "paymob_integration_id": "12345",
                    "paymob_iframe_id": "67890",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["is_configured"])

        get_res = self.client.get("/api/settings/billing/gateway/")
        data = get_res.json()
        self.assertTrue(data["is_configured"])
        self.assertNotEqual(data["paymob_api_key"], "sk_live_abcd1234")
        self.assertIn("••••", data["paymob_api_key"])
        self.assertEqual(data["paymob_integration_id"], "12345")
        self.assertEqual(data["paymob_iframe_id"], "67890")

    def test_resubmitting_masked_value_does_not_wipe_stored_secret(self):
        self.client.force_login(self.admin)
        self.client.post(
            "/api/settings/billing/gateway/",
            data=json.dumps(
                {
                    "paymob_api_key": "sk_live_abcd1234",
                    "paymob_hmac_secret": "hmac_secret_wxyz9876",
                    "paymob_integration_id": "12345",
                    "paymob_iframe_id": "67890",
                }
            ),
            content_type="application/json",
        )
        masked = self.client.get("/api/settings/billing/gateway/").json()

        # Simulate the settings UI round-tripping the masked value back
        # (e.g. saving other fields without touching the secret inputs).
        self.client.post(
            "/api/settings/billing/gateway/",
            data=json.dumps(
                {
                    "paymob_api_key": masked["paymob_api_key"],
                    "paymob_hmac_secret": masked["paymob_hmac_secret"],
                    "paymob_integration_id": "12345",
                    "paymob_iframe_id": "67890",
                }
            ),
            content_type="application/json",
        )
        still_configured = self.client.get("/api/settings/billing/gateway/").json()
        self.assertTrue(still_configured["is_configured"])

    def test_clearing_a_field_makes_gateway_unconfigured_again(self):
        self.client.force_login(self.admin)
        self.client.post(
            "/api/settings/billing/gateway/",
            data=json.dumps(
                {
                    "paymob_api_key": "sk_live_abcd1234",
                    "paymob_hmac_secret": "hmac_secret_wxyz9876",
                    "paymob_integration_id": "12345",
                    "paymob_iframe_id": "67890",
                }
            ),
            content_type="application/json",
        )
        self.client.post(
            "/api/settings/billing/gateway/",
            data=json.dumps({"paymob_api_key": ""}),
            content_type="application/json",
        )
        data = self.client.get("/api/settings/billing/gateway/").json()
        self.assertFalse(data["is_configured"])
