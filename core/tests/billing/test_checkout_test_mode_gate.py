"""Fake/test-mode checkout is gated by BILLING_TEST_MODE (default = DEBUG)."""

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from core.models import Currency, Invoice, Plan, PlanPrice
from core.services.billing.checkout_service import NO_GATEWAY_MESSAGE
from core.services.billing.subscription_service import SubscriptionService
from wealthflow.env_settings import build_security_settings

User = get_user_model()
_ANY = "core.services.billing.paymob_gateway.PaymobGateway.any_configured"


class BillingTestModeSettingTests(TestCase):
    def test_defaults_to_debug_value(self):
        self.assertTrue(build_security_settings({})["BILLING_TEST_MODE"])
        prod = build_security_settings({"WEALTHFLOW_DEBUG": "false", "WEALTHFLOW_SECRET_KEY": "x"})
        self.assertFalse(prod["BILLING_TEST_MODE"])

    def test_explicit_env_override(self):
        on = build_security_settings({"WEALTHFLOW_DEBUG": "false", "WEALTHFLOW_SECRET_KEY": "x", "WEALTHFLOW_BILLING_TEST_MODE": "true"})
        off = build_security_settings({"WEALTHFLOW_BILLING_TEST_MODE": "false"})
        self.assertTrue(on["BILLING_TEST_MODE"])
        self.assertFalse(off["BILLING_TEST_MODE"])


class CheckoutTestModeGateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="gate_user", password="pass12345")
        self.egp = Currency.objects.create(code="EGP", name="Egyptian Pound")
        self.plan = Plan.objects.create(code="gate_pro", name="Gate Pro", sort_order=1)
        PlanPrice.objects.create(plan=self.plan, currency=self.egp, amount="250.00")
        SubscriptionService.start_trial(self.user)
        self.client.force_login(self.user)

    def _checkout(self):
        return self.client.post("/api/billing/checkout/", json.dumps({"plan_id": self.plan.id, "currency_code": "EGP"}), content_type="application/json")

    def _fake_complete(self, invoice_id):
        return self.client.post("/api/billing/checkout/fake-complete/", json.dumps({"invoice_id": invoice_id}), content_type="application/json")

    @override_settings(BILLING_TEST_MODE=False)
    def test_production_without_gateway_refuses_checkout_and_creates_no_invoice(self):
        with patch(_ANY, return_value=False):
            res = self._checkout()
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["error"], NO_GATEWAY_MESSAGE)
        self.assertFalse(Invoice.objects.filter(owner=self.user).exists())

    @override_settings(BILLING_TEST_MODE=False)
    def test_production_without_gateway_refuses_fake_complete_even_for_existing_invoice(self):
        inv = Invoice.objects.create(owner=self.user, subscription=self.user.subscription, plan=self.plan, amount=250, currency=self.egp, status="pending")
        with patch(_ANY, return_value=False):
            res = self._fake_complete(inv.id)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Invoice.objects.get(pk=inv.pk).status, "pending")
        self.user.subscription.refresh_from_db()
        self.assertNotEqual(self.user.subscription.status, "active")

    @override_settings(BILLING_TEST_MODE=True)
    def test_test_mode_on_without_gateway_keeps_the_fake_flow(self):
        with patch(_ANY, return_value=False):
            res = self._checkout()
            self.assertEqual(res.status_code, 201)
            self.assertEqual(res.json()["mode"], "fake")
            self.assertEqual(self._fake_complete(res.json()["invoice_id"]).status_code, 200)
        self.user.subscription.refresh_from_db()
        self.assertEqual(self.user.subscription.status, "active")

    @override_settings(BILLING_TEST_MODE=True)
    def test_test_mode_never_overrides_a_configured_gateway(self):
        inv = Invoice.objects.create(owner=self.user, subscription=self.user.subscription, plan=self.plan, amount=250, currency=self.egp, status="pending")
        with patch(_ANY, return_value=True):
            self.assertEqual(self._fake_complete(inv.id).status_code, 400)
        self.assertEqual(Invoice.objects.get(pk=inv.pk).status, "pending")
