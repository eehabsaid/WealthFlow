from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import AssetInsurance, Currency, FixedAsset
from core.services.financial_advisor.overview_service import OverviewService

User = get_user_model()
TODAY = date(2026, 9, 21)


def _keys(payload):
    return [a["title_key"] for a in payload["alerts"]]


class OverviewEmptyStatesTest(TestCase):
    """Brand-new users must get honest empty states, not fake reassurance."""

    def setUp(self):
        Currency.objects.get_or_create(code="EGP", defaults={"symbol": "£", "name": "Egyptian Pound"})
        self.user = User.objects.create_user(username="adv_new", password="pass12345")

    def _payload(self):
        return OverviewService(self.user, today=TODAY).payload()

    def _policy(self, expiry):
        asset = FixedAsset.objects.create(
            owner=self.user, name="Car", asset_type="Vehicle", purchase_date=TODAY,
        )
        return AssetInsurance.objects.create(asset=asset, company="Acme", expiry_date=expiry)

    def test_no_policies_is_neutral_not_up_to_date(self):
        keys = _keys(self._payload())
        self.assertIn("overview_alert_insurance_none_title", keys)
        self.assertNotIn("overview_alert_insurance_up_to_date_title", keys)

    def test_active_policy_is_up_to_date(self):
        self._policy(TODAY + timedelta(days=200))
        keys = _keys(self._payload())
        self.assertIn("overview_alert_insurance_up_to_date_title", keys)

    def test_expired_policy_warns(self):
        self._policy(TODAY - timedelta(days=1))
        payload = self._payload()
        alert = next(a for a in payload["alerts"] if a["title_key"] == "overview_alert_insurance_expired_title")
        self.assertEqual(alert["params"]["count"], 1)
        self.assertEqual(alert["severity"], "warning")

    def test_other_users_policy_is_not_counted(self):
        other = User.objects.create_user(username="adv_other", password="pass12345")
        asset = FixedAsset.objects.create(owner=other, name="Car", asset_type="Vehicle", purchase_date=TODAY)
        AssetInsurance.objects.create(asset=asset, company="Acme", expiry_date=TODAY + timedelta(days=90))
        self.assertIn("overview_alert_insurance_none_title", _keys(self._payload()))

    def test_no_history_hides_net_worth_growth(self):
        self.assertIsNone(self._payload()["kpis"]["net_worth_growth_yoy"])
