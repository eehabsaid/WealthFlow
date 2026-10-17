"""Shared fixtures for the Stripe tests (no tests here). No real keys, no network."""

import hashlib
import hmac
import json
import time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import AppSettings, Currency, Invoice, Plan, PlanPrice
from core.services.ai.credential_encryption import encrypt_credential
from core.services.billing.subscription_service import SubscriptionService

User = get_user_model()
WEBHOOK_SECRET = "whsec_test_123"


def configure_stripe(currencies="USD,EUR"):
    AppSettings.set("stripe_secret_key", encrypt_credential("sk_test_abc"))
    AppSettings.set("stripe_webhook_secret", encrypt_credential(WEBHOOK_SECRET))
    AppSettings.set("stripe_currencies", currencies)


def sign(body: bytes, secret=WEBHOOK_SECRET, stamp=None) -> str:
    stamp = int(stamp if stamp is not None else time.time())
    mac = hmac.new(secret.encode(), f"{stamp}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={stamp},v1={mac}"


def session_event(invoice, kind="checkout.session.completed", **over):
    obj = {
        "client_reference_id": f"wf-inv-{invoice.id}", "payment_status": "paid", "payment_intent": "pi_123",
        "amount_total": int(invoice.amount * 100), "currency": invoice.currency.code.lower(),
    }
    obj.update(over)
    return {"type": kind, "data": {"object": obj}}


class StripeBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="stripe_user", password="pass12345", email="s@s.com")
        self.usd = Currency.objects.create(code="USD", name="US Dollar")
        self.plan = Plan.objects.create(code="st_pro", name="Stripe Pro", sort_order=1)
        PlanPrice.objects.create(plan=self.plan, currency=self.usd, amount="20.00")
        SubscriptionService.start_trial(self.user)
        self.sub = SubscriptionService.get_subscription(self.user)
        self.client.force_login(self.user)

    def invoice(self, status="pending", **kw):
        return Invoice.objects.create(
            owner=self.user, subscription=self.sub, plan=self.plan, amount=Decimal("20.00"),
            currency=self.usd, status=status, **kw,
        )

    def post_event(self, event, header=None):
        body = json.dumps(event).encode()
        return self.client.post(
            "/api/billing/stripe/webhook/", data=body, content_type="application/json",
            HTTP_STRIPE_SIGNATURE=header if header is not None else sign(body),
        )
