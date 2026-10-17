"""Settings > Billing: Stripe credentials endpoint (admin only, masked secrets)."""

import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.authentication.services import AuthWorkflowService
from core.models import AppSettings
from core.services.billing.stripe_gateway import StripeGateway

User = get_user_model()
URL = "/api/settings/billing/stripe/"


class StripeSettingsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="sg_admin", password="pass12345", email="sg@a.com")
        profile = AuthWorkflowService.get_profile(self.admin)
        profile.is_sysadmin = True
        profile.save(update_fields=["is_sysadmin"])
        self.plain = User.objects.create_user(username="sg_user", password="pass12345")

    def post(self, **body):
        return self.client.post(URL, data=json.dumps(body), content_type="application/json")

    def test_requires_admin(self):
        self.client.force_login(self.plain)
        self.assertIn(self.client.get(URL).status_code, (401, 403))
        self.assertIn(self.post(stripe_secret_key="sk_x").status_code, (401, 403))

    def test_starts_unconfigured_with_default_currencies(self):
        self.client.force_login(self.admin)
        data = self.client.get(URL).json()
        self.assertFalse(data["is_configured"])
        self.assertEqual((data["stripe_secret_key"], data["stripe_currencies"]), ("", "USD,EUR,GBP"))
        self.assertEqual(data["webhook_path"], "/api/billing/stripe/webhook/")

    def test_save_encrypts_masks_and_keeps_secret_when_masked_value_is_resubmitted(self):
        self.client.force_login(self.admin)
        res = self.post(stripe_secret_key="sk_test_abcd1234", stripe_webhook_secret="whsec_wxyz9876", stripe_currencies="usd, eur")
        data = res.json()
        self.assertTrue(data["is_configured"])
        self.assertNotIn("sk_test_abcd1234", json.dumps(data))
        self.assertNotEqual(AppSettings.get("stripe_secret_key", ""), "sk_test_abcd1234")
        self.assertEqual(data["stripe_currencies"], "USD,EUR")
        self.post(stripe_secret_key=data["stripe_secret_key"])
        self.assertEqual(StripeGateway.get_config()["secret_key"], "sk_test_abcd1234")

    def test_blank_clears_secret_and_bad_currencies_are_rejected(self):
        self.client.force_login(self.admin)
        self.post(stripe_secret_key="sk_test_1", stripe_webhook_secret="whsec_1")
        self.assertFalse(self.post(stripe_secret_key="").json()["is_configured"])
        for bad in ("", "US", "USD;12"):
            self.assertEqual(self.post(stripe_currencies=bad).status_code, 400, bad)
