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


class PaymobRegionalSettingsTestCase(TestCase):
    """Gulf (SAR/AED) regional Paymob accounts in the same settings endpoint."""

    URL = "/api/settings/billing/gateway/"

    def setUp(self):
        PaymobGatewaySettingsTestCase.setUp(self)

    def _post(self, body):
        return self.client.post(self.URL, data=json.dumps(body), content_type="application/json")

    def _sar(self, **extra):
        return {"regions": {"SAR": {
            "api_key": "ksa_key_1234", "hmac_secret": "ksa_hmac_5678",
            "integration_id": "333", "iframe_id": "444", "base_url": "ksa.paymob.com", **extra,
        }}}

    def test_regions_start_empty_and_unconfigured(self):
        self.client.force_login(self.admin)
        data = self.client.get(self.URL).json()
        self.assertEqual(set(data["regions"]), {"SAR", "AED"})
        self.assertFalse(data["regions"]["SAR"]["is_configured"])
        self.assertEqual(data["paymob_default_currencies"], "EGP")

    def test_save_region_masks_secrets_and_marks_configured(self):
        self.client.force_login(self.admin)
        self.assertEqual(self._post(self._sar()).status_code, 200)
        sar = self.client.get(self.URL).json()["regions"]["SAR"]
        self.assertTrue(sar["is_configured"])
        self.assertIn("••••", sar["api_key"])
        self.assertNotIn("ksa_key_1234", json.dumps(sar))
        self.assertEqual(sar["base_url"], "ksa.paymob.com")

    def test_masked_round_trip_keeps_region_secrets(self):
        self.client.force_login(self.admin)
        self._post(self._sar())
        masked = self.client.get(self.URL).json()["regions"]["SAR"]
        self._post({"regions": {"SAR": {"api_key": masked["api_key"], "hmac_secret": masked["hmac_secret"], "iframe_id": "444"}}})
        self.assertTrue(self.client.get(self.URL).json()["regions"]["SAR"]["is_configured"])

    def test_non_paymob_host_is_rejected(self):
        self.client.force_login(self.admin)
        for host in ("evil.example.com", "https://paymob.com.evil.io", "http://169.254.169.254"):
            res = self._post(self._sar(base_url=host))
            self.assertEqual(res.status_code, 400, host)
        self.assertFalse(self.client.get(self.URL).json()["regions"]["SAR"]["is_configured"])

    def test_bad_region_code_and_default_currencies_rejected(self):
        self.client.force_login(self.admin)
        self.assertEqual(self._post({"regions": {"sar!": {}}}).status_code, 400)
        self.assertEqual(self._post({"paymob_default_currencies": "EGP,12"}).status_code, 400)
        self.assertEqual(self._post({"paymob_default_currencies": ""}).status_code, 400)

    def test_default_currencies_saved_normalized(self):
        self.client.force_login(self.admin)
        self._post({"paymob_default_currencies": "egp; usd, EGP"})
        self.assertEqual(self.client.get(self.URL).json()["paymob_default_currencies"], "EGP,USD")

    def test_regions_require_admin(self):
        self.client.force_login(self.plain_user)
        self.assertIn(self._post(self._sar()).status_code, (401, 403))
