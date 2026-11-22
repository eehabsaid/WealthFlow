"""Legal consent and snapshot caching tests."""




from core.authentication.legal import LEGAL_VERSION
from core.authentication.services import AuthWorkflowService
from core.models import LegalVersion
from core.services.legal import clear_cache, current_label, needs_reconsent
from .legal_text_support import LegalTextBase


class LegalConsentTests(LegalTextBase):
    def test_signup_records_current_label(self):
        self.publish("2026-11-v1")
        from core.services.legal import accept_current

        profile = AuthWorkflowService.get_profile(self.member)
        accept_current(profile)
        profile.refresh_from_db()
        self.assertEqual(profile.terms_version, "2026-11-v1")
        self.assertIsNotNone(profile.terms_accepted_at)

    def test_existing_accounts_keep_accepted_version(self):
        profile = AuthWorkflowService.get_profile(self.member)
        profile.terms_version = LEGAL_VERSION
        profile.save(update_fields=["terms_version"])
        self.publish("v2", reconsent=False)
        profile.refresh_from_db()
        self.assertEqual(profile.terms_version, LEGAL_VERSION)
        self.assertFalse(needs_reconsent(profile))

    def test_reconsent_flow(self):
        profile = AuthWorkflowService.get_profile(self.member)
        profile.terms_version = LEGAL_VERSION
        profile.save(update_fields=["terms_version"])
        self.publish("v3", reconsent=True)
        self.client.force_login(self.member)
        status = self.client.get("/api/legal/consent/").json()
        self.assertTrue(status["required"])
        self.assertEqual(status["version"], "v3")
        self.assertEqual(status["accepted_version"], LEGAL_VERSION)
        self.assertEqual(self.client.post("/api/legal/consent/").json()["accepted_version"], "v3")
        self.assertFalse(self.client.get("/api/legal/consent/").json()["required"])
        profile.refresh_from_db()
        self.assertEqual(profile.terms_version, "v3")

    def test_publisher_is_not_prompted_for_their_own_version(self):
        self.publish("v5", reconsent=True)
        admin_profile = AuthWorkflowService.get_profile(self.admin)
        admin_profile.refresh_from_db()
        self.assertEqual(admin_profile.terms_version, "v5")
        self.assertFalse(needs_reconsent(admin_profile))
        # other accounts are still asked once a re-consent version exists
        self.assertTrue(needs_reconsent(AuthWorkflowService.get_profile(self.member)))

    def test_later_version_without_flag_does_not_prompt(self):
        profile = AuthWorkflowService.get_profile(self.member)
        profile.terms_version = "v3"
        profile.save(update_fields=["terms_version"])
        self.publish("v3", reconsent=True)
        self.publish("v4", reconsent=False)
        profile.refresh_from_db()
        self.assertFalse(needs_reconsent(profile))

    def test_consent_requires_login(self):
        self.client.logout()
        self.assertIn(self.client.get("/api/legal/consent/").status_code, (401, 403, 302))


class LegalSnapshotIsNeverCachedTests(LegalTextBase):
    """A process-level copy of the current version leaked between tests (and
    live-server threads); the version must be read from the DB on each call."""

    def test_direct_db_changes_are_visible_without_clear_cache(self):
        self.assertEqual(current_label(), LEGAL_VERSION)
        LegalVersion.objects.create(label="v-direct", content={}, require_reconsent=True, created_by=self.admin)
        self.assertEqual(current_label(), "v-direct")
        self.assertTrue(needs_reconsent(AuthWorkflowService.get_profile(self.member)))
        LegalVersion.objects.all().delete()
        self.assertEqual(current_label(), LEGAL_VERSION)
        self.assertFalse(needs_reconsent(AuthWorkflowService.get_profile(self.member)))

    def test_clear_cache_is_a_harmless_noop(self):
        clear_cache()
        clear_cache()
        self.assertEqual(current_label(), LEGAL_VERSION)
