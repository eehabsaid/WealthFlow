"""Paymob: regional (Gulf) accounts, webhook amount/currency checks, pending/refund callbacks."""
import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from core.models import AppSettings, Currency, Invoice, Plan, PlanPrice
from core.services.ai.credential_encryption import encrypt_credential
from core.services.billing import CheckoutError, CheckoutService, PaymobGateway
from core.services.billing.checkout_service import amount_to_cents
from core.services.billing.paymob_gateway import _HMAC_FIELDS, normalize_base_url, region_key
from core.services.billing.subscription_service import SubscriptionService

User = get_user_model()


def _set_default():
    AppSettings.set("paymob_api_key", encrypt_credential("egy-key"))
    AppSettings.set("paymob_hmac_secret", encrypt_credential("egy-hmac"))
    AppSettings.set("paymob_integration_id", "111")
    AppSettings.set("paymob_iframe_id", "222")


def _set_region(code, host="ksa.paymob.com", hmac_secret="ksa-hmac"):
    AppSettings.set(region_key(code, "api_key"), encrypt_credential("ksa-key"))
    AppSettings.set(region_key(code, "hmac_secret"), encrypt_credential(hmac_secret))
    AppSettings.set(region_key(code, "integration_id"), "333")
    AppSettings.set(region_key(code, "iframe_id"), "444")
    AppSettings.set(region_key(code, "base_url"), host)


class _Base(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="pm_user", password="pass12345")
        self.egp = Currency.objects.create(code="EGP", name="Egyptian Pound")
        self.sar = Currency.objects.create(code="SAR", name="Saudi Riyal")
        self.plan = Plan.objects.create(code="pm_pro", name="Pro", sort_order=1)
        PlanPrice.objects.create(plan=self.plan, currency=self.egp, amount="250.00")
        PlanPrice.objects.create(plan=self.plan, currency=self.sar, amount="19.99")
        SubscriptionService.start_trial(self.user)


class RegionalConfigTests(_Base):
    def test_normalize_base_url(self):
        self.assertEqual(normalize_base_url(""), "https://accept.paymob.com/api")
        self.assertEqual(normalize_base_url("ksa.paymob.com"), "https://ksa.paymob.com/api")
        self.assertEqual(normalize_base_url("http://uae.paymob.com/"), "https://uae.paymob.com/api")
        self.assertEqual(normalize_base_url("https://ksa.paymob.com/api"), "https://ksa.paymob.com/api")

    def test_default_account_serves_only_its_currencies(self):
        _set_default()
        self.assertTrue(PaymobGateway.is_configured("EGP"))
        self.assertFalse(PaymobGateway.is_configured("SAR"))

    def test_regional_account_serves_its_currency_with_its_own_host(self):
        _set_default()
        _set_region("SAR")
        cfg = PaymobGateway.get_config("SAR")
        self.assertEqual(cfg["base_url"], "https://ksa.paymob.com/api")
        self.assertEqual(cfg["integration_id"], "333")
        self.assertTrue(PaymobGateway.is_configured("SAR"))
        self.assertEqual(PaymobGateway.get_config("EGP")["integration_id"], "111")

    def test_gulf_checkout_refused_not_sent_to_egypt_account(self):
        _set_default()
        with patch("core.services.billing.paymob_gateway.PaymobGateway.create_checkout") as create:
            with self.assertRaises(CheckoutError):
                CheckoutService.initiate_checkout(self.user, self.plan, self.sar)
            create.assert_not_called()
        self.assertEqual(Invoice.objects.count(), 0)

    def test_gulf_checkout_uses_regional_account_and_country(self):
        _set_default()
        _set_region("SAR")
        with patch(
            "core.services.billing.paymob_gateway.PaymobGateway.create_checkout",
            return_value={"order_id": 9, "iframe_url": "https://ksa.paymob.com/x"},
        ) as create:
            result = CheckoutService.initiate_checkout(self.user, self.plan, self.sar)
        self.assertEqual(result["mode"], "paymob")
        kwargs = create.call_args.kwargs
        self.assertEqual(kwargs["currency_code"], "SAR")
        self.assertEqual(kwargs["amount_cents"], 1999)
        self.assertEqual(kwargs["billing_data"]["country"], "SA")

    def test_regional_only_setup_disables_fake_mode(self):
        _set_region("SAR")
        self.assertTrue(PaymobGateway.any_configured())
        with self.assertRaises(CheckoutError):
            CheckoutService.initiate_checkout(self.user, self.plan, self.egp)

    @override_settings(BILLING_TEST_MODE=True)
    def test_unconfigured_everywhere_stays_fake_mode(self):
        self.assertFalse(PaymobGateway.any_configured())
        self.assertEqual(CheckoutService.initiate_checkout(self.user, self.plan, self.sar)["mode"], "fake")

    def test_amount_to_cents_rounds_not_truncates(self):
        self.assertEqual(amount_to_cents(Decimal("19.99")), 1999)
        self.assertEqual(amount_to_cents("0.29"), 29)
        self.assertEqual(amount_to_cents(Decimal("1.005")), 101)

    def test_webhook_signature_accepts_default_and_regional_secrets(self):
        _set_default()
        _set_region("SAR")
        obj = {"amount_cents": 1999, "id": 5, "success": True, "currency": "SAR", "order": {"id": 9}}
        concatenated = "".join(
            "" if (n := _dig(obj, f)) is None else (str(n).lower() if isinstance(n, bool) else str(n))
            for f in _HMAC_FIELDS
        )
        for secret, expected in (("ksa-hmac", True), ("egy-hmac", True), ("other", False)):
            sig = hmac.new(secret.encode(), concatenated.encode(), hashlib.sha512).hexdigest()
            self.assertEqual(PaymobGateway.verify_webhook_hmac({"obj": obj}, sig), expected, secret)


def _dig(obj, path):
    node = obj
    for seg in path.split("."):
        node = node.get(seg) if isinstance(node, dict) else None
    return node


@patch("core.services.billing.paymob_gateway.PaymobGateway.verify_webhook_hmac", return_value=True)
class WebhookHardeningTests(_Base):
    def setUp(self):
        super().setUp()
        self.invoice = Invoice.objects.create(
            owner=self.user, subscription=SubscriptionService.get_subscription(self.user),
            plan=self.plan, amount="19.99", currency=self.sar, status="pending",
        )

    def _post(self, **obj):
        body = {"obj": {"order": {"merchant_order_id": f"wf-inv-{self.invoice.id}"}, **obj}}
        res = self.client.post("/api/billing/paymob/webhook/?hmac=x", data=json.dumps(body), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        self.invoice.refresh_from_db()
        return self.invoice.status

    def test_exact_amount_and_currency_activates(self, _m):
        self.assertEqual(self._post(success=True, amount_cents=1999, currency="SAR"), "paid")

    def test_underpayment_is_not_activated(self, _m):
        self.assertEqual(self._post(success=True, amount_cents=100, currency="SAR"), "pending")

    def test_wrong_currency_is_not_activated(self, _m):
        self.assertEqual(self._post(success=True, amount_cents=1999, currency="EGP"), "pending")

    def test_missing_amount_is_not_activated(self, _m):
        self.assertEqual(self._post(success=True), "pending")

    def test_pending_callback_is_not_marked_failed(self, _m):
        self.assertEqual(self._post(success=False, pending=True, amount_cents=1999, currency="SAR"), "pending")

    def test_voided_or_refunded_success_is_not_activated(self, _m):
        self.assertEqual(self._post(success=True, is_refunded=True, amount_cents=1999, currency="SAR"), "pending")
        self.assertEqual(self._post(success=True, is_voided=True, amount_cents=1999, currency="SAR"), "pending")

    def test_failed_callback_still_marks_failed(self, _m):
        self.assertEqual(self._post(success=False, pending=False, amount_cents=1999, currency="SAR"), "failed")


class PaymobReturnTests(_Base):
    def test_return_redirects_to_plans_and_activates_nothing(self):
        invoice = Invoice.objects.create(
            owner=self.user, subscription=SubscriptionService.get_subscription(self.user),
            plan=self.plan, amount="250.00", currency=self.egp, status="pending",
        )
        self.client.force_login(self.user)
        res = self.client.get(f"/billing/paymob/return/?success=true&merchant_order_id=wf-inv-{invoice.id}")
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res["Location"], "/#billing-plans")
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, "pending")

    def test_return_requires_login(self):
        self.assertEqual(self.client.get("/billing/paymob/return/").status_code, 302)
        self.assertIn("login", self.client.get("/billing/paymob/return/")["Location"])
