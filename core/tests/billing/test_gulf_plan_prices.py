from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Currency, ExchangeRate, Plan, PlanPrice
from core.services.billing import SubscriptionService

User = get_user_model()


class GulfPlanPriceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="gulf_billing", password="pw-12345-x")
        self.client.force_login(self.user)
        egp = Currency.objects.create(code="EGP", name="Egyptian Pound")
        usd = Currency.objects.create(code="USD", name="US Dollar")
        self.plan = Plan.objects.create(code="gulf_pro", name="Pro", sort_order=1)
        PlanPrice.objects.create(plan=self.plan, currency=egp, amount="250.00")
        PlanPrice.objects.create(plan=self.plan, currency=usd, amount="9.00")
        for code, value in (("USD", "52.3"), ("SAR", "13.94")):
            ExchangeRate.objects.create(
                currency_code=code, currency_name=code, buy_rate=Decimal(value),
                sell_rate=Decimal(value), mid_rate=Decimal(value),
            )

    def _codes(self, plans_payload):
        plan = next(p for p in plans_payload["plans"] if p["code"] == "gulf_pro")
        return {p["currency_code"] for p in plan["prices"]}

    def test_egyptian_user_sees_every_price(self):
        data = self.client.get("/api/billing/plans/").json()
        self.assertEqual(self._codes(data), {"EGP", "USD"})

    def test_gulf_user_is_not_offered_egp_prices(self):
        self.client.post("/api/base-currency/", data={"code": "SAR"}, content_type="application/json")
        data = self.client.get("/api/billing/plans/").json()
        self.assertEqual(self._codes(data), {"USD"})

    def test_gulf_user_status_hides_egp_prices_too(self):
        SubscriptionService.start_trial(self.user)
        self.client.post("/api/base-currency/", data={"code": "SAR"}, content_type="application/json")
        data = self.client.get("/api/billing/status/").json()
        prices = data["subscription"].get("plan", {}).get("prices", [])
        self.assertNotIn("EGP", {p["currency_code"] for p in prices})

    def test_gulf_user_who_kept_egp_still_sees_it(self):
        egp = Currency.objects.get(owner=self.user, code="EGP")
        from core.models import BalanceEntry
        BalanceEntry.objects.create(owner=self.user, title="Cairo", currency=egp, amount=1)
        self.client.post("/api/base-currency/", data={"code": "SAR"}, content_type="application/json")
        data = self.client.get("/api/billing/plans/").json()
        self.assertIn("EGP", self._codes(data))
