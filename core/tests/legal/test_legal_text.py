"""Editable Privacy/Terms text: DB versions, i18n fallback, cache, gating, re-consent."""


import json


from core.authentication.legal import LEGAL_VERSION
from core.constants.roles import (
    SYSADMIN_ONLY_SETTINGS_TABS,
    grantable_permission_keys,
)
from core.models import LegalVersion
from core.services.legal import current_label, get_document
from .legal_text_support import LegalTextBase, _sections


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
