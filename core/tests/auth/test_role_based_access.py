from django.contrib.auth import get_user_model
from django.test import TestCase

from core.authentication.services import AuthWorkflowService
from core.authentication.utils.auth_utils import (
    user_is_sysadmin,
    effective_permission_keys,
)
from core.constants.roles import SYSADMIN_ONLY_SETTINGS_TABS
from core.models.permissions import PagePermission, Role, RolePermission, UserRole

User = get_user_model()


class RoleBasedAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="pw12345")

    def _make_sysadmin(self, user):
        profile = AuthWorkflowService.get_profile(user)
        profile.is_sysadmin = True
        profile.save(update_fields=["is_sysadmin"])

    def test_plain_user_has_no_keys_by_default(self):
        self.assertFalse(user_is_sysadmin(self.user))
        self.assertEqual(effective_permission_keys(self.user), set())

    def test_sysadmin_gets_every_grantable_key_without_role_or_override(self):
        self._make_sysadmin(self.user)
        self.assertTrue(user_is_sysadmin(self.user))
        keys = effective_permission_keys(self.user)
        self.assertIn("dashboard", keys)
        # Sysadmin-locked tabs are never part of the grantable key set at
        # all — sysadmin access to them is checked directly via
        # user_is_sysadmin(), not via this key set (see the locked-view
        # test below).
        self.assertNotIn("settings_users", keys)
        self.assertNotIn("settings_billing", keys)
        self.assertNotIn("settings_roles", keys)
        self.assertNotIn("settings_aiadvisor", keys)

    def test_role_grants_are_unioned_across_multiple_roles(self):
        role_a = Role.objects.create(name="Finance")
        RolePermission.objects.create(role=role_a, key="balance")
        role_b = Role.objects.create(name="Reports")
        RolePermission.objects.create(role=role_b, key="reports")
        UserRole.objects.create(user=self.user, role=role_a)
        UserRole.objects.create(user=self.user, role=role_b)

        keys = effective_permission_keys(self.user)
        self.assertEqual(keys, {"balance", "reports"})

    def test_per_user_override_grants_beyond_role(self):
        role = Role.objects.create(name="Basic")
        RolePermission.objects.create(role=role, key="dashboard")
        UserRole.objects.create(user=self.user, role=role)
        PagePermission.objects.create(user=self.user, page="reports", granted=True)

        keys = effective_permission_keys(self.user)
        self.assertEqual(keys, {"dashboard", "reports"})

    def test_per_user_override_revokes_what_role_grants(self):
        role = Role.objects.create(name="Basic")
        RolePermission.objects.create(role=role, key="dashboard")
        RolePermission.objects.create(role=role, key="reports")
        UserRole.objects.create(user=self.user, role=role)
        PagePermission.objects.create(user=self.user, page="reports", granted=False)

        keys = effective_permission_keys(self.user)
        self.assertEqual(keys, {"dashboard"})

    def test_sysadmin_only_tabs_are_never_in_grantable_choices(self):
        from core.constants.roles import grantable_permission_keys

        grantable = set(grantable_permission_keys())
        for locked_key in SYSADMIN_ONLY_SETTINGS_TABS:
            self.assertNotIn(locked_key, grantable)

    def test_sysadmin_locked_view_rejects_role_grant_but_allows_sysadmin(self):
        Role.objects.create(name="AllSettings")
        # Even if somehow granted via override, the view for a locked tab
        # must only trust is_sysadmin, not effective_permission_keys().
        PagePermission.objects.create(user=self.user, page="settings_users", granted=True)
        self.client.force_login(self.user)
        res = self.client.get("/api/users/")
        self.assertEqual(res.status_code, 403)

        self._make_sysadmin(self.user)
        res = self.client.get("/api/users/")
        self.assertEqual(res.status_code, 200)

    def test_ai_advisor_tab_rejects_role_grant_but_allows_sysadmin(self):
        # AI Advisor is app-wide config, sysadmin-only — not delegable via
        # a role, even one that (invalidly) claims the key.
        Role.objects.create(name="AIOps")
        PagePermission.objects.create(user=self.user, page="settings_aiadvisor", granted=True)
        self.client.force_login(self.user)
        res = self.client.get("/api/settings/ai/")
        self.assertEqual(res.status_code, 403)

        self._make_sysadmin(self.user)
        res = self.client.get("/api/settings/ai/")
        self.assertEqual(res.status_code, 200)

    def test_every_sidebar_page_and_settings_tab_is_grantable(self):
        """Every main-app page and settings tab must be assignable via a
        Role or per-user override, so an end-user can be given access to
        any single one of them without becoming sysadmin. Regression test
        for the WealthFlow AI page, which was previously missing here."""
        from core.constants.roles import grantable_permission_keys

        grantable = set(grantable_permission_keys())
        main_app_pages = {
            "dashboard",
            "wealthflow_ai",
            "financial_advisor",
            "employment",
            "balance",
            "bank_certificates",
            "fixed_assets",
            "exchange_rates",
            "gold_price",
            "expenses",
            "expense-categories",
            "reports",
            "advanced_reports",
        }
        for key in main_app_pages:
            self.assertIn(key, grantable, f"{key} is missing from the grantable keys")
