from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from core.models import AppSettings

User = get_user_model()

_SIGNUP = {"password": "SecurePass123!", "confirm_password": "SecurePass123!", "lang": "en"}


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DEFAULT_FROM_EMAIL="noreply@example.com")
class LoginLockoutTests(TestCase):
    def setUp(self):
        AppSettings.set("active_language", "en")
        self.user = User.objects.create_user(username="victim", email="v@example.com", password="RightPass123!")

    def _bad_login(self):
        return self.client.post("/accounts/login/", {"username": "victim", "password": "wrong"})

    def test_lockout_after_five_failures_even_with_right_password(self):
        for _ in range(5):
            self._bad_login()
        res = self.client.post("/accounts/login/", {"username": "victim", "password": "RightPass123!"})
        self.assertEqual(res.status_code, 429)
        self.assertContains(res, "auth_error_too_many_attempts", status_code=429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_api_login_lockout_returns_json_429(self):
        body = '{"username": "victim", "password": "wrong"}'
        for _ in range(5):
            self.client.post("/api/auth/login/", data=body, content_type="application/json")
        res = self.client.post("/api/auth/login/", data=body, content_type="application/json")
        self.assertEqual(res.status_code, 429)
        self.assertEqual(res.json()["error_key"], "auth_error_too_many_attempts")

    def test_four_failures_then_success_still_logs_in(self):
        for _ in range(4):
            self._bad_login()
        res = self.client.post("/accounts/login/", {"username": "victim", "password": "RightPass123!"})
        self.assertEqual(res.status_code, 302)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", DEFAULT_FROM_EMAIL="noreply@example.com")
class SignupEnumerationTests(TestCase):
    def setUp(self):
        AppSettings.set("active_language", "en")

    def _signup(self, username, email):
        return self.client.post("/accounts/signup/", {"username": username, "email": email, **_SIGNUP})

    def test_response_identical_for_new_and_registered_email(self):
        fresh = self._signup("fresh", "fresh@example.com")
        User.objects.filter(username="fresh").update(is_active=True)
        again = self._signup("other", "fresh@example.com")
        for res in (fresh, again):
            self.assertContains(res, "auth_signup_success_verify_email")
        self.assertEqual(User.objects.filter(email="fresh@example.com").count(), 1)

    def test_pending_account_gets_a_new_verification_email(self):
        self._signup("pend", "pend@example.com")
        mail.outbox.clear()
        self._signup("pend2", "pend@example.com")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/accounts/verify-email/", mail.outbox[0].body)
