"""Shared base for the sysadmin customer-admin tests."""

import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from core.authentication.services import AuthWorkflowService
from core.models import Currency, Invoice, Plan, Subscription

User = get_user_model()


class CustomerAdminBase(TestCase):
    """Shared fixtures/helpers for the customer-admin test modules (no tests here)."""

    def setUp(self):
        self.admin = User.objects.create_superuser(username="ca_admin", password="pass12345", email="a@a.com")
        profile = AuthWorkflowService.get_profile(self.admin)
        profile.is_sysadmin = True
        profile.save(update_fields=["is_sysadmin"])
        self.basic, _ = Plan.objects.get_or_create(code="basic", defaults={"name": "Basic", "sort_order": 1})
        self.pro, _ = Plan.objects.get_or_create(code="pro", defaults={"name": "Pro", "sort_order": 2})
        self.user = User.objects.create_user(username="ca_user", password="pass12345", email="u@u.com")
        self.now = timezone.now()
        self.sub = Subscription.objects.create(
            owner=self.user, plan=self.basic, status="trialing", trial_end=self.now + timedelta(days=3)
        )
        self.currency = Currency.objects.filter(owner=self.user).first() or Currency.objects.create(
            owner=self.user, code="USD", name="US Dollar", symbol="$"
        )
        self.client.force_login(self.admin)

    def _invoice(self, status="pending", gateway_reference=""):
        return Invoice.objects.create(
            owner=self.user, subscription=self.sub, plan=self.pro, amount=Decimal("100.00"), currency=self.currency,
            status=status, gateway_reference=gateway_reference, period_start=self.now,
            period_end=self.now + timedelta(days=30),
        )

    def _act(self, url, **body):
        return self.client.post(url, data=json.dumps(body), content_type="application/json")

    def _customer(self, **body):
        return self._act(f"/api/settings/billing/customers/{self.user.id}/action/", **body)

    def _invoice_act(self, invoice, **body):
        return self._act(f"/api/settings/billing/invoices/{invoice.id}/action/", **body)
