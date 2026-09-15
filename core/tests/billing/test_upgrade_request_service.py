from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Currency, Plan
from core.services.billing import UpgradeRequestService

User = get_user_model()


class UpgradeRequestServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="upgrade_testuser", password="pass12345")
        self.basic = Plan.objects.create(code="test_basic", name="Test Basic", sort_order=0)
        self.pro = Plan.objects.create(code="test_pro", name="Test Pro", sort_order=1)
        self.egp = Currency.objects.create(code="EGP", name="Egyptian Pound")

    def test_submit_creates_pending_request(self):
        req = UpgradeRequestService.submit(self.user, self.pro, self.egp)
        self.assertEqual(req.owner, self.user)
        self.assertEqual(req.plan, self.pro)
        self.assertEqual(req.status, "pending")

    def test_submit_is_idempotent_updates_existing_pending(self):
        first = UpgradeRequestService.submit(self.user, self.basic, self.egp)
        second = UpgradeRequestService.submit(self.user, self.pro, self.egp)

        self.assertEqual(first.id, second.id)
        self.assertEqual(second.plan, self.pro)
        self.assertEqual(self.user.upgrade_requests.count(), 1)

    def test_get_pending_returns_none_when_no_request(self):
        self.assertIsNone(UpgradeRequestService.get_pending(self.user))

    def test_get_pending_ignores_non_pending_requests(self):
        req = UpgradeRequestService.submit(self.user, self.pro, self.egp)
        req.status = "completed"
        req.save(update_fields=["status"])

        self.assertIsNone(UpgradeRequestService.get_pending(self.user))
