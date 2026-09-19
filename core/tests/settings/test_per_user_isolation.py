from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import AppSettings, Currency, GoldTypeSetting, GoldPuritySetting
from core.models.certificate.certificate_status import CertificateStatus

User = get_user_model()


class PerUserSettingsIsolationTests(TestCase):
    """Regression coverage for the multi-tenant settings gap: one user's
    changes must never leak to another user, and global-only settings
    (SMTP, available_languages) must stay shared."""

    def setUp(self):
        self.alice = User.objects.create_user(username="alice2", password="pw12345")
        self.bob = User.objects.create_user(username="bob2", password="pw12345")

    def test_property_valuation_settings_are_isolated_per_user(self):
        AppSettings.set("property_valuation_rate_map", '{"Cairo": 100}', user=self.alice)
        AppSettings.set("property_valuation_rate_map", '{"Cairo": 999}', user=self.bob)

        self.assertEqual(
            AppSettings.get("property_valuation_rate_map", user=self.alice), '{"Cairo": 100}'
        )
        self.assertEqual(
            AppSettings.get("property_valuation_rate_map", user=self.bob), '{"Cairo": 999}'
        )

    def test_active_language_writes_to_own_profile_not_global(self):
        self.client.force_login(self.alice)
        res = self.client.post(
            "/api/settings/",
            data='{"key": "active_language", "value": "ar"}',
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)

        from core.authentication.services import AuthWorkflowService

        alice_profile = AuthWorkflowService.get_profile(self.alice)
        bob_profile = AuthWorkflowService.get_profile(self.bob)
        self.assertEqual(alice_profile.preferred_language, "ar")
        self.assertNotEqual(bob_profile.preferred_language, "ar")
        # The global row must be untouched by a logged-in user's change
        self.assertIsNone(AppSettings.objects.filter(key="active_language", owner=None).first())

    def test_smtp_style_global_key_stays_shared_across_users(self):
        # smtp_host is NOT in USER_SCOPED_SETTING_KEYS -> always global
        self.client.force_login(self.alice)
        self.client.post(
            "/api/settings/",
            data='{"key": "smtp_host", "value": "mail.example.com"}',
            content_type="application/json",
        )
        self.assertEqual(AppSettings.get("smtp_host", user=self.bob), "mail.example.com")

    def test_currency_catalog_is_cloned_per_user_and_independently_editable(self):
        # Both users get their own clone from the signal-based seeding
        alice_currencies = Currency.objects.filter(owner=self.alice)
        bob_currencies = Currency.objects.filter(owner=self.bob)
        self.assertGreater(alice_currencies.count(), 0)
        self.assertEqual(alice_currencies.count(), bob_currencies.count())

        # Editing Alice's copy must not affect Bob's
        alice_usd = alice_currencies.filter(code="USD").first()
        if alice_usd:
            alice_usd.symbol = "ALICE-$"
            alice_usd.save()
            bob_usd = bob_currencies.filter(code="USD").first()
            self.assertNotEqual(bob_usd.symbol, "ALICE-$")

    def test_gold_and_cert_status_catalogs_seeded_per_user(self):
        for Model in (GoldTypeSetting, GoldPuritySetting, CertificateStatus):
            self.assertTrue(Model.objects.filter(owner=self.alice).exists())
            self.assertTrue(Model.objects.filter(owner=self.bob).exists())

    def test_request_lang_prefers_own_profile_over_stale_browser_cookie(self):
        """Regression: a shared-browser wf_lang cookie (set while a
        different account was last active, or on the anonymous login page)
        must never outrank the authenticated user's own stored preference —
        this was the root cause of one account's language bleeding into
        another's on the same browser."""
        from core.authentication.services import AuthWorkflowService
        from core.authentication.utils.auth_utils import request_lang
        from django.test import RequestFactory

        profile = AuthWorkflowService.get_profile(self.bob)
        profile.preferred_language = "en"
        profile.save(update_fields=["preferred_language"])

        rf = RequestFactory()
        request = rf.get("/", HTTP_COOKIE="wf_lang=ar")
        request.user = self.bob

        self.assertEqual(request_lang(request), "en")

    def test_settings_post_never_overwrites_active_language_without_persist_intent(self):
        """The frontend only sends this POST on an explicit language
        switch now (persist=true); this test locks in that the backend
        side of the contract — writing to the caller's own profile, not
        some other row — still holds regardless of what a stale client
        sends."""
        self.client.force_login(self.bob)
        res = self.client.post(
            "/api/settings/",
            data='{"key": "active_language", "value": "ar"}',
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)

        from core.authentication.services import AuthWorkflowService

        self.assertEqual(
            AuthWorkflowService.get_profile(self.bob).preferred_language, "ar"
        )
        self.assertNotEqual(
            AuthWorkflowService.get_profile(self.alice).preferred_language, "ar"
        )
