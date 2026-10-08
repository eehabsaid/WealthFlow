"""Sysadmin-created users get a trial when the Settings > Billing option is on (default ON, no backfill)."""

import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.authentication.services import AuthWorkflowService
from core.models import Plan, Subscription

User = get_user_model()


class TrialOnAdminCreateTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="tr_admin", password="pass12345", email="a@a.com")
        profile = AuthWorkflowService.get_profile(self.admin)
        profile.is_sysadmin = True
        profile.save(update_fields=["is_sysadmin"])
        Plan.objects.get_or_create(code="basic", defaults={"name": "Basic", "sort_order": 1})
        self.client.force_login(self.admin)

    def _create(self, username, **extra):
        body = {"username": username, "email": f"{username}@x.com", "password": "pass12345", **extra}
        return self.client.post("/api/users/", data=json.dumps(body), content_type="application/json")

    def _toggle(self, value):
        return self.client.put("/api/settings/billing/trial-options/", data=json.dumps({"trial_on_admin_created_users": value}), content_type="application/json")

    def test_default_is_on_and_new_user_gets_trial(self):
        self.assertTrue(self.client.get("/api/settings/billing/trial-options/").json()["trial_on_admin_created_users"])
        self.assertEqual(self._create("tr_new").status_code, 201)
        sub = Subscription.objects.get(owner__username="tr_new")
        self.assertEqual(sub.status, "trialing")
        self.assertTrue(sub.has_access())

    def test_off_creates_no_subscription(self):
        self.assertEqual(self._toggle(False).status_code, 200)
        self._create("tr_off")
        self.assertFalse(Subscription.objects.filter(owner__username="tr_off").exists())
        self.assertFalse(self.client.get("/api/settings/billing/trial-options/").json()["trial_on_admin_created_users"])

    def test_toggle_back_on(self):
        self._toggle(False)
        self._toggle(True)
        self._create("tr_on")
        self.assertTrue(Subscription.objects.filter(owner__username="tr_on").exists())

    def test_existing_users_untouched_by_the_setting(self):
        old = User.objects.create_user(username="tr_old", password="pass12345")
        self._toggle(True)
        self.assertFalse(Subscription.objects.filter(owner=old).exists())

    def test_sysadmin_and_superuser_accounts_are_not_trialed(self):
        self._create("tr_sys", is_sysadmin=True)
        self._create("tr_root", is_superuser=True)
        self.assertFalse(Subscription.objects.filter(owner__username__in=["tr_sys", "tr_root"]).exists())

    def test_no_plan_catalog_does_not_break_user_creation(self):
        Plan.objects.all().delete()
        self.assertEqual(self._create("tr_noplan").status_code, 201)
        self.assertFalse(Subscription.objects.filter(owner__username="tr_noplan").exists())

    def test_option_validation_and_permissions(self):
        self.assertEqual(self.client.put("/api/settings/billing/trial-options/", data=json.dumps({"trial_on_admin_created_users": "yes"}), content_type="application/json").status_code, 400)
        plain = User.objects.create_user(username="tr_plain", password="pass12345")
        self.client.force_login(plain)
        self.assertIn(self.client.get("/api/settings/billing/trial-options/").status_code, (401, 403))
        self.assertIn(self._toggle(False).status_code, (401, 403))
