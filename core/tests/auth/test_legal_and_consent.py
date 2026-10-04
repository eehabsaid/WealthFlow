"""Privacy Policy / Terms pages and the signup consent checkbox."""
import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from core.authentication.legal import LEGAL_VERSION
from core.authentication.services import AuthWorkflowService
from core.authentication.views.legal_views import PRIVACY_SECTIONS, TERMS_SECTIONS

User = get_user_model()
I18N_DIR = Path(__file__).resolve().parents[3] / "static" / "i18n"
SIGNUP = {"username": "consent_user", "email": "consent@example.com", "password": "SecurePass123!",
          "confirm_password": "SecurePass123!", "lang": "en"}


class LegalPagesTests(TestCase):
    def test_pages_are_public_and_show_draft_notice_and_version(self):
        for path, title in (("/privacy/", "Privacy Policy"), ("/terms/", "Terms of Service")):
            res = self.client.get(path)  # anonymous: no redirect to login
            self.assertEqual(res.status_code, 200, path)
            body = res.content.decode()
            self.assertIn(title, body)
            self.assertIn("legal review needed", body)
            self.assertIn(LEGAL_VERSION, body)

    def test_all_sections_render_with_translation_keys(self):
        privacy = self.client.get("/privacy/").content.decode()
        terms = self.client.get("/terms/").content.decode()
        for i in range(1, PRIVACY_SECTIONS + 1):
            self.assertIn(f'data-i18n="privacy_s{i}_body"', privacy)
        for i in range(1, TERMS_SECTIONS + 1):
            self.assertIn(f'data-i18n="terms_s{i}_body"', terms)
        self.assertIn("Paymob", privacy)

    def test_post_not_allowed(self):
        self.assertEqual(self.client.post("/privacy/").status_code, 405)
        self.assertEqual(self.client.post("/terms/").status_code, 405)

    def test_legal_text_exists_in_every_language_with_same_keys(self):
        keys = [f"privacy_s{i}_{p}" for i in range(1, PRIVACY_SECTIONS + 1) for p in ("title", "body")]
        keys += [f"terms_s{i}_{p}" for i in range(1, TERMS_SECTIONS + 1) for p in ("title", "body")]
        keys += ["legal_draft_notice", "legal_privacy_title", "legal_terms_title", "auth_accept_prefix",
                 "auth_accept_and", "auth_error_terms_required"]
        for lang in ("en", "ar", "fr", "de"):
            data = json.loads((I18N_DIR / f"{lang}.json").read_text(encoding="utf-8"))
            for key in keys:
                self.assertTrue(str(data.get(key, "")).strip(), f"{lang}:{key}")

    def test_login_and_signup_pages_link_to_legal_pages(self):
        for path in ("/accounts/login/", "/accounts/signup/"):
            body = self.client.get(path).content.decode()
            self.assertIn('class="auth-legal-links"', body, path)  # footer row, not only the checkbox links
            self.assertIn('href="/terms/"', body, path)
            self.assertIn('href="/privacy/"', body, path)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DEFAULT_FROM_EMAIL="noreply@example.com")
class SignupConsentTests(TestCase):
    def test_signup_form_has_required_consent_checkbox(self):
        body = self.client.get("/accounts/signup/").content.decode()
        self.assertIn('name="accept_terms"', body)
        self.assertIn("required", body[body.index('name="accept_terms"'):][:200])

    def test_form_signup_without_consent_is_refused_and_creates_no_user(self):
        res = self.client.post("/accounts/signup/", SIGNUP)
        self.assertEqual(res.status_code, 200)
        self.assertIn("auth_error_terms_required", res.content.decode())
        self.assertFalse(User.objects.filter(username="consent_user").exists())

    def test_form_signup_with_consent_records_acceptance_and_version(self):
        self.client.post("/accounts/signup/", {**SIGNUP, "accept_terms": "on"})
        profile = AuthWorkflowService.get_profile(User.objects.get(username="consent_user"))
        self.assertIsNotNone(profile.terms_accepted_at)
        self.assertEqual(profile.terms_version, LEGAL_VERSION)

    def test_api_signup_requires_consent(self):
        post = lambda body: self.client.post("/api/auth/signup/", data=json.dumps(body), content_type="application/json")
        refused = post(SIGNUP)
        self.assertEqual(refused.status_code, 400)
        self.assertEqual(refused.json()["error_key"], "auth_error_terms_required")
        self.assertEqual(post({**SIGNUP, "accept_terms": False}).status_code, 400)
        self.assertEqual(post({**SIGNUP, "accept_terms": True}).status_code, 201)

    def test_consent_check_does_not_reveal_registered_emails(self):
        # Refusal happens before any account lookup, so it is identical for new and existing emails.
        User.objects.create_user(username="existing", email="consent@example.com", password="x-pass-12345")
        res = self.client.post("/accounts/signup/", SIGNUP)
        self.assertIn("auth_error_terms_required", res.content.decode())

    def test_admin_created_accounts_have_no_recorded_consent(self):
        user = User.objects.create_user(username="byadmin", password="x-pass-12345")
        profile = AuthWorkflowService.get_profile(user)
        self.assertIsNone(profile.terms_accepted_at)
        self.assertEqual(profile.terms_version, "")
