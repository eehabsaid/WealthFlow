"""Editable Privacy/Terms text: DB versions, i18n fallback, cache, gating, re-consent."""

import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.authentication.legal import LEGAL_VERSION
from core.authentication.services import AuthWorkflowService
from core.constants.roles import (
    SYSADMIN_ONLY_SETTINGS_TABS,
    grantable_permission_keys,
)
from core.models import LegalVersion
from core.services.legal import clear_cache, current_label, get_document, needs_reconsent

User = get_user_model()


def _sections(*pairs):
    return [{"title": t, "body": b} for t, b in pairs]


class LegalTextBase(TestCase):
    def setUp(self):
        clear_cache()
        self.admin = User.objects.create_user(username="boss", password="pw12345")
        p = AuthWorkflowService.get_profile(self.admin)
        p.is_sysadmin = True
        p.save(update_fields=["is_sysadmin"])
        self.member = User.objects.create_user(username="mem", password="pw12345")
        AuthWorkflowService.get_profile(self.member)

    def tearDown(self):
        clear_cache()

    def publish(self, label="v1", reconsent=False, content=None, client=None):
        client = client or self.client
        client.force_login(self.admin)
        content = content or {"en": {"terms": {"title": "My Terms", "sections": _sections(("A", "Body A\nline2"))}}}
        return client.post(
            "/api/settings/legal/",
            data=json.dumps({"label": label, "content": content, "require_reconsent": reconsent}),
            content_type="application/json",
        )


class LegalFallbackAndRenderTests(LegalTextBase):
    def test_empty_table_uses_i18n_defaults(self):
        self.assertEqual(current_label(), LEGAL_VERSION)
        doc = get_document("en", "terms")
        self.assertFalse(doc["overridden"])
        self.assertEqual(len(doc["sections"]), 9)
        self.assertEqual(len(get_document("ar", "privacy")["sections"]), 8)

    def test_published_text_is_served_and_cache_cleared_on_save(self):
        self.assertContains(self.client.get("/terms/"), "data-i18n")  # warms the cache
        self.assertEqual(self.publish().status_code, 201)
        page = self.client.get("/terms/")
        self.assertContains(page, "My Terms")
        self.assertContains(page, "Body A<br>line2")
        self.assertContains(page, "v1")
        self.assertNotContains(page, 'data-i18n="terms_s1_title"')

    def test_other_languages_and_docs_fall_back_to_defaults(self):
        self.publish()
        self.assertFalse(get_document("fr", "terms")["overridden"])
        self.assertFalse(get_document("en", "privacy")["overridden"])
        self.client.cookies["wf_lang"] = "fr"
        self.assertContains(self.client.get("/terms/"), 'data-i18n="terms_s1_title"')

    def test_unchanged_text_is_not_stored_as_override(self):
        from core.services.legal.content import default_document

        d = default_document("en", "terms")
        self.publish(content={"en": {"terms": d}})
        self.assertEqual(LegalVersion.objects.get().content, {})

    def test_html_is_escaped(self):
        self.publish(content={"en": {"terms": {"title": "<script>x</script>", "sections": _sections(("<b>", "<i>"))}}})
        page = self.client.get("/terms/").content.decode()
        self.assertNotIn("<script>x</script>", page)
        self.assertIn("&lt;script&gt;x&lt;/script&gt;", page)


class LegalEditorApiTests(LegalTextBase):
    def test_sysadmin_only_gate(self):
        self.assertIn("settings_legal", SYSADMIN_ONLY_SETTINGS_TABS)
        self.assertNotIn("settings_legal", grantable_permission_keys())
        self.client.force_login(self.member)
        self.assertEqual(self.client.get("/api/settings/legal/").status_code, 403)
        self.client.force_login(self.member)
        res = self.client.post(
            "/api/settings/legal/",
            data=json.dumps({"label": "x", "content": {}}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 403)
        self.assertEqual(self.client.get("/api/settings/legal/1/").status_code, 403)

    def test_anonymous_rejected(self):
        self.client.logout()
        self.assertIn(self.client.get("/api/settings/legal/").status_code, (401, 403, 302))

    def test_validation(self):
        self.client.force_login(self.admin)
        post = lambda body: self.client.post("/api/settings/legal/", data=json.dumps(body), content_type="application/json")
        self.assertEqual(post({"label": "bad label!", "content": {}}).status_code, 400)
        self.assertEqual(post({"label": "", "content": {}}).status_code, 400)
        self.assertEqual(post({"label": "ok", "content": "nope"}).status_code, 400)
        long_body = {"en": {"terms": {"title": "t", "sections": _sections(("a", "x" * 8001))}}}
        self.assertEqual(post({"label": "ok", "content": long_body}).json()["error"], "too_long")
        self.assertEqual(self.publish("dup").status_code, 201)
        self.assertEqual(self.publish("dup").status_code, 409)

    def test_history_and_detail(self):
        self.publish("v1")
        self.publish("v2")
        data = self.client.get("/api/settings/legal/").json()
        self.assertEqual([v["label"] for v in data["versions"]], ["v2", "v1"])
        self.assertEqual(data["current_label"], "v2")
        self.assertEqual(len(data["defaults"]["en"]["terms"]["sections"]), 9)
        first = LegalVersion.objects.get(label="v1")
        detail = self.client.get(f"/api/settings/legal/{first.pk}/").json()["version"]
        self.assertEqual(detail["content"]["en"]["terms"]["title"], "My Terms")


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
