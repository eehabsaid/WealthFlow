"""
Direct service-level checkout tests (CheckoutServiceUnitTestCase group).

Split out of the former monolithic test_checkout_flow.py (200-line rule).
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Currency, Plan, PlanPrice
from core.services.billing import CheckoutError, CheckoutService

User = get_user_model()


class CheckoutServiceUnitTestCase(TestCase):
    """Direct service-level tests for logic not easily reached via the
    fake-mode HTTP endpoints above."""

    def setUp(self):
        self.user = User.objects.create_user(username="svc_user", password="pass12345")
        self.egp = Currency.objects.create(code="EGP", name="Egyptian Pound")
        self.plan = Plan.objects.create(code="svc_plan", name="Service Plan", sort_order=1)
        PlanPrice.objects.create(plan=self.plan, currency=self.egp, amount="99.00")

    def test_initiate_checkout_without_subscription_raises(self):
        with self.assertRaises(CheckoutError):
            CheckoutService.initiate_checkout(self.user, self.plan, self.egp)
